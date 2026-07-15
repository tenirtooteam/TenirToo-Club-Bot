"""[Feature 011 / US2] Контракт объявлений формата колбэков.

Проверяет инварианты из contracts/callback-routes.md и data-model.md.
Инвариант R-1 (полнота реестра навигатора) появится в T028, когда реестр
будет собран целиком.
"""

import pytest

import callbacks as cb
from callbacks import (
    ALL_FACTORIES,
    CONSTANT_ROUTES,
    PAGINATED_FACTORIES,
    HelpCB,
    TemplateAction,
    route_prefix,
)

MAX_CALLBACK_BYTES = 64
"""Лимит Telegram на callback_data."""


def _max_value(field_name: str, annotation):
    """Максимальное ожидаемое значение поля — для проверки лимита длины.

    ID топиков/групп/пользователей: Telegram user_id укладывается в 10 знаков,
    берём заведомо больший запас. Страницы — трёхзначные с запасом.
    """
    if annotation is TemplateAction:
        return max(TemplateAction, key=lambda a: len(a.value))
    if field_name == "page":
        return 999
    if field_name == "back_data":
        # Худший случай: вложен упакованный параметризованный маршрут.
        return "group_topics_list:999999:999"
    if field_name == "key":
        return "moderator_tools"
    return 9999999999


def _maximal_instance(factory):
    """Экземпляр фабрики с максимальными ожидаемыми значениями всех полей."""
    values = {
        name: _max_value(name, field.annotation)
        for name, field in factory.model_fields.items()
    }
    return factory(**values)


# --- R-1: полнота реестра навигатора ---------------------------------------

# Фабрики, которые обслуживает НЕ навигатор, а обработчики напрямую: в границы
# фичи они попали механически, как вызывающие общего паджинатора (D-4).
EXTERNAL_FACTORIES = {cb.AddTopicToCB, cb.ModAddUserListCB, cb.SearchPageCB}

NAVIGATOR_FACTORIES = [f for f in ALL_FACTORIES if f not in EXTERNAL_FACTORIES]


def test_r1_every_navigator_factory_is_registered():
    """[R-1] Каждое объявление семейства присутствует в реестре ровно один раз.

    Ловит фабрику, которую объявили и забыли подключить: без реестра она молча
    уходила бы в защитный возврат вместо своего экрана.
    """
    from services.ui_service import _ROUTE_REGISTRY

    missing = [f.__name__ for f in NAVIGATOR_FACTORIES if f.__prefix__ not in _ROUTE_REGISTRY]
    assert not missing, f"Объявлены, но не подключены к навигатору: {missing}"


def test_r1_registry_has_no_stray_entries():
    """В реестре нет записей без объявления в callbacks.py."""
    from services.ui_service import _ROUTE_REGISTRY

    declared = {f.__prefix__ for f in ALL_FACTORIES}
    stray = set(_ROUTE_REGISTRY) - declared
    assert not stray, f"В реестре записи без объявления: {stray}"


def test_r1_registry_factory_matches_its_prefix():
    """Ключ реестра совпадает с префиксом лежащей под ним фабрики."""
    from services.ui_service import _ROUTE_REGISTRY

    for prefix, (factory, _render) in _ROUTE_REGISTRY.items():
        assert factory.__prefix__ == prefix, (
            f"Реестр: ключ {prefix!r} указывает на {factory.__name__} "
            f"с префиксом {factory.__prefix__!r}"
        )


def test_external_factories_are_not_navigator_routes():
    """Вне-семейные фабрики намеренно НЕ в реестре — их разбирают обработчики.

    Держит границу D-4 явной: если такую фабрику однажды подключат к навигатору,
    это будет осознанное расширение scope, а не случайность.
    """
    from services.ui_service import _ROUTE_REGISTRY

    leaked = [f.__name__ for f in EXTERNAL_FACTORIES if f.__prefix__ in _ROUTE_REGISTRY]
    assert not leaked, f"Вне-семейные фабрики просочились в реестр навигатора: {leaked}"


# --- R-2: уникальность префиксов -------------------------------------------


def test_r2_prefixes_are_unique():
    """[R-2] Два маршрута не могут делить префикс.

    Это и есть гарантия невозможности коллизии имён, которую допускал
    подстрочный матчинг: `"user_info" in cmd` срабатывал на чужом маршруте.
    """
    prefixes = [f.__prefix__ for f in ALL_FACTORIES]
    duplicates = {p for p in prefixes if prefixes.count(p) > 1}
    assert not duplicates, f"Префиксы повторяются: {duplicates}"


def test_r2_prefix_has_no_separator():
    """Префикс не содержит разделителя — иначе разбор неоднозначен."""
    for f in ALL_FACTORIES:
        assert f.__separator__ not in f.__prefix__, (
            f"{f.__name__}: префикс {f.__prefix__!r} содержит разделитель"
        )


# --- C-1: постоянные маршруты отличимы от параметризованных ----------------


def test_c1_constant_routes_have_no_separator():
    """[C-1] Ни один постоянный маршрут не содержит `:` или `|`.

    На этом навигатор отличает постоянный маршрут от параметризованного: строка
    без разделителя — константа. Нарушение этого инварианта ломает разграничение.
    """
    for name in CONSTANT_ROUTES:
        assert route_prefix(name) == name, (
            f"Постоянный маршрут {name!r} содержит разделитель — разграничение сломано"
        )


def test_c1_constant_routes_do_not_collide_with_factories():
    """Имя постоянного маршрута не совпадает с префиксом фабрики."""
    prefixes = {f.__prefix__ for f in ALL_FACTORIES}
    collisions = prefixes & set(CONSTANT_ROUTES)
    assert not collisions, (
        f"Маршрут объявлен и константой, и фабрикой одновременно: {collisions}"
    )


# --- P-1: контракт паджинатора ---------------------------------------------


def test_p1_paginated_factories_have_page_field():
    """[P-1] Каждая фабрика для паджинатора несёт поле `page`."""
    for f in PAGINATED_FACTORIES:
        assert "page" in f.model_fields, f"{f.__name__}: нет поля page"


def test_p1_paginated_registry_covers_every_paginator_caller():
    """Страничность следует из поля, а не из отдельного реестра имён (FR-005).

    17 = 13 маршрутов семейства навигатора + 4, попавшие в границы механически
    как вызывающие общего паджинатора (`moderator`, `add_topic_to`,
    `mod_add_user_list`, `search_pg`). Счётчик держит инвентарь честным: если
    появится новый вызывающий без фабрики, паджинатор не соберётся.
    """
    assert len(PAGINATED_FACTORIES) == 17, (
        f"Ожидалось 17 паджинируемых маршрутов, объявлено {len(PAGINATED_FACTORIES)}"
    )


# --- FR-011: лимит Telegram 64 байта ---------------------------------------


@pytest.mark.parametrize("factory", ALL_FACTORIES, ids=lambda f: f.__name__)
def test_fr011_pack_fits_telegram_limit(factory):
    """[FR-011] `pack()` не поднимает на максимальных значениях полей.

    Проверяем именно «pack() не падает», а не считаем длину руками: лимит
    обеспечивает библиотека (research.md §1), и она же — источник правды.
    """
    instance = _maximal_instance(factory)
    try:
        packed = instance.pack()
    except ValueError as e:
        pytest.fail(f"{factory.__name__}: pack() не уложился в лимит: {e}")
    assert len(packed.encode()) <= MAX_CALLBACK_BYTES


# --- Roundtrip -------------------------------------------------------------


@pytest.mark.parametrize("factory", ALL_FACTORIES, ids=lambda f: f.__name__)
def test_roundtrip_preserves_fields(factory):
    """`unpack(pack(x)) == x` — producer и consumer не могут разойтись (US2)."""
    original = _maximal_instance(factory)
    restored = factory.unpack(original.pack())
    assert restored == original


# --- route_prefix ----------------------------------------------------------


@pytest.mark.parametrize("factory", ALL_FACTORIES, ids=lambda f: f.__name__)
def test_route_prefix_recovers_declared_prefix(factory):
    """Навигатор обязан доставать имя маршрута из любой упакованной строки."""
    packed = _maximal_instance(factory).pack()
    assert route_prefix(packed) == factory.__prefix__


def test_route_prefix_handles_help_pipe_separator():
    """`HelpCB` живёт на `|`, но префикс из него достаётся так же."""
    packed = HelpCB(key="topics", back_data="group_topics_list:5:1").pack()
    assert route_prefix(packed) == "help"


def test_help_survives_nested_packed_callback():
    """Маршрут возврата справки хранит упакованный колбэк с двоеточиями.

    Причина, по которой HelpCB не может жить на общем `:`: значение поля не
    вправе содержать разделитель своей же фабрики.
    """
    nested = "group_topics_list:999:2"
    restored = HelpCB.unpack(HelpCB(key="topics", back_data=nested).pack())
    assert restored.back_data == nested


# --- Enum-параметр ---------------------------------------------------------


def test_template_action_roundtrips_as_named_field():
    """Вид операции над шаблоном — именованный параметр, а не позиция p[3]."""
    packed = cb.TmplActStartCB(
        action=TemplateAction.SYNC, group_id=42, page=3
    ).pack()
    restored = cb.TmplActStartCB.unpack(packed)
    assert restored.action == TemplateAction.SYNC
    assert restored.group_id == 42
    assert restored.page == 3


# --- Отказы unpack ---------------------------------------------------------


@pytest.mark.parametrize(
    "bad,reason",
    [
        ("mod_topic_groups:abc:3", "нечисловой id -> ValidationError"),
        ("mod_topic_groups:55", "неверная арность -> TypeError"),
        ("mod_topic_groups:55:2:9", "лишний сегмент -> TypeError"),
        ("other_route:55:2", "чужой префикс -> ValueError"),
    ],
)
def test_unpack_failures_are_covered_by_known_tuple(bad, reason):
    """Все отказы `unpack()` ловятся кортежем `(TypeError, ValueError)`.

    Тот же кортеж использует CallbackQueryFilter внутри aiogram, поэтому
    расхождение «фильтр пропустил / навигатор упал» невозможно (D-1).
    """
    with pytest.raises((TypeError, ValueError)):
        cb.ModTopicGroupsCB.unpack(bad)


def test_old_format_does_not_unpack():
    """Кнопка старого формата не притворяется валидным маршрутом (C-7).

    `user_info_5` обязан деградировать в «неизвестный маршрут», а не разобраться
    во что-то похожее на правду.
    """
    with pytest.raises((TypeError, ValueError)):
        cb.UserInfoCB.unpack("user_info_5")
