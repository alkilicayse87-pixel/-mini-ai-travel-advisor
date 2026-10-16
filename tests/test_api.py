from fastapi.testclient import TestClient

from app import advisor
from app.api import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_chat(monkeypatch):
    monkeypatch.setattr(advisor, "chat", lambda m, p=None: ("Hello!", "resp_1"))
    r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 200
    assert r.json() == {"answer": "Hello!", "response_id": "resp_1"}


def test_chat_validation():
    assert client.post("/chat", json={"message": ""}).status_code == 422
    assert client.post("/chat", json={"message": "x" * 5000}).status_code == 422
