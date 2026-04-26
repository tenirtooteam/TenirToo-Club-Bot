import pytest
from unittest.mock import AsyncMock, patch
from aiogram import types
from services.ui_service import UIService

@pytest.mark.asyncio
async def test_show_menu_with_callback_query():
    """Проверяет, что show_menu корректно обрабатывает CallbackQuery."""
    # Подготавливаем моки
    state = AsyncMock()
    state.get_data.return_value = {"last_menu_ids": []}
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.message = AsyncMock(spec=types.Message)
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    
    # Запускаем метод
    await UIService.sterile_show(state, callback, "Тестовый текст", reply_markup=None)
    
    # Проверяем, что были вызваны нужные методы Telegram API
    callback.message.edit_text.assert_called_once_with("Тестовый текст", reply_markup=None, parse_mode="HTML")
    callback.answer.assert_called_once()
    
@pytest.mark.asyncio
async def test_show_menu_with_message():
    """Проверяет, что show_menu корректно обрабатывает Message (очистка старого меню + отправка нового)."""
    state = AsyncMock()
    state.get_data.return_value = {"last_menu_ids": [100]}
    
    message = AsyncMock(spec=types.Message)
    message.chat = AsyncMock()
    message.chat.id = 123
    message.bot = AsyncMock()
    message.bot.send_message = AsyncMock(return_value=AsyncMock(message_id=200))
    message.bot.delete_message = AsyncMock()
    message.delete = AsyncMock()
    
    await UIService.sterile_show(state, message, "Новый текст", reply_markup=None)
    
    # Проверяем удаление старого меню через finish_input -> clear_last_menu
    message.bot.delete_message.assert_called_with(chat_id=123, message_id=100)
    
    # Проверяем отправку нового
    message.bot.send_message.assert_called_once_with(123, "Новый текст", reply_markup=None, parse_mode="HTML")
    
    # Проверяем, что новый ID запомнен в FSM
    state.update_data.assert_called_with(last_menu_ids=[200])
    
    # [CC-1] КРИТИЧЕСКИЙ ТЕСТ: проверяем, что состояние НЕ сброшено в None
    # (поскольку это промежуточное меню)
    state.set_state.assert_not_called()

@pytest.mark.asyncio
async def test_finish_input_with_state_reset():
    """Проверяет, что finish_input принудительно сбрасывает состояние, если reset_state=True."""
    state = AsyncMock()
    state.get_data.return_value = {}
    message = AsyncMock(spec=types.Message)
    message.chat = AsyncMock()
    message.chat.id = 123
    message.bot = AsyncMock()
    
    await UIService.terminate_input(state, message, reset_state=True)
    state.set_state.assert_called_once_with(None)

@pytest.mark.asyncio
async def test_finish_input_without_state_reset():
    """Проверяет, что finish_input СОХРАНЯЕТ состояние, если reset_state=False."""
    state = AsyncMock()
    state.get_data.return_value = {}
    message = AsyncMock(spec=types.Message)
    message.chat = AsyncMock()
    message.chat.id = 123
    message.bot = AsyncMock()
    
    await UIService.terminate_input(state, message, reset_state=False)
    state.set_state.assert_not_called()
@pytest.mark.asyncio
async def test_generic_navigator_signature_protection():
    """
    [CC-2] Проверяет, что generic_navigator падает с правильной (или перехваченной) ошибкой,
    если в него передать неверные аргументы (защита от повторения бага).
    """
    state = AsyncMock()
    # Эмулируем вызов старого багованного формата (state не передан, callback первым)
    event_str = "🏔 <b>Мероприятия Клуба</b>" # Передаем строку вместо event, как было в баге
    
    # Этот тест проверяет, что ошибка 'str' object has no attribute 'from_user'
    # возникает именно в generic_navigator, поэтому мы должны использовать show_menu
    with pytest.raises(AttributeError):
        # Если мы передаем строку вместо event в generic_navigator, он упадет на from_user
        await UIService.generic_navigator(state, event_str, "какой-то_callback_data")
