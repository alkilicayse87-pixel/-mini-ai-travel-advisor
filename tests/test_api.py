import pytest
from fastapi.testclient import TestClient

from app import advisor
from app.api import app
from app.security import limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_limiter():
    limiter.reset()


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


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(advisor, 'chat', lambda m, p=None: ('ok', 'resp_1'))
    codes = [client.post('/chat', json={'message': 'hi'}).status_code for _ in range(12)]
    assert codes[:10] == [200] * 10
    assert codes[10:] == [429, 429]


def test_security_headers():
    assert client.get('/health').headers['x-content-type-options'] == 'nosniff'
