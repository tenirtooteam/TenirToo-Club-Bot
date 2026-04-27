import pytest
from unittest.mock import AsyncMock
from aiogram import Bot
from services.notification_service import NotificationService

@pytest.mark.asyncio
async def test_send_to_users():
    mock_bot = AsyncMock(spec=Bot)
    user_ids = [111, 222, 111] # Duplicate should be handled by set()
    text = "Test notification"
    
    await NotificationService.send_to_users(mock_bot, user_ids, text)
    
    # Check that send_message was called for each unique user
    assert mock_bot.send_message.call_count == 2
    
    # Verify calls
    calls = mock_bot.send_message.call_args_list
    called_ids = [c.kwargs['chat_id'] for c in calls]
    assert 111 in called_ids
    assert 222 in called_ids
    assert text in calls[0].kwargs['text']

@pytest.mark.asyncio
async def test_send_to_users_error_handling():
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.send_message.side_effect = Exception("Telegram Error")
    
    # Should not raise exception
    await NotificationService.send_to_users(mock_bot, [123], "Fail test")
    assert mock_bot.send_message.called
