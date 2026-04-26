from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.pagination_util import add_nav_footer

def get_events_list_kb(events: list, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура списка мероприятий."""
    builder = InlineKeyboardBuilder()
    
    for event in events:
        builder.row(
            InlineKeyboardButton(
                text=f"🏔 {event['title']} ({event['start_date']})",
                callback_data=f"event_view:{event['event_id']}"
            )
        )
        
    builder.row(
        InlineKeyboardButton(text="➕ Создать мероприятие", callback_data="event_create")
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⏳ На модерации", callback_data="event_pending_list")
        )
    
    add_nav_footer(builder, back_data="user_main", help_key="events", help_back_data="event_list")
    return builder.as_markup()

def get_event_card_kb(event_id: int, is_participant: bool, can_edit: bool) -> InlineKeyboardMarkup:
    """Клавиатура карточки мероприятия."""
    builder = InlineKeyboardBuilder()
    
    # Кнопки участия
    if is_participant:
        builder.row(InlineKeyboardButton(text="🚫 Не иду", callback_data=f"event_leave:{event_id}"))
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
    """Клавиатура для администраторов для одобрения мероприятия."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"event_approve:{event_id}"),
        InlineKeyboardButton(text="🛑 Отклонить", callback_data=f"event_reject:{event_id}")
    )
    add_nav_footer(builder, back_data="event_pending_list")
    return builder.as_markup()

def get_event_cancel_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены при создании мероприятия."""
    builder = InlineKeyboardBuilder()
    add_nav_footer(builder, back_data="event_list")
    return builder.as_markup()

def get_audit_log_kb() -> InlineKeyboardMarkup:
    """Клавиатура под лог-сообщением после решения по заявке."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 К списку на модерации", callback_data="event_pending_list")
    return builder.as_markup()
