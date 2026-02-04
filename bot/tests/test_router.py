from unittest.mock import AsyncMock, MagicMock

from core.router import MessageRouter


def _make_router() -> MessageRouter:
    agent = MagicMock()
    db = MagicMock()
    return MessageRouter(agent, db)


def test_should_respond_command():
    r = _make_router()
    assert r.should_respond("/help") is True


def test_should_respond_mention():
    r = _make_router()
    assert r.should_respond("hey @regelebot how are you?") is True


def test_should_respond_normal():
    r = _make_router()
    assert r.should_respond("just chatting") is False


def test_clean_message():
    r = _make_router()
    assert r.clean_message("@regelebot hello") == "hello"


def test_is_command():
    r = _make_router()
    assert r.is_command("/poll") is True
    assert r.is_command("hello") is False
