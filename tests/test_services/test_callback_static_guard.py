"""[Feature 011] Статический гейт: механизм роутинга не вернётся к строкам.

Запирает SC-001/SC-002/SC-003 на уровне кода, а не намерения: подстрочный
матчинг, позиционный разбор и ручная сборка callback_data должны быть не просто
удалены сегодня, но и не иметь дороги обратно.

Разбор через AST, а не по тексту: комментарии в ui_service.py намеренно цитируют
удалённые конструкции (`"user_info" in cmd`, `int(p[-1])`), и текстовый поиск
поймал бы их как нарушения. Гейт смотрит на код, а не на его описание.

Границы (D-4): проверяется семейство навигатора. `keyboards/event_kb.py` и
`keyboards/announcements_kb.py` обслуживают семейства `event_*` / `ann_*` /
`date_*`, они вне scope и НЕ должны флагаться.
"""

import ast
import io
from pathlib import Path

import pytest

import callbacks as cb

REPO = Path(__file__).resolve().parents[2]

OUT_OF_SCOPE_KEYBOARDS = {"event_kb.py", "announcements_kb.py"}
"""Вне границ фичи (D-4). Тот же класс дефекта, отдельная фича."""


def _parse(rel_path: str) -> ast.Module:
    return ast.parse(io.open(REPO / rel_path, encoding="utf-8").read())


# --- SC-001: выбор маршрута только точным сопоставлением -------------------


def test_sc001_navigator_has_no_substring_route_matching():
    """В навигаторе нет выбора экрана по вхождению подстроки в имя команды.

    Ловит возврат к `if "user_info" in cmd` — конструкции, из-за которой маршрут
    с чужим именем-подстрокой мог перехватить чужой экран.
    """
    tree = _parse("services/ui_service.py")
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        for op, comparator in zip(node.ops, node.comparators):
            if not isinstance(op, ast.In):
                continue
            # `"строка" in <имя>` — матчинг подстрокой по имени маршрута.
            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                if isinstance(comparator, ast.Name) and comparator.id in {"cmd", "callback_data"}:
                    violations.append(f"строка {node.left.value!r} in {comparator.id} (стр. {node.lineno})")
    assert not violations, (
        "Подстрочный матчинг маршрута вернулся в навигатор:\n  " + "\n  ".join(violations)
    )


# --- SC-002: параметры только по имени поля --------------------------------


def test_sc002_navigator_has_no_positional_extraction():
    """В навигаторе нет извлечения параметров по позиции в строке.

    Ловит возврат к `int(p[-1])` / `int(p[3])` — конструкции, из-за которой
    номер страницы приезжал вместо ID сущности (DEF-1), а topic_id и group_id
    менялись местами (DEF-3).
    """
    tree = _parse("services/ui_service.py")
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not (isinstance(node.value, ast.Name) and node.value.id in {"p", "parts"}):
            continue
        idx = node.slice
        is_int_index = isinstance(idx, ast.Constant) and isinstance(idx.value, int)
        is_neg_index = (
            isinstance(idx, ast.UnaryOp)
            and isinstance(idx.op, ast.USub)
            and isinstance(idx.operand, ast.Constant)
        )
        if is_int_index or is_neg_index:
            violations.append(f"{node.value.id}[...] на стр. {node.lineno}")
    assert not violations, (
        "Позиционный разбор маршрута вернулся в навигатор:\n  " + "\n  ".join(violations)
    )


def test_sc002_navigator_does_not_split_pagination_off_the_wire():
    """Номер страницы не отрезается от строки — он объявленное поле (FR-005)."""
    src = io.open(REPO / "services/ui_service.py", encoding="utf-8").read()
    tree = ast.parse(src)
    violations = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "split"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "_pg_"
        ):
            violations.append(f"split('_pg_') на стр. {node.lineno}")
    assert not violations, "\n  ".join(violations)


def test_sc002_paginated_cmds_registry_is_gone():
    """Дублирующий реестр имён страничных команд удалён (FR-005)."""
    from services.ui_service import UIService

    assert not hasattr(UIService, "PAGINATED_CMDS"), (
        "PAGINATED_CMDS вернулся: страничность обязана следовать из поля `page` "
        "объявления маршрута, а не из второго списка имён"
    )


# --- SC-003: producer использует единственное объявление формата -----------


def _leading_literal(node: ast.JoinedStr) -> str:
    """Постоянный префикс f-строки — текст до первой подстановки."""
    if node.values and isinstance(node.values[0], ast.Constant):
        return node.values[0].value
    return ""


def _family_prefixes() -> list[str]:
    return sorted((f.__prefix__ for f in cb.ALL_FACTORIES), key=len, reverse=True)


def _hand_built_family_callbacks(rel_path: str) -> list[str]:
    tree = _parse(rel_path)
    prefixes = _family_prefixes()
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.keyword) or node.arg not in {
            "callback_data", "back_data", "help_back_data",
        }:
            continue
        if not isinstance(node.value, ast.JoinedStr):
            continue
        literal = _leading_literal(node.value)
        for prefix in prefixes:
            if literal == prefix or literal.startswith(prefix + "_"):
                found.append(f"{rel_path}:{node.value.lineno} — f-строка {literal!r} (маршрут {prefix!r})")
                break
    return found


@pytest.mark.parametrize(
    "kb_file",
    [p.name for p in (REPO / "keyboards").glob("*_kb.py") if p.name not in OUT_OF_SCOPE_KEYBOARDS]
    + ["pagination_util.py"],
)
def test_sc003_keyboards_do_not_hand_build_family_callbacks(kb_file):
    """Клавиатуры не собирают данные маршрутов семейства f-строками.

    Ловит рассинхрон producer/consumer в зародыше: ручная f-строка — это вторая
    голова формата, ровно то, ради устранения чего затевалась фича (US2).
    """
    violations = _hand_built_family_callbacks(f"keyboards/{kb_file}")
    assert not violations, (
        "Ручная сборка данных маршрута семейства:\n  " + "\n  ".join(violations)
    )


def test_sc003_out_of_scope_keyboards_are_deliberately_untouched():
    """Границу D-4 держим явной, а не по памяти.

    `event_kb` / `announcements_kb` СЕГОДНЯ собирают колбэки вручную — это
    осознанно вне scope 011. Тест фиксирует, что исключение реально нужно: если
    их однажды мигрируют, он упадёт и напомнит убрать исключение отсюда.
    """
    tree = _parse("keyboards/event_kb.py")
    hand_built = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.keyword) and n.arg == "callback_data"
        and isinstance(n.value, ast.JoinedStr)
    ]
    assert hand_built, (
        "keyboards/event_kb.py больше не собирает колбэки вручную — семейство "
        "event_* мигрировано? Тогда убери его из OUT_OF_SCOPE_KEYBOARDS."
    )
