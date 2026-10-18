import pytest
from fastapi.testclient import TestClient

from app import advisor, usage
from app.api import app
from app.schemas import Usage
from app.security import limiter

client = TestClient(app)


def fake_chat(message, previous_id=None):
    call = Usage(input_tokens=100, output_tokens=50, cost_usd=0.00004)
    return "Hello!", "resp_1", call, call


@pytest.fixture(autouse=True)
def _reset_limiter():
    limiter.reset()
    usage.reset_daily()


def test_origin_locked(monkeypatch):
    from app import security

    monkeypatch.setattr(advisor, "chat", fake_chat)
    monkeypatch.setattr(security, "ALLOWED_ORIGINS", ["https://my.app"])
    assert client.post("/chat", json={"message": "hi"}).status_code == 403
    bad = client.post("/chat", json={"message": "hi"}, headers={"Origin": "https://other-site.example"})
    assert bad.status_code == 403
    ok = client.post("/chat", json={"message": "hi"}, headers={"Origin": "https://my.app"})
    assert ok.status_code == 200


def test_daily_budget_stops_requests(monkeypatch):
    from app import security

    monkeypatch.setattr(advisor, "chat", fake_chat)
    monkeypatch.setattr(security, "DAILY_BUDGET_USD", 0.00005)
    assert client.post("/chat", json={"message": "hi"}).status_code == 200  # spends 0.00004
    assert client.post("/chat", json={"message": "hi"}).status_code == 200  # still under cap, spends more
    assert client.post("/chat", json={"message": "hi"}).status_code == 503


def test_conversation_cost_cap(monkeypatch):
    from app import security

    monkeypatch.setattr(advisor, "chat", fake_chat)
    monkeypatch.setattr(security, "MAX_CONVERSATION_USD", 0.1)
    usage.add_to_conversation("resp_big", None, Usage(cost_usd=0.5))
    r = client.post("/chat", json={"message": "hi", "previous_response_id": "resp_big"})
    assert r.status_code == 429


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_chat(monkeypatch):
    monkeypatch.setattr(advisor, "chat", fake_chat)
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "Hello!"
    assert body["response_id"] == "resp_1"
    assert body["usage"]["input_tokens"] == 100
    assert body["conversation_usage"]["output_tokens"] == 50


def test_chat_validation():
    assert client.post("/chat", json={"message": ""}).status_code == 422
    assert client.post("/chat", json={"message": "x" * 5000}).status_code == 422


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(advisor, "chat", fake_chat)
    codes = [client.post("/chat", json={"message": "hi"}).status_code for _ in range(12)]
    assert codes[:10] == [200] * 10
    assert codes[10:] == [429, 429]


def test_security_headers():
    assert client.get("/health").headers["x-content-type-options"] == "nosniff"


def test_cost_estimate():
    # 1M input + 1M output tokens of gpt-4o-mini = $0.15 + $0.60
    assert usage.estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000) == 0.75
    assert usage.estimate_cost("unknown-model", 1000, 1000) == 0.0


def test_conversation_total_accumulates():
    first = usage.add_to_conversation("r1", None, Usage(input_tokens=10, output_tokens=5, cost_usd=0.1))
    second = usage.add_to_conversation("r2", "r1", Usage(input_tokens=20, output_tokens=5, cost_usd=0.2))
    assert first.input_tokens == 10
    assert second.input_tokens == 30
    assert second.output_tokens == 10
    assert second.cost_usd == 0.3


def _sample_itinerary():
    from app.schemas import Activity, Budget, BudgetItem, DayPlan, Itinerary, ItineraryResult

    it = Itinerary(
        title="Lisbon Food & Art", destination="Lisbon", duration_days=1, summary="s",
        days=[DayPlan(day=1, theme="Food", activities=[
            Activity(time_of_day="morning", title="Pastel de nata", description="d", estimated_cost=3)])],
        tips=["Walk a lot"],
        budget=Budget(currency="EUR", items=[BudgetItem(category="Food", amount=3)], total=3),
    )
    return ItineraryResult(ready=True, clarification=None, itinerary=it)


def test_itinerary_ready(monkeypatch):
    call = Usage(input_tokens=1, output_tokens=2, cost_usd=0.0)
    monkeypatch.setattr(advisor, "generate_itinerary", lambda pid: (_sample_itinerary(), "resp_2", call, call))
    r = client.post("/itinerary", json={"previous_response_id": "resp_1"})
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["itinerary"]["days"][0]["activities"][0]["time_of_day"] == "morning"
    assert body["itinerary"]["budget"]["total"] == 3


def test_itinerary_needs_clarification(monkeypatch):
    from app.schemas import ItineraryResult

    call = Usage()
    res = ItineraryResult(ready=False, clarification="How many days?", itinerary=None)
    monkeypatch.setattr(advisor, "generate_itinerary", lambda pid: (res, "resp_2", call, call))
    body = client.post("/itinerary", json={"previous_response_id": "resp_1"}).json()
    assert body["ready"] is False
    assert body["clarification"] == "How many days?"
    assert body["itinerary"] is None


def test_itinerary_requires_conversation_id():
    assert client.post("/itinerary", json={}).status_code == 422
