"""[Feature 011] Объявления формата колбэков — единый источник правды (FR-001).

Каждый параметризованный маршрут семейства легаси-навигатора объявлен здесь ровно
один раз. Этот модуль — источник и для построения кнопок (`keyboards/*` через
`.pack()`), и для их разбора (`UIService.generic_navigator` через `.unpack()`,
`handlers/*` через `.filter()`). Формат больше не живёт в двух головах.

Границы (см. spec.md § Границы применимости требований, research.md D-4):
семейства `event_*` / `ann_*` / `date_*` и разбор `search_start_*` / `search_pick_*`
сюда НЕ входят — они разбираются обработчиками напрямую, минуя навигатор, и
мигрируют отдельной фичей.

Архитектура: модуль — листовой узел графа импортов (`R-ARCH-4`). Он не импортирует
ни `services`, ни `handlers`, ни `database`, ни `keyboards`: это чистые объявления
формата, доступные обеим сторонам контракта, но не зависящие ни от одной.

Механика (проверена на aiogram 3.4.1, research.md §1):
- разделитель по умолчанию `:`; префикс не может его содержать;
- `pack()` поднимает `ValueError`, если результат >64 байт — лимит Telegram
  обеспечивает библиотека, вручную длину не считаем (FR-011);
- `unpack()` требует ТОЧНОЙ арности: все поля пакуются всегда, «короткой формы»
  маршрута не существует, поэтому `page` обязателен даже при значении 1;
- отказы `unpack()` покрываются кортежем `(TypeError, ValueError)`, так как
  `pydantic.ValidationError` наследует `ValueError`.
"""

from enum import Enum

from aiogram.filters.callback_data import CallbackData


class TemplateAction(str, Enum):
    """Вид операции над шаблоном доступа.

    Раньше — строковый сегмент на позиции p[3]; теперь параметр с именем.
    """

    APPLY = "apply"
    SYNC = "sync"


# --- Постоянные маршруты ---------------------------------------------------

CONSTANT_ROUTES = frozenset(
    {
        "admin_main",
        "user_main",
        "user_profile_view",
        "roles_dashboard",
        "roles_faq",
        "templates_faq",
        "event_list",
        "event_pending_list",
        "landing",
        "close_menu",
        "ignore",
        "noop",
        "admin_confirm_onboarding",
        "add_group_start",
        "add_user_start",
        "sheets_export_all",
        "sheets_import_all",
    }
)
"""Маршруты без параметров — остаются простыми строками.

Разбору не подвержены, значит и классу ошибок 011 не подвержены (spec.md,
Assumptions). Инвариант C-1: ни один из них не содержит `:` — именно на этом
навигатор отличает постоянный маршрут от параметризованного.
"""


# --- Паджинируемые маршруты ------------------------------------------------
# Номер страницы — объявленный параметр, а не суффикс `_pg_{n}` (FR-005).
# Раньше страничность маршрута хранилась отдельным реестром имён
# (UIService.PAGINATED_CMDS); теперь она следует из наличия поля `page`.


class ManageGroupsCB(CallbackData, prefix="manage_groups"):
    page: int = 1


class ManageUsersCB(CallbackData, prefix="manage_users"):
    page: int = 1


class AllTopicsListCB(CallbackData, prefix="all_topics_list"):
    page: int = 1


class ListUsersRolesCB(CallbackData, prefix="list_users_roles"):
    page: int = 1


class UserTopicsCB(CallbackData, prefix="user_topics"):
    page: int = 1


class ModeratorCB(CallbackData, prefix="moderator"):
    """Панель модератора — список управляемых топиков.

    Раньше жил голой константой, хотя его клавиатура паджинируется: стрелки
    выпускали `moderator_pg_2`, но экран не был в PAGINATED_CMDS, и номер
    страницы молча отбрасывался. Тот же латентный класс, что у `user_topics`.
    """

    page: int = 1


class GroupTopicsListCB(CallbackData, prefix="group_topics_list"):
    group_id: int
    page: int = 1


class ModTopicGroupsCB(CallbackData, prefix="mod_topic_groups"):
    topic_id: int
    page: int = 1


class ModGroupAddListCB(CallbackData, prefix="mod_gr_addlist"):
    topic_id: int
    page: int = 1


class ModUsersManageCB(CallbackData, prefix="mod_users_manage"):
    topic_id: int
    page: int = 1


class ModTopicModeratorsCB(CallbackData, prefix="mod_topic_moderators"):
    topic_id: int
    page: int = 1


class UserTemplatesManageCB(CallbackData, prefix="user_templates_manage"):
    user_id: int
    page: int = 1


class TmplActStartCB(CallbackData, prefix="tmpl_act_start"):
    action: TemplateAction
    group_id: int
    page: int = 1


class TopicAssignCB(CallbackData, prefix="topic_assign"):
    """Выбор топика при выдаче роли.

    Префикс намеренно `topic_assign`, а не прежний `topic_assign_pg`: имя
    маршрута не несёт признак страничности (FR-016). Именно `_pg` внутри старого
    префикса съедался разбором `split("_pg_")[0]` и делал маршрут недостижимым
    (DEF-2).
    """

    user_id: int
    page: int = 1


# --- Вызывающие паджинатора вне семейства навигатора -----------------------
# Экраны, которые разбираются обработчиками напрямую, минуя generic_navigator
# (D-4). В границы фичи они попадают МЕХАНИЧЕСКИ: паджинатор — общий, и его
# контракт сменился, поэтому им нужен `page_cb`, иначе клавиатура не соберётся.
#
# Мигрирует только вход на экран/страницу. Их action-кнопки
# (`topic_add_confirm_*`, `mod_tgl_dir_*`, `search_pick_*`) и разбор этих кнопок
# в обработчиках остаются старым форматом — это отдельная фича.


class AddTopicToCB(CallbackData, prefix="add_topic_to"):
    group_id: int
    page: int = 1


class ModAddUserListCB(CallbackData, prefix="mod_add_user_list"):
    topic_id: int
    page: int = 1


class SearchPageCB(CallbackData, prefix="search_pg"):
    """Страница результатов поиска.

    Префикс сохранён как `search_pg`, а не `search`: `search` — не маршрут, а
    голый префикс паджинатора, тогда как реальные кнопки поиска уже занимают
    пространство имён `search_start_*` / `search_pick_*`. Отдельный префикс
    исключает коллизию с ними при точном сопоставлении.
    """

    page: int = 1


# --- Непаджинируемые параметризованные маршруты ----------------------------


class UserInfoCB(CallbackData, prefix="user_info"):
    user_id: int


class GroupInfoCB(CallbackData, prefix="group_info"):
    group_id: int


class TopicGlobalViewCB(CallbackData, prefix="topic_global_view"):
    topic_id: int


class TopicInGroupCB(CallbackData, prefix="topic_in_group"):
    """Карточка топика в контексте группы.

    Поля названы по назначению. Раньше извлекались как `int(p[-1])` и
    `int(p[-2])` и уезжали в `show_topic_detail(topic_id, group_id)`
    перевёрнутыми — открывалась карточка чужого топика (DEF-3).
    """

    topic_id: int
    group_id: int


class UserTopicInfoCB(CallbackData, prefix="u_topic_info"):
    topic_id: int


class ModTopicSelectCB(CallbackData, prefix="mod_topic_select"):
    topic_id: int


class UserRolesManageCB(CallbackData, prefix="user_roles_manage"):
    user_id: int


class HelpCB(CallbackData, prefix="help", sep="|"):
    """Экран справки с маршрутом возврата.

    Разделитель `|`, а не общий `:`, — вынужденно и осознанно: `back_data`
    хранит УПАКОВАННЫЙ колбэк другого маршрута (например
    `group_topics_list:5:1`), а `pack()` запрещает разделитель внутри значения.
    С `sep=":"` это падало бы с ValueError на любом параметризованном возврате.

    Следствие для навигатора: префикс извлекается разбором по первому вхождению
    `:` ИЛИ `|` — см. `route_prefix()`.
    """

    key: str
    back_data: str


# --- Реестр объявлений -----------------------------------------------------

ALL_FACTORIES = (
    ManageGroupsCB,
    ManageUsersCB,
    AllTopicsListCB,
    ListUsersRolesCB,
    UserTopicsCB,
    ModeratorCB,
    AddTopicToCB,
    ModAddUserListCB,
    SearchPageCB,
    GroupTopicsListCB,
    ModTopicGroupsCB,
    ModGroupAddListCB,
    ModUsersManageCB,
    ModTopicModeratorsCB,
    UserTemplatesManageCB,
    TmplActStartCB,
    TopicAssignCB,
    UserInfoCB,
    GroupInfoCB,
    TopicGlobalViewCB,
    TopicInGroupCB,
    UserTopicInfoCB,
    ModTopicSelectCB,
    UserRolesManageCB,
    HelpCB,
)
"""Все объявления формата семейства. Инвариант R-2: префиксы уникальны."""

PAGINATED_FACTORIES = tuple(f for f in ALL_FACTORIES if "page" in f.model_fields)
"""Объявления с полем `page` — те, что вправе уехать в паджинатор (инвариант P-1)."""

_SEPARATORS = ":|"


def route_prefix(callback_data: str) -> str:
    """Возвращает имя маршрута из строки колбэка.

    Разбирает по первому вхождению любого из используемых разделителей, потому
    что `HelpCB` вынужден жить на `|` (см. его docstring). Для строки без
    разделителей возвращает её саму — то есть постоянный маршрут.
    """
    for i, ch in enumerate(callback_data):
        if ch in _SEPARATORS:
            return callback_data[:i]
    return callback_data
