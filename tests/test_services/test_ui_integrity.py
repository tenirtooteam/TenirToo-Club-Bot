
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.pagination_util import add_nav_footer
import config

def test_callback_data_length_integrity():
    """Проверка, что все стандартные callback_data в подвале не превышают 64 байт."""
    builder = InlineKeyboardBuilder()
    # Имитируем длинные ключи
    long_key = "a" * 30
    long_back = "b" * 30
    add_nav_footer(builder, help_key=long_key, help_back_data=long_back)
    
    markup = builder.as_markup()
    for row in markup.inline_keyboard:
        for btn in row:
            if btn.callback_data:
                assert len(btn.callback_data.encode('utf-8')) <= 64

def test_webapp_url_integrity():
    """Проверка, что кнопки WebApp не создаются с пустым URL."""
    with patch("config.WEBAPP_URL", ""):
        from keyboards.user_kb import user_main_kb
        markup = user_main_kb()
        for row in markup.inline_keyboard:
            for btn in row:
                if btn.web_app:
                    assert btn.web_app.url != ""
                    assert btn.web_app.url is not None

@pytest.mark.asyncio
async def test_help_handler_robustness():
    """Проверка, что universal_help_handler переваривает старые форматы."""
    from handlers.common import universal_help_handler
    from aiogram.fsm.context import FSMContext
    
    # Мокаем колбэк со старым форматом (без двоеточий)
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.data = "help_main_menu"
    callback.message = AsyncMock(spec=types.Message)
    state = AsyncMock(spec=FSMContext)
    
    with patch("handlers.common.show_help_view", new_callable=AsyncMock) as mock_show:
        await universal_help_handler(callback, state)
        # Должен распарсить как key="main_menu" и back_data="landing"
        mock_show.assert_called_once()
        args = mock_show.call_args[0]
        assert args[2] == "main_menu" # key
        assert args[3] == "landing"   # back_data

def test_all_help_keys_exist():
    """Проверка, что все кнопки справки в клавиатурах имеют соответствующие записи в HelpService."""
    from services.help_service import HelpService
    from keyboards.admin_kb import main_admin_kb
    from keyboards.user_kb import user_main_kb
    
    for kb_func in [main_admin_kb, user_main_kb]:
        markup = kb_func()
        for row in markup.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("help:"):
                    key = btn.callback_data.split(":")[1]
                    # fallback не должен возвращать ⚠️ если ключ существует
                    help_text = HelpService.get_help(key)
                    assert "информация для данного раздела пока не добавлена" not in help_text
