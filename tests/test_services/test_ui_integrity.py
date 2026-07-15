
import pytest
from unittest.mock import AsyncMock, patch
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.pagination_util import add_nav_footer

def test_callback_data_length_integrity():
    """Все callback_data в подвале укладываются в лимит Telegram 64 байта.

    [feature 011 / FR-011] Реальный худший случай: самый длинный ключ справки
    плюс вложенный упакованный маршрут возврата с максимальными ID.
    """
    import callbacks as cb

    builder = InlineKeyboardBuilder()
    add_nav_footer(
        builder,
        back_data=cb.UserInfoCB(user_id=9999999999).pack(),
        help_key="moderator_tools",
        help_back_data=cb.GroupTopicsListCB(group_id=999999, page=999).pack(),
    )

    markup = builder.as_markup()
    for row in markup.inline_keyboard:
        for btn in row:
            if btn.callback_data:
                assert len(btn.callback_data.encode('utf-8')) <= 64


def test_callback_data_overflow_fails_loudly_instead_of_truncating():
    """[feature 011 / FR-011] Превышение лимита — громкий отказ, а не тихая обрезка.

    Раньше add_nav_footer резал строку как `cb_data[:64]`. Обрезка посередине
    давала синтаксически целый, но семантически битый маршрут: кнопка строилась,
    пользователь жал, и она молча уходила в fallback «Ошибка навигации».

    Теперь лимит обеспечивает `pack()`, и превышение падает на сборке клавиатуры
    — то есть в тестах у разработчика, а не в чате у пользователя. Вход ниже
    синтетический: реальные ключи и маршруты возврата дают ~49 байт из 64.
    """
    import callbacks as cb

    with pytest.raises(ValueError, match="too long"):
        cb.HelpCB(key="a" * 30, back_data="b" * 30).pack()

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
async def test_help_handler_receives_named_fields():
    """[R-UI-11 / feature 011] Хендлер справки получает поля по имени.

    Разбор переехал в объявление формата: ручная лесенка по `split(":")` с
    угадыванием формата заменена на `HelpCB`, а ключ и маршрут возврата
    приезжают именованными полями (FR-003).
    """
    import callbacks as cb
    from handlers.common import universal_help_handler
    from aiogram.fsm.context import FSMContext

    callback = AsyncMock(spec=types.CallbackQuery)
    callback.message = AsyncMock(spec=types.Message)
    state = AsyncMock(spec=FSMContext)
    data = cb.HelpCB(key="main_menu", back_data="landing")

    with patch("handlers.common.show_help_view", new_callable=AsyncMock) as mock_show:
        await universal_help_handler(callback, state, data)

    mock_show.assert_called_once()
    args = mock_show.call_args.args
    assert args[2] == "main_menu"  # key
    assert args[3] == "landing"    # back_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_data",
    [
        "help_main_menu",          # совсем старый формат
        "help:main_menu",          # переходный формат: неверная арность
        "help|main_menu",          # неверная арность в новом формате
        "help|a|b|c",              # лишний сегмент
        "not_help_at_all",         # чужой маршрут
    ],
)
async def test_help_filter_rejects_malformed_defensively(bad_data):
    """[R-UI-11] Защитный разбор обеспечивает фильтр, а не хендлер.

    `HelpCB.filter()` ловит `(TypeError, ValueError)` внутри `unpack()` и просто
    не пропускает битые данные — исключение наружу не выходит. Такие колбэки
    уходят в глобальный fallback (`R-SEC-2`), то есть деградируют безопасно (C-7).
    """
    import callbacks as cb

    callback = AsyncMock(spec=types.CallbackQuery)
    callback.data = bad_data

    result = await cb.HelpCB.filter()(callback)
    assert result is False, f"{bad_data!r} не должен проходить фильтр справки"

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
