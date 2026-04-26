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
    
    # Записываем старый ID меню в стейт (новый формат списка)
    await mock_state.update_data(last_menu_ids=[999])
    
    # Мокаем отправку сообщения
    bot.send_message = AsyncMock(return_value=AsyncMock(message_id=2002))
    
    # Вызываем show_menu с сообщением
    await UIService.sterile_show(mock_state, message, "New Menu", reply_markup=None)
    
    # Проверяем, что бот пытался удалить старое сообщение (999)
    bot.delete_message.assert_any_call(chat_id=123, message_id=999)
    
    # Проверяем, что новый ID меню (2002) сохранен в стейт (в списке)
    data = await mock_state.get_data()
    assert 2002 in data.get('last_menu_ids', [])

@pytest.mark.asyncio
async def test_ui_redirect_command_cleanup(mock_state):
    bot = AsyncMock()
    message = AsyncMock()
    message.message_id = 2000
    message.bot = bot
    message.chat.id = 123
    message.chat.type = "private"
    
    # Имитируем старое меню
    await mock_state.update_data(last_menu_ids=[1500])
    
    # Вызываем sterile_command декоратор (внутреннюю логику)
    # Здесь мы тестируем UIService.delete_tracked_ui напрямую
    await UIService.delete_tracked_ui(mock_state, bot, 123)
    
    bot.delete_message.assert_called_with(chat_id=123, message_id=1500)
    
    # После очистки список должен быть пустым
    data = await mock_state.get_data()
    assert not data.get('last_menu_ids')
    assert data.get('last_menu_id') is None
