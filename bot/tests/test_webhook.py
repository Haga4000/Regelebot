from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _message_payload():
    return {
        "from_": "group1",
        "sender": "user1",
        "sender_name": "Alice",
        "body": "/help",
        "timestamp": 1234567890,
    }


def test_missing_secret(client):
    resp = client.post("/webhook/message", json=_message_payload())
    assert resp.status_code == 422


def test_wrong_secret(client):
    resp = client.post(
        "/webhook/message",
        json=_message_payload(),
        headers={"X-Webhook-Secret": "wrong"},
    )
    assert resp.status_code == 401


@patch("api.webhook.get_db")
@patch("api.webhook.ConversationService")
@patch("api.webhook.MainAgent")
@patch("api.webhook.MessageRouter")
def test_rate_limit(mock_router_cls, mock_agent_cls, mock_conv_cls, mock_get_db, client):
    # Set up mock context manager for get_db
    mock_db = AsyncMock()
    mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_conv = AsyncMock()
    mock_conv.get_recent_history.return_value = []
    mock_conv_cls.return_value = mock_conv

    mock_router = AsyncMock()
    mock_router.should_respond.return_value = False
    mock_router.route.return_value = None
    mock_router_cls.return_value = mock_router

    headers = {"X-Webhook-Secret": "test-secret"}

    # Reset the rate limiter for this test
    from core.rate_limiter import rate_limiter
    rate_limiter.reset()

    for i in range(10):
        resp = client.post("/webhook/message", json=_message_payload(), headers=headers)
        assert resp.status_code == 200, f"Request {i+1} failed unexpectedly"

    resp = client.post("/webhook/message", json=_message_payload(), headers=headers)
    assert resp.status_code == 429


@patch("api.webhook.get_db")
@patch("api.webhook.ConversationService")
@patch("api.webhook.MainAgent")
@patch("api.webhook.MessageRouter")
def test_null_reply(mock_router_cls, mock_agent_cls, mock_conv_cls, mock_get_db, client):
    mock_db = AsyncMock()
    mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_conv = AsyncMock()
    mock_conv.get_recent_history.return_value = []
    mock_conv_cls.return_value = mock_conv

    mock_router = AsyncMock()
    mock_router.should_respond.return_value = False
    mock_router.route.return_value = None
    mock_router_cls.return_value = mock_router

    headers = {"X-Webhook-Secret": "test-secret"}

    from core.rate_limiter import rate_limiter
    rate_limiter.reset()

    resp = client.post("/webhook/message", json=_message_payload(), headers=headers)
    assert resp.status_code == 200
    assert resp.json()["reply"] is None
