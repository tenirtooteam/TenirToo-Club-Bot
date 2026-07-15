"""[Feature 011] CHAR-DEF — воспроизводящие тесты подтверждённых дефектов роутинга.

Три дефекта, найденные при планировании 011 (research.md §2). Каждый — прямое
следствие подстрочного/позиционного разбора в UIService.generic_navigator.

Эти тесты обязаны быть КРАСНЫМИ на текущем коде и зелёными после миграции
(FR-018, R-PROC-3, Constitution IV). Они утверждают КОРРЕКТНОЕ поведение, а не
фиксируют дефект как эталон — иначе миграция узаконила бы баг.

| Тест  | FR     | Дефект                                                       |
|-------|--------|--------------------------------------------------------------|
| DEF-1 | FR-015 | `p = callback_data.split("_")` идёт по строке с хвостом       |
|       |        | `_pg_{n}`, поэтому `int(p[-1])` возвращает номер страницы     |
|       |        | вместо ID сущности.                                           |
| DEF-2 | FR-016 | Префикс `topic_assign_pg_` сам содержит `_pg`; его съедает    |
|       |        | `split("_pg_")[0]`, маршрут не сопоставляется ни с чем.       |
| DEF-3 | FR-017 | `show_topic_detail(int(p[-1]), int(p[-2]))` при сигнатуре     |
|       |        | `(topic_id, group_id)` — аргументы инвертированы.             |

Как и CHAR-OK, тесты format-agnostic: строку колбэка производит реальная
клавиатура, тест её не конструирует.
"""

from unittest.mock import AsyncMock, patch

import pytest

from services.ui_service import UIService
from tests.test_services.test_callback_routing_characterization import (
    NEXT_PAGE,
    button_data,
    route,
)


@pytest.fixture
def seed_paginated():
    """Списки заведомо длиннее одной страницы (limit=7) — иначе стрелки нет."""
    from database import db

    db.add_user(999999999, "Admin", "Root")
    db.add_user(777, "Targetuser", "Testovich")

    # Топик 55 с 9 привязанными шаблонами -> список групп топика паджинируется.
    db.register_topic_if_not_exists(55)
    db.update_topic_name(55, "ALPHATOPIC")
    group_ids = []
    for i in range(9):
        gid = db.create_group(f"GROUP{i:02d}")
        db.add_topic_to_group(gid, 55)
        group_ids.append(gid)

    # 9 уникальных топиков -> список выбора топика для роли паджинируется.
    for t_id in range(101, 110):
        db.register_topic_if_not_exists(t_id)
        db.update_topic_name(t_id, f"TOPIC{t_id}")
        db.add_topic_to_group(group_ids[0], t_id)

    return {"topic_id": 55, "user_id": 777, "group_ids": group_ids}


# --- DEF-1 (FR-015) --------------------------------------------------------


@pytest.mark.asyncio
async def test_def1_paginated_route_keeps_entity_id(seed_paginated):
    """[FR-015] Переход на стр. 2 списка групп топика 55 остаётся в топике 55.

    Сегодня навигатор извлекает `int(p[-1])` по полной строке
    `mod_topic_groups_55_pg_2`, то есть получает topic_id=2 — номер страницы.
    Пользователь видит группы чужого топика.
    """
    import keyboards as kb

    markup = kb.moderator_group_list_kb(topic_id=55, page=1)
    next_page_data = button_data(markup, NEXT_PAGE)

    captured = {}

    def _spy(topic_id, page=1, limit=7):
        captured["topic_id"] = topic_id
        captured["page"] = page
        return markup

    with patch("keyboards.moderator_group_list_kb", side_effect=_spy):
        await route(next_page_data)

    assert captured.get("topic_id") == 55, (
        f"DEF-1: навигатор открыл топик {captured.get('topic_id')} вместо 55 — "
        "номер страницы подменил ID сущности"
    )
    assert captured.get("page") == 2, (
        f"DEF-1: ожидалась страница 2, получена {captured.get('page')}"
    )


# --- DEF-2 (FR-016) --------------------------------------------------------


@pytest.mark.asyncio
async def test_def2_topic_assign_route_is_routable(seed_paginated):
    """[FR-016] Переход на стр. 2 выбора топика для роли работает.

    Сегодня префикс `topic_assign_pg_777` теряет `_pg` в `split("_pg_")[0]`,
    маршрут не матчится и администратора выбрасывает в главное меню.
    """
    import keyboards as kb

    markup = kb.topic_selection_for_role_kb(user_id=777, page=1)
    next_page_data = button_data(markup, NEXT_PAGE)

    captured = {}

    def _spy(user_id, page=1, limit=7):
        captured["user_id"] = user_id
        captured["page"] = page
        return markup

    with patch("keyboards.topic_selection_for_role_kb", side_effect=_spy):
        cap = await route(next_page_data)

    assert "Ошибка навигации" not in cap.text and "Добро пожаловать" not in cap.text, (
        "DEF-2: маршрут не сопоставился и ушёл в защитный возврат"
    )
    assert captured.get("user_id") == 777, (
        f"DEF-2: экран выбора топика не открыт для юзера 777 (получено "
        f"{captured.get('user_id')})"
    )
    assert captured.get("page") == 2, (
        f"DEF-2: ожидалась страница 2, получена {captured.get('page')}"
    )


# --- DEF-3 (FR-017) --------------------------------------------------------


@pytest.mark.asyncio
async def test_def3_topic_in_group_argument_order(seed_paginated):
    """[FR-017] Топик, выбранный из списка топиков группы, открывает свою карточку.

    Кнопка строится как `topic_in_group_{t_id}_{group_id}`, а навигатор зовёт
    `show_topic_detail(int(p[-1]), int(p[-2]))` при сигнатуре
    `(topic_id, group_id)` — аргументы приезжают перевёрнутыми.
    """
    import keyboards as kb

    group_id = seed_paginated["group_ids"][0]
    markup = kb.group_topics_list_kb(group_id)
    topic_button = button_data(markup, "TOPIC101")

    spy = AsyncMock()
    with patch.object(UIService, "show_topic_detail", spy):
        await route(topic_button)

    assert spy.called, "show_topic_detail не вызван"
    args, kwargs = spy.call_args.args, spy.call_args.kwargs
    got_topic = kwargs.get("topic_id", args[2] if len(args) > 2 else None)
    got_group = kwargs.get("group_id", args[3] if len(args) > 3 else None)

    assert (got_topic, got_group) == (101, group_id), (
        f"DEF-3: ожидалось topic_id=101, group_id={group_id}; "
        f"получено topic_id={got_topic}, group_id={got_group} — аргументы инвертированы"
    )
