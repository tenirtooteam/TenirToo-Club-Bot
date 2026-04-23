import pytest
from unittest.mock import AsyncMock, MagicMock
from services.ui_service import UIService
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

@pytest.fixture
def mock_state():
    storage = MemoryStorage()
    key = MagicMock()
    key.chat_id = 123
    key.user_id = 456
    return FSMContext(storage, key)

@pytest.mark.asyncio
async def test_ui_sterile_cleanup_logic(mock_state):
    # Мокаем бота и сообщение (используем Message для срабатывания логики очистки)
    bot = AsyncMock()
    message = AsyncMock()
    message.message_id = 1001
    message.bot = bot
    message.chat.id = 123
    message.chat.type = "private"
    
    # Записываем старый ID меню в стейт
    await mock_state.update_data(last_menu_id=999)
    
    # Мокаем отправку сообщения
    bot.send_message = AsyncMock(return_value=AsyncMock(message_id=2002))
    
    # Вызываем show_menu с сообщением
    await UIService.show_menu(mock_state, message, "New Menu", reply_markup=None)
    
    # Проверяем, что бот пытался удалить старое сообщение (999)
    bot.delete_message.assert_any_call(chat_id=123, message_id=999)
    
    # Проверяем, что новый ID меню (2002) сохранен в стейт
    data = await mock_state.get_data()
    assert data['last_menu_id'] == 2002

@pytest.mark.asyncio
async def test_ui_redirect_command_cleanup(mock_state):
    bot = AsyncMock()
    message = AsyncMock()
    message.message_id = 2000
    message.bot = bot
    message.chat.id = 123
    message.chat.type = "private"
    
    # Имитируем старое меню
    await mock_state.update_data(last_menu_id=1500)
    
    # Вызываем sterile_command декоратор (внутреннюю логику)
    # Здесь мы тестируем UIService.clear_last_menu напрямую
    await UIService.clear_last_menu(mock_state, bot, 123)
    
    bot.delete_message.assert_called_with(chat_id=123, message_id=1500)
    
    # После очистки в стейте не должно быть ID
    data = await mock_state.get_data()
    assert data.get('last_menu_id') is None
