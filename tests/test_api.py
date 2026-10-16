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
