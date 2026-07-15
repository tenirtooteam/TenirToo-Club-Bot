"""[Feature 011] Сквозной прогон трёх дефектных сценариев через диспетчер.

Тесты в test_callback_routing_defects.py зовут навигатор напрямую — то есть
доказывают, что ПОСЛЕ фильтра всё правильно. Здесь замыкается недостающее звено:
клик идёт через реальный Dispatcher с реальными роутерами, поэтому проверяется
вся цепь «кнопка клавиатуры -> Factory.filter() -> навигатор -> экран».

Это ближайшее к ручной проверке из quickstart.md §7, что достижимо без живого
Telegram: транспорт замокан, всё остальное настоящее.
"""

import datetime
from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

import callbacks as cb


def _make_dispatcher() -> Dispatcher:
    from handlers.admin import router as admin_router
    from handlers.announcements import router as announcements_router
    from handlers.common import router as common_router
    from handlers.events import router as events_router
    from handlers.moderator import router as moderator_router
    from handlers.user import router as user_router

    dp = Dispatcher(storage=MemoryStorage())
    for r in (common_router, user_router, admin_router, moderator_router, events_router, announcements_router):
        r._parent_router = None
        dp.include_router(r)
    return dp


def _button_data(markup, fragment: str) -> str:
    for row in markup.inline_keyboard:
        for btn in row:
            if fragment in btn.text and btn.callback_data:
                return btn.callback_data
    raise AssertionError(f"кнопка {fragment!r} не найдена")


async def _click(dp: Dispatcher, bot, callback_data: str, user_id: int):
    callback = types.CallbackQuery(
        id="1",
        from_user=types.User(id=user_id, is_bot=False, first_name="Admin"),
        chat_instance="1",
        message=types.Message(
            message_id=100,
            date=datetime.datetime.now(),
            chat=types.Chat(id=user_id, type="private"),
            text="Menu Context",
        ),
        data=callback_data,
    )
    with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await dp.feed_update(bot, types.Update(update_id=1, callback_query=callback))


@pytest.fixture
def admin_env():
    """Админ + списки длиннее одной страницы (limit=7)."""
    from database import db

    admin_id = 999999999
    db.add_user(admin_id, "Admin", "Root")
    db.add_user(777, "Targetuser", "Testovich")

    db.register_topic_if_not_exists(55)
    db.update_topic_name(55, "ALPHATOPIC")
    group_ids = []
    for i in range(9):
        gid = db.create_group(f"GROUP{i:02d}")
        db.add_topic_to_group(gid, 55)
        group_ids.append(gid)
    for t_id in range(101, 110):
        db.register_topic_if_not_exists(t_id)
        db.update_topic_name(t_id, f"TOPIC{t_id}")
        db.add_topic_to_group(group_ids[0], t_id)

    bot = AsyncMock()
    bot.id = 123456789
    return {"dp": _make_dispatcher(), "bot": bot, "admin_id": admin_id, "group_ids": group_ids}


@pytest.mark.asyncio
async def test_journey_def1_next_page_keeps_the_same_topic(admin_env):
    """[DEF-1 / quickstart §7] «След. ▶️» на группах топика 55 остаётся в топике 55."""
    import keyboards as kb

    markup = kb.moderator_group_list_kb(topic_id=55, page=1)
    next_data = _button_data(markup, "След.")

    seen = {}

    def _spy(topic_id, page=1, limit=7):
        seen["topic_id"], seen["page"] = topic_id, page
        return markup

    with patch("services.permission_service.PermissionService.can_manage_topic", return_value=True), \
         patch("keyboards.moderator_group_list_kb", side_effect=_spy), \
         patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock):
        await _click(admin_env["dp"], admin_env["bot"], next_data, admin_env["admin_id"])

    assert seen == {"topic_id": 55, "page": 2}, (
        f"сквозь диспетчер приехало {seen}, ожидалось topic_id=55, page=2"
    )


@pytest.mark.asyncio
async def test_journey_def2_role_topic_picker_paginates(admin_env):
    """[DEF-2 / quickstart §7] «След. ▶️» в выборе топика для роли открывает стр. 2."""
    import keyboards as kb

    markup = kb.topic_selection_for_role_kb(user_id=777, page=1)
    next_data = _button_data(markup, "След.")

    seen = {}

    def _spy(user_id, page=1, limit=7):
        seen["user_id"], seen["page"] = user_id, page
        return markup

    with patch("keyboards.topic_selection_for_role_kb", side_effect=_spy), \
         patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock):
        await _click(admin_env["dp"], admin_env["bot"], next_data, admin_env["admin_id"])

    assert seen == {"user_id": 777, "page": 2}, (
        f"сквозь диспетчер приехало {seen}, ожидалось user_id=777, page=2"
    )


@pytest.mark.asyncio
async def test_journey_def3_topic_from_group_opens_that_topic(admin_env):
    """[DEF-3 / quickstart §7] Топик из списка группы открывает СВОЮ карточку."""
    import keyboards as kb
    from services.ui_service import UIService

    group_id = admin_env["group_ids"][0]
    markup = kb.group_topics_list_kb(group_id)
    topic_data = _button_data(markup, "TOPIC101")

    spy = AsyncMock()
    with patch.object(UIService, "show_topic_detail", spy):
        await _click(admin_env["dp"], admin_env["bot"], topic_data, admin_env["admin_id"])

    assert spy.called, "show_topic_detail не вызван — маршрут не дошёл сквозь фильтр"
    args, kwargs = spy.call_args.args, spy.call_args.kwargs
    got_topic = kwargs.get("topic_id", args[2] if len(args) > 2 else None)
    got_group = kwargs.get("group_id", args[3] if len(args) > 3 else None)
    assert (got_topic, got_group) == (101, group_id), (
        f"сквозь диспетчер приехало topic_id={got_topic}, group_id={got_group}"
    )


@pytest.mark.asyncio
async def test_journey_stale_old_format_button_does_not_crash(admin_env):
    """[C-7] Кнопка старого формата из истории чата не роняет бота.

    После обновления в чатах остаются сообщения с кнопками вида `user_info_5`.
    Фильтры их не признают, диспетчер отдаёт их глобальному fallback (`R-SEC-2`).
    Требование — не упасть.
    """
    for stale in ("user_info_5", "mod_topic_groups_55_pg_2", "manage_groups", "help:templates:manage_groups"):
        with patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock):
            await _click(admin_env["dp"], admin_env["bot"], stale, admin_env["admin_id"])


@pytest.mark.asyncio
async def test_journey_typed_entry_button_reaches_its_screen(admin_env):
    """Кнопка входа в списочный экран доезжает до экрана сквозь фильтр (US2)."""
    import keyboards as kb
    from services.ui_service import UIService

    entry = _button_data(kb.main_admin_kb(), "ШАБЛОНЫ ДОСТУПА")
    assert entry == cb.ManageGroupsCB(page=1).pack(), "producer выпустил не объявленный формат"

    shown = AsyncMock()
    with patch.object(UIService, "sterile_show", shown), \
         patch("services.permission_service.PermissionService.is_global_admin", return_value=True):
        await _click(admin_env["dp"], admin_env["bot"], entry, admin_env["admin_id"])

    assert shown.called, "кнопка не доехала до экрана"
    assert "Шаблоны доступа" in shown.call_args.args[2]
