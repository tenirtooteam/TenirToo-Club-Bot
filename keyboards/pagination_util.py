from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import math

import callbacks as cb

def add_nav_footer(builder: InlineKeyboardBuilder, back_data: str = None, include_close: bool = True, help_key: str = None, help_back_data: str = None):
    """
    Универсальный помощник для добавления кнопок навигации в 'подвал' меню [PL-5.1.14].
    Сверхкомпактный режим: [Назад] [Закрыть] [❓]
    """
    nav_buttons = []
    if back_data:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ НАЗАД", callback_data=back_data))

    if include_close:
        nav_buttons.append(InlineKeyboardButton(text="❌ ЗАКРЫТЬ", callback_data="close_menu"))

    if help_key:
        # Логика возврата из справки:
        # 1. Явный путь (help_back_data) - приоритет
        # 2. Путь назад (back_data) - если мы в дочернем меню
        # 3. 'landing' - системный корень как последний рубеж
        back_link = help_back_data or back_data or "landing"

        # [feature 011 / FR-011] Лимит Telegram 64 байта обеспечивает pack():
        # он поднимает ValueError. Прежняя ручная обрезка cb_data[:64] была
        # хуже отказа — она резала строку посередине и выпускала синтаксически
        # целый, но семантически битый маршрут, который молча уходил в fallback.
        # Теперь превышение — громкий отказ на сборке клавиатуры, а не сюрприз
        # у пользователя.
        nav_buttons.append(
            InlineKeyboardButton(text="❓", callback_data=cb.HelpCB(key=help_key, back_data=back_link).pack())
        )

    if nav_buttons:
        builder.row(*nav_buttons)


def build_paginated_menu(
    item_buttons: list[InlineKeyboardButton],
    static_buttons: list[InlineKeyboardButton],
    page: int,
    limit: int,
    page_cb,
    adjust_items: int = 1,
    search_type: str = None, # 'user', 'group', 'topic'
    search_action: str = None, # 'info', 'select', etc.
    search_context: str = None, # Additional data (e.g. topic_id)
    help_key: str = None,
    help_back_data: str = None
):
    """Строит меню со страничной навигацией.

    [feature 011 / FR-005] `page_cb` — ЭКЗЕМПЛЯР объявления маршрута с полем
    `page`, а не строковый префикс. Стрелки получаются как копия этого объекта с
    подменённым номером страницы, поэтому строковой хирургии здесь больше нет.

    Прежний контракт (`callback_prefix: str` + склейка `f"{prefix}_pg_{n}"`) был
    корнем сразу двух дефектов: номер страницы приезжал в навигатор как ID
    сущности (DEF-1), а префикс, сам содержавший `_pg`, ломал разбор целиком
    (DEF-2). Оба исчезают вместе со склейкой.
    """
    builder = InlineKeyboardBuilder()
    start = (page - 1) * limit
    end = start + limit

    # 1. Основной список элементов
    for btn in item_buttons[start:end]:
        builder.button(text=btn.text, callback_data=btn.callback_data)

    builder.adjust(adjust_items)

    # 2. Навигация по страницам (Стрелки)
    nav_arrows = []
    total_items = len(item_buttons)
    total_pages = max(1, math.ceil(total_items / limit))

    def _page_link(target: int) -> str:
        """Тот же маршрут, другая страница — номер меняется как поле."""
        return page_cb.model_copy(update={"page": target}).pack()

    if page > 1:
        nav_arrows.append(InlineKeyboardButton(text="◀️ Пред.", callback_data=_page_link(page - 1)))
    if total_pages > 1:
        nav_arrows.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        nav_arrows.append(InlineKeyboardButton(text="След. ▶️", callback_data=_page_link(page + 1)))

    if nav_arrows:
        builder.row(*nav_arrows)

    # 3. Кнопка поиска
    if search_type and total_items > limit:
        search_cb = f"search_start_{search_type}_{search_action}"
        if search_context:
            search_cb += f"_{search_context}"
        builder.row(InlineKeyboardButton(text="🔎 Поиск", callback_data=search_cb))

    # 4. Статичные функциональные кнопки (фильтруем кнопки навигации и справки)
    footer_back_data = None
    footer_help_key = help_key

    for s_btn in static_buttons:
        # Если в статичных кнопках есть "Назад" или "Закрыть", мы их обработаем в футере
        if s_btn.callback_data:
            if s_btn.callback_data == "close_menu":
                continue
            # [feature 011] Прежде здесь была вторая клауза:
            # `or s_btn.callback_data == callback_prefix` — «кнопка ведёт назад
            # на этот же список». Она удалена вместе со строковым префиксом как
            # мёртвая: проверено runtime-зондом (0 срабатываний на всём прогоне)
            # и статической сверкой всех 16 вызовов паджинатора. Кнопку «Назад»
            # целиком опознаёт текстовая ветка ниже.
            if s_btn.text == "⬅️ НАЗАД":
                footer_back_data = s_btn.callback_data
                continue
            # Если в статичных кнопках есть справка — забираем её ключ в футер.
            # [feature 011] Разбор через объявление формата, а не по префиксу
            # строки: ключ достаётся по имени поля (FR-003).
            if cb.route_prefix(s_btn.callback_data) == cb.HelpCB.__prefix__:
                try:
                    footer_help_key = cb.HelpCB.unpack(s_btn.callback_data).key
                    continue
                except (TypeError, ValueError):
                    pass

        # Остальные (функциональные) кнопки — на всю строку
        builder.row(s_btn)

    # 5. Универсальный футер [PL-5.1.14]
    add_nav_footer(builder, back_data=footer_back_data, help_key=footer_help_key, help_back_data=help_back_data)

    return builder.as_markup()
