"""[Feature 011 / US1] CHAR-OK — характеризация роутинга колбэков.

Фиксирует текущее КОРРЕКТНОЕ соответствие «нажатая кнопка -> показанный экран»
перед миграцией на типизированные CallbackData-фабрики (FR-012).

Ключевое свойство: тесты НЕ хардкодят строку колбэка. Формат провода — ровно то,
что меняет миграция (`user_info_5` -> `user_info:5`), поэтому захардкоженный вход
пришлось бы править по ходу, а FR-012 это прямо запрещает. Вместо этого прогон
идёт по кругу «реальная клавиатура -> реальная кнопка -> навигатор», что
format-agnostic по построению и заодно ловит рассинхрон producer/consumer (US2).

Маршруты с подтверждёнными дефектами (FR-015..FR-017) здесь НЕ фиксируются —
их эталон живёт в test_callback_routing_defects.py как RED-репро (FR-018, D-3).
"""

import datetime
from unittest.mock import AsyncMock, patch

import pytest
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from services.ui_service import UIService


# --- Харнесс ---------------------------------------------------------------


class RouteCapture:
    """Что навигатор сделал в ответ на данные кнопки.

    Точка захвата — sterile_show: по R-UI-1 через неё обязан проходить каждый
    переход интерфейса, поэтому она же служит проверкой FR-009.
    """

    def __init__(self):
        self.sterile_show = AsyncMock()
        self.fsm_cleared = AsyncMock()
        self.states_set = []

    @property
    def shown(self) -> bool:
        """Был ли переход выполнен через sterile_show (FR-009)."""
        return self.sterile_show.called

    @property
    def text(self) -> str:
        """Текст показанного экрана (3-й позиционный аргумент sterile_show)."""
        assert self.sterile_show.called, "sterile_show не вызывался — экран не показан"
        return self.sterile_show.call_args.args[2]

    @property
    def markup(self):
        """Разметка показанного экрана."""
        assert self.sterile_show.called, "sterile_show не вызывался — экран не показан"
        kwargs = self.sterile_show.call_args.kwargs
        if "reply_markup" in kwargs:
            return kwargs["reply_markup"]
        args = self.sterile_show.call_args.args
        return args[3] if len(args) > 3 else None

    @property
    def fsm_was_reset(self) -> bool:
        """Сбрасывал ли навигатор состояние FSM на этом переходе (FR-007)."""
        return self.fsm_cleared.called


def button_data(markup, text_fragment: str) -> str:
    """Достаёт callback_data реальной кнопки по фрагменту её текста.

    Именно так тест остаётся format-agnostic: строку колбэка производит
    клавиатура, тест её не знает и не конструирует.
    """
    for row in markup.inline_keyboard:
        for btn in row:
            if text_fragment in btn.text and btn.callback_data:
                return btn.callback_data
    available = [b.text for row in markup.inline_keyboard for b in row]
    raise AssertionError(
        f"Кнопка с фрагментом текста {text_fragment!r} не найдена. Есть: {available}"
    )


NEXT_PAGE = "След."
"""Фрагмент текста кнопки перехода на следующую страницу (pagination_util.py)."""


async def route(callback_data, user_id: int = 999999999) -> RouteCapture:
    """Прогоняет данные кнопки через навигатор и возвращает захват.

    По умолчанию ходим от глобального админа (config.ADMIN_ID из conftest),
    чтобы права не мешали характеризовать именно роутинг.
    """
    cap = RouteCapture()

    bot = AsyncMock()
    bot.id = 123456789
    user = types.User(id=user_id, is_bot=False, first_name="TestUser")
    chat = types.Chat(id=user_id, type="private")
    message = types.Message(
        message_id=1, date=datetime.datetime.now(), chat=chat, text="Menu Context"
    )
    message._bot = bot
    callback = types.CallbackQuery(
        id="1", from_user=user, chat_instance="1", message=message, data=str(callback_data)
    )
    callback._bot = bot

    state = FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id),
    )

    with patch.object(UIService, "sterile_show", cap.sterile_show), patch.object(
        UIService, "clear_fsm_data_safely", cap.fsm_cleared
    ), patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
        await UIService.generic_navigator(state, callback, callback.data)

    return cap


# --- Фикстуры данных -------------------------------------------------------


@pytest.fixture
def seed():
    """Минимальный набор сущностей с различимыми именами.

    Имена намеренно уникальны: экран опознаётся по имени сущности в тексте,
    а не по строке колбэка.
    """
    from database import db

    db.add_user(999999999, "Admin", "Root")
    db.add_user(777, "Targetuser", "Testovich")
    group_id = db.create_group("ALPHAGROUP")
    db.register_topic_if_not_exists(55)
    db.update_topic_name(55, "ALPHATOPIC")
    db.add_topic_to_group(group_id, 55)
    return {"group_id": group_id, "topic_id": 55, "user_id": 777}


# --- CHAR-OK: постоянные маршруты ------------------------------------------

CONSTANT_ROUTES = [
    "admin_main",
    "user_main",
    "roles_dashboard",
    "roles_faq",
]
"""Маршруты, у которых формат — и есть голая строка (`callbacks.CONSTANT_ROUTES`).

Списочные экраны (`manage_groups`, `manage_users`, `all_topics_list`,
`list_users_roles`, `moderator`, `user_topics`) здесь НЕ перечислены: они
паджинируются, то есть параметризованы, и их формат объявлен фабрикой. Их
характеризация — в TOP_LEVEL_LIST_ROUTES ниже.
"""


@pytest.mark.asyncio
@pytest.mark.parametrize("route_data", CONSTANT_ROUTES)
async def test_char_constant_route_shows_screen(seed, route_data):
    """Постоянный маршрут показывает экран через sterile_show (FR-009)."""
    cap = await route(route_data)
    assert cap.shown, f"{route_data}: переход не прошёл через sterile_show"
    assert cap.text, f"{route_data}: пустой текст экрана"


@pytest.mark.asyncio
@pytest.mark.parametrize("route_data", CONSTANT_ROUTES)
async def test_char_constant_route_resets_fsm(seed, route_data):
    """[FR-007 / замок асимметрии] Постоянные маршруты СБРАСЫВАЮТ состояние FSM.

    Половина характеризации асимметрии из services/ui_service.py:279-281:
    сброс живёт внутри `if cmd in simple`. Вторая половина — в
    test_char_parameterized_route_does_not_reset_fsm.
    """
    cap = await route(route_data)
    assert cap.fsm_was_reset, (
        f"{route_data}: постоянный маршрут обязан сбрасывать FSM (FR-007)"
    )


@pytest.mark.asyncio
async def test_char_landing_shows_screen(seed):
    """`landing` разрешается через get_landing_data, а не через словарь simple."""
    cap = await route("landing")
    assert cap.shown
    assert cap.text


# --- CHAR-OK: списочные экраны верхнего уровня -----------------------------
# Жили в словаре `simple`, но паджинируются — то есть параметризованы. Маршрут
# строится ФАБРИКОЙ (источник правды), а не литералом провода: строка формата
# здесь не хардкодится (инвариант №2 набора).


def _top_level_list_routes():
    import callbacks as cb

    return [
        pytest.param(cb.ManageGroupsCB(), id="manage_groups"),
        pytest.param(cb.ManageUsersCB(), id="manage_users"),
        pytest.param(cb.AllTopicsListCB(), id="all_topics_list"),
        pytest.param(cb.ListUsersRolesCB(), id="list_users_roles"),
        pytest.param(cb.ModeratorCB(), id="moderator"),
        pytest.param(cb.UserTopicsCB(), id="user_topics"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("route_cb", _top_level_list_routes())
async def test_char_top_level_list_shows_screen(seed, route_cb):
    cap = await route(route_cb.pack())
    assert cap.shown, f"{route_cb!r}: переход не прошёл через sterile_show"
    assert cap.text


@pytest.mark.asyncio
@pytest.mark.parametrize("route_cb", _top_level_list_routes())
async def test_char_top_level_list_resets_fsm(seed, route_cb):
    """[FR-007 / замок асимметрии] Списочные экраны СБРАСЫВАЮТ состояние FSM.

    Эти маршруты жили в словаре `simple`, а он сбрасывал ввод перед показом.
    Переезд в реестр обязан сохранить это ровно как было (`R-FSM-1`): экраны
    верхнего уровня гасят незавершённый ввод, экраны-карточки — нет.
    """
    cap = await route(route_cb.pack())
    assert cap.fsm_was_reset, (
        f"{route_cb!r}: списочный экран обязан сбрасывать FSM (FR-007)"
    )


@pytest.mark.asyncio
async def test_char_top_level_list_entry_button_is_typed(seed):
    """Кнопка входа в списочный экран выпускает объявленный формат.

    Гоним от реальной клавиатуры: если producer и потребитель разойдутся,
    кнопка уедет в защитный возврат и тест это поймает (US2).
    """
    import keyboards as kb

    cap = await route(button_data(kb.main_admin_kb(), "ШАБЛОНЫ ДОСТУПА"))
    assert "Шаблоны доступа" in cap.text
    assert cap.fsm_was_reset


# --- CHAR-OK: параметризованные маршруты (непаджинируемые) -----------------


@pytest.mark.asyncio
async def test_char_user_info_opens_that_user(seed):
    """Кнопка участника открывает карточку ИМЕННО этого участника."""
    import keyboards as kb

    markup = kb.users_list_kb()
    cap = await route(button_data(markup, "Targetuser"))
    assert "Targetuser" in cap.text


@pytest.mark.asyncio
async def test_char_group_info_opens_that_group(seed):
    """Кнопка шаблона открывает карточку ИМЕННО этого шаблона."""
    import keyboards as kb

    markup = kb.groups_list_kb()
    cap = await route(button_data(markup, "ALPHAGROUP"))
    assert "ALPHAGROUP" in cap.text


@pytest.mark.asyncio
async def test_char_topic_global_view_opens_that_topic(seed):
    """Кнопка топика в общем списке открывает карточку ИМЕННО этого топика."""
    import keyboards as kb

    markup = kb.all_topics_kb()
    cap = await route(button_data(markup, "ALPHATOPIC"))
    assert "ALPHATOPIC" in cap.text


@pytest.mark.asyncio
async def test_char_user_roles_manage_opens_that_user(seed):
    """Кнопка «Управление ролями» открывает роли ИМЕННО этого участника."""
    import keyboards as kb

    markup = kb.user_edit_kb(seed["user_id"], is_superadmin=True)
    cap = await route(button_data(markup, "Управление ролями"))
    assert "Targetuser" in cap.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "route_builder",
    ["users_list_kb::Targetuser", "groups_list_kb::ALPHAGROUP"],
)
async def test_char_parameterized_route_does_not_reset_fsm(seed, route_builder):
    """[FR-007 / замок асимметрии] Параметризованные маршруты НЕ сбрасывают FSM.

    Это НЕ баг к исправлению, а зафиксированное текущее поведение: сброс живёт
    внутри `if cmd in simple` (services/ui_service.py:279-281) и до
    параметризованных веток не доходит. Миграция обязана сохранить асимметрию
    как есть — расширение сброса было бы изменением поведения вопреки FR-012.
    """
    import keyboards as kb

    builder_name, fragment = route_builder.split("::")
    markup = getattr(kb, builder_name)()
    cap = await route(button_data(markup, fragment))
    assert cap.shown, "экран должен быть показан"
    assert not cap.fsm_was_reset, (
        f"{builder_name}: параметризованный маршрут не сбрасывает FSM сегодня — "
        "не «чинить» (FR-007)"
    )


# --- CHAR-OK: паджинируемые маршруты, чей разбор сегодня корректен ---------


@pytest.mark.asyncio
async def test_char_user_templates_manage_opens_that_user(seed):
    """`user_templates_manage` корректен сегодня — спасён позиционным p[3].

    Держим как эталон: миграция обязана сохранить результат, изменив механизм.
    """
    import keyboards as kb

    markup = kb.user_edit_kb(seed["user_id"], is_superadmin=True)
    cap = await route(button_data(markup, "Состав шаблонов"))
    assert "Targetuser" in cap.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fragment,expected",
    [("Применить шаблон", "ПРИМЕНЕНИЯ"), ("Синхронизировать топик", "СИНХРОНИЗАЦИИ")],
)
async def test_char_tmpl_act_start_keeps_action(seed, fragment, expected):
    """`tmpl_act_start` различает действие apply/sync — корректен сегодня (p[4])."""
    import keyboards as kb

    markup = kb.group_edit_kb(seed["group_id"])
    cap = await route(button_data(markup, fragment))
    assert expected in cap.text


# --- CHAR-OK: справка и защитный возврат -----------------------------------


@pytest.mark.asyncio
async def test_char_help_route_opens_help(seed):
    """Маршрут справки (`help:{key}:{back}`) показывает экран справки."""
    cap = await route("help:templates:manage_groups")
    assert cap.shown
    assert cap.text


@pytest.mark.asyncio
async def test_char_unknown_route_falls_back_safely(seed, caplog):
    """[FR-008] Неизвестный маршрут -> предупреждение в лог + возврат, без исключения."""
    with caplog.at_level("WARNING"):
        cap = await route("this_route_does_not_exist_at_all")

    assert cap.shown, "защитный возврат обязан показать экран"
    assert any("NAVIGATOR" in r.message for r in caplog.records), (
        "неизвестный маршрут обязан оставить предупреждение в логе"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_data,klass",
    [
        ("nonexistent_route:1", "неизвестный префикс"),
        ("mod_topic_groups:abc:3", "нечисловой id -> ValidationError"),
        ("mod_topic_groups:55", "неверная арность -> TypeError"),
        ("mod_topic_groups:55:2:9", "лишний сегмент -> TypeError"),
        ("user_info_5", "старый формат (кнопка из истории чата)"),
        ("mod_topic_groups:55:-1", "отрицательная страница"),
        ("mod_topic_groups:55:abc", "нечисловая страница"),
        ("", "пустая строка"),
        (":", "голый разделитель"),
        ("user_info:", "пустое значение поля"),
    ],
)
async def test_char_malformed_input_degrades_safely(seed, bad_data, klass):
    """[FR-008 / SC-005] Любой класс битого входа -> безопасный возврат.

    Требование — не «показать красивую ошибку», а «не уронить и не увести на
    случайный экран». Исключение наружу не выходит ни в одном классе; логика
    отказа принадлежит `unpack()`, который ловится тем же кортежем
    `(TypeError, ValueError)`, что использует фильтр aiogram (D-1).
    """
    cap = await route(bad_data)
    assert cap.shown, f"{klass}: экран не показан — защитный возврат не сработал"
    assert cap.text, f"{klass}: пустой текст"


@pytest.mark.asyncio
async def test_char_malformed_input_never_reaches_wrong_screen(seed):
    """Битые данные не приводят к экрану ЧУЖОЙ сущности.

    Ровно этот класс и жил в подстрочном матчинге: `mod_topic_groups_55_pg_3`
    открывал топик 3. Теперь непроходящее значение отбраковывается на разборе,
    а не подставляется молча.
    """
    import keyboards as kb

    spy_called = {}

    def _spy(topic_id, page=1, limit=7):
        spy_called["topic_id"] = topic_id
        return kb.moderator_group_list_kb(55, 1)

    with patch("keyboards.moderator_group_list_kb", side_effect=_spy):
        await route("mod_topic_groups:abc:3")

    assert not spy_called, (
        f"битый id дошёл до экрана как topic_id={spy_called.get('topic_id')}"
    )


@pytest.mark.asyncio
async def test_char_unknown_route_message_swallowed_before_onboarding(seed):
    """[FR-008 / характеризация] Текст «Ошибка навигации» теряется до онбординга.

    Защитный возврат зовёт show_admin_dashboard(text="⚠️ Ошибка навигации..."),
    но тот, не найдя в FSM `admin_onboarded`, показывает экран онбординга и
    переданный текст отбрасывает. Это фактическое поведение сегодня; фиксируем
    как есть — «починка» была бы изменением поведения вопреки FR-012.
    """
    cap = await route("this_route_does_not_exist_at_all")
    assert "Ошибка навигации" not in cap.text
    assert "Добро пожаловать" in cap.text
