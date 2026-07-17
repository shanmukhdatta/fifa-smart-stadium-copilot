import pytest
from fastapi.testclient import TestClient

from backend.ai.llm_client import LLMUnavailableError
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def force_llm_unavailable(monkeypatch):
    async def _raise(*args, **kwargs):
        raise LLMUnavailableError("forced for test")

    monkeypatch.setattr("backend.ai.llm_client.complete", _raise)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_login_success():
    resp = client.post("/api/auth/login", json={"username": "fan1", "password": "fanpass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password():
    resp = client.post("/api/auth/login", json={"username": "fan1", "password": "wrong"})
    assert resp.status_code == 401


def test_demo_token_issued_for_fan_role():
    resp = client.post("/api/auth/demo-token", params={"role": "fan"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_chat_requires_auth():
    resp = client.post("/api/chat", json={"message": "Where is Gate 2?"})
    assert resp.status_code == 401


def test_chat_authenticated_flow():
    token = client.post("/api/auth/demo-token", params={"role": "fan"}).json()["access_token"]
    resp = client.post(
        "/api/chat",
        json={"message": "Where is the nearest restroom?", "language": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_text"]
    assert "navigation" in body["agents_used"]
    assert body["request_id"]


def test_chat_rejects_empty_message():
    token = client.post("/api/auth/demo-token", params={"role": "fan"}).json()["access_token"]
    resp = client.post(
        "/api/chat",
        json={"message": "", "language": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422  # Pydantic min_length validation


def test_chat_message_too_long_rejected():
    token = client.post("/api/auth/demo-token", params={"role": "fan"}).json()["access_token"]
    resp = client.post(
        "/api/chat",
        json={"message": "a" * 5000, "language": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_chat_history_preserved():
    token = client.post("/api/auth/demo-token", params={"role": "fan"}).json()["access_token"]
    client.post(
        "/api/chat",
        json={"message": "Where is the nearest restroom to Gate 2?", "language": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )
    from backend.api.routes import _get_history
    history = _get_history("demo-fan")
    assert history is not None
    assert len(history) >= 2
    assert history[-2]["role"] == "user"
    assert "Gate 2" in history[-2]["content"]
    assert history[-1]["role"] == "assistant"


def test_demo_token_rate_limited():
    from backend.core.rate_limit import limiter
    limiter.reset()

    # Make 5 requests within the limit (5/minute)
    for _ in range(5):
        resp = client.post("/api/auth/demo-token", params={"role": "fan"})
        assert resp.status_code == 200

    # The 6th request should trigger a 429
    resp = client.post("/api/auth/demo-token", params={"role": "fan"})
    assert resp.status_code == 429
