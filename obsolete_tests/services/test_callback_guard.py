import pytest
from unittest.mock import AsyncMock
from aiogram.exceptions import TelegramBadRequest
from services.callback_guard import safe_callback

@pytest.mark.asyncio
async def test_safe_callback_suppress_not_modified():
    # Имитируем ошибку "message is not modified"
    callback = AsyncMock()
    callback.answer = AsyncMock()
    
    @safe_callback()
    async def handler(cb):
        # Имитируем ошибку через мок или правильный конструктор
        e = TelegramBadRequest(method=AsyncMock(), message="message is not modified")
        raise e
    
    await handler(callback)
    
    # Должен быть вызван только answer без параметров (тихое подавление)
    callback.answer.assert_called_once_with()

@pytest.mark.asyncio
async def test_safe_callback_alert_on_generic_error():
    callback = AsyncMock()
    callback.answer = AsyncMock()
    
    @safe_callback()
    async def handler(cb):
        raise Exception("Fatal Error")
    
    await handler(callback)
    
    # Должен быть вызван answer с алертом
    callback.answer.assert_called_once()
    args, kwargs = callback.answer.call_args
    assert kwargs["show_alert"] is True
    # Текст передается позиционным аргументом
    assert "Критическая" in args[0]
