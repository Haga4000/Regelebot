from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.conversation import ConversationService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    return ConversationService(mock_db)


async def test_store_adds_and_flushes(service, mock_db):
    await service.store_message(
        group_id="g1",
        role="user",
        content="hello",
        sender_name="Alice",
    )
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()


async def test_get_recent_history_reverses(service, mock_db):
    msg1 = MagicMock()
    msg2 = MagicMock()

    # Simulate DB returning newest-first
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [msg2, msg1]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await service.get_recent_history("g1")
    assert result == [msg1, msg2]  # should be reversed to oldest-first
