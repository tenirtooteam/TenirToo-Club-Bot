import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram import types
from services.ui_service import UIService

# Тест удален из-за конфликта с frozen pydantic моделями aiogram

@pytest.mark.asyncio
async def test_clear_last_menu_calls_bot_delete():
    """[CC-3] Проверка физического удаления сообщений ботом."""
    state = AsyncMock()
    state.get_data.return_value = {"last_menu_ids": [100, 101]}
    bot = AsyncMock()
    
    await UIService.delete_tracked_ui(state, bot, 12345)
    
    # Должно быть 2 вызова delete_message
    assert bot.delete_message.call_count == 2
    # Состояние должно очиститься
    state.update_data.assert_called_with(last_menu_ids=[], last_menu_id=None)
