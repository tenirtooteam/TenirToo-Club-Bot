from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.pagination_util import add_nav_footer

def get_events_list_kb(events: list, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура списка походов."""
    builder = InlineKeyboardBuilder()
    
    for event in events:
        builder.row(
            InlineKeyboardButton(
                text=f"🏔 {event['title']} ({event['start_date']})",
                callback_data=f"event_view:{event['event_id']}"
            )
        )
        
    builder.row(
        InlineKeyboardButton(text="➕ Создать поход", callback_data="event_create")
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⏳ На модерации", callback_data="event_pending_list")
        )
    
    add_nav_footer(builder, back_data="user_main", help_key="events", help_back_data="event_list")
    return builder.as_markup()

def get_event_card_kb(event_id: int, is_participant: bool, can_edit: bool, has_pending: bool = False, show_actions: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура карточки похода."""
    builder = InlineKeyboardBuilder()
    
    if show_actions:
        # Кнопки участия
        if is_participant:
            builder.row(InlineKeyboardButton(text="🚫 Не иду", callback_data=f"event_leave:{event_id}"))
        elif has_pending:
            builder.row(InlineKeyboardButton(text="🚶 Отменить заявку", callback_data=f"event_cancel_join:{event_id}"))
        else:
            builder.row(InlineKeyboardButton(text="✅ Иду", callback_data=f"event_join:{event_id}"))
            
        # Кнопки редактирования
        if can_edit:
            # Кнопка анонса видна только для одобренных ивентов
            builder.row(InlineKeyboardButton(text="📢 Анонсировать", callback_data=f"event_announce_init:{event_id}"))
            builder.row(
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"event_edit:{event_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"event_delete:{event_id}")
            )
        
    add_nav_footer(builder, back_data="event_list", help_key="events")
    return builder.as_markup()

def get_event_moderation_kb(event_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для администраторов для одобрения похода."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"event_approve:{event_id}"),
        InlineKeyboardButton(text="🛑 Отклонить", callback_data=f"event_reject:{event_id}")
    )
    add_nav_footer(builder, back_data="event_pending_list")
    return builder.as_markup()

def get_event_cancel_kb(back_data: str = "event_list") -> InlineKeyboardMarkup:
    """Клавиатура отмены создания похода (только кнопка Назад)."""
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data=back_data)
    return builder.as_markup()

def get_date_picker_kb(back_data: str = "event_list") -> InlineKeyboardMarkup:
    """Клавиатура с быстрыми датами."""
    from services.date_service import DateService
    builder = InlineKeyboardBuilder()
    
    # Добавляем 4 быстрые кнопки (2х2)
    quick_btns = DateService.get_quick_date_buttons()
    for btn in quick_btns:
        builder.add(btn)
    builder.adjust(2)
    
    # Кнопка ручного ввода [CC-3]
    builder.row(InlineKeyboardButton(text="✍️ Ввести свою дату", callback_data="date_retry"))
    
    # Кнопка отмены/назад в футере
    add_nav_footer(builder, back_data=back_data, help_key="events")
    return builder.as_markup()

def get_date_confirm_kb(iso_start: str, iso_end: str = None, back_data: str = "date_retry") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения после текстового ввода."""
    builder = InlineKeyboardBuilder()
    
    # Если введена одна дата, предлагаем варианты
    if not iso_end:
        builder.button(text="✅ Один день", callback_data=f"date_confirm:{iso_start}:one")
        builder.button(text="🗓 Добавить дату конца", callback_data=f"date_add_end:{iso_start}")
    else:
        builder.button(text="✅ Подтвердить диапазон", callback_data=f"date_confirm:{iso_start}:{iso_end}")
        
    builder.button(text="🔄 Ввести заново", callback_data="date_retry")
    builder.adjust(1)
    
    # Стандартный футер навигации для предотвращения UI Deadlock
    add_nav_footer(builder, back_data=back_data, help_key="events")
    return builder.as_markup()

def get_audit_log_kb() -> InlineKeyboardMarkup:
    """Клавиатура под лог-сообщением после решения по заявке."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 К списку на модерации", callback_data="event_pending_list")
    return builder.as_markup()
