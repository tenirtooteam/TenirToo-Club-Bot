import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
from services.ui_service import UIService
from services.event_service import EventService
from keyboards.event_kb import (
    get_events_list_kb, get_event_card_kb,
    get_event_moderation_kb, get_event_cancel_kb
)

logger = logging.getLogger(__name__)
router = Router()

class EventCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_dates = State()

@router.callback_query(F.data == "event_list")
async def show_events_list(event_or_msg: CallbackQuery | Message, state: FSMContext, custom_text: str = None):
    await state.clear()
    user_id = event_or_msg.from_user.id
    events = db.get_active_events()
    is_admin = db.is_global_admin(user_id)
    
    text = custom_text or "🏔 <b>Мероприятия Клуба</b>\nЗдесь вы можете записаться на походы и тренировки."
    kb = get_events_list_kb(events, is_admin)
    
    await UIService.show_menu(
        state,
        event_or_msg,
        text,
        reply_markup=kb
    )

@router.callback_query(F.data == "event_pending_list")
async def show_pending_events(callback: CallbackQuery, state: FSMContext):
    """Список мероприятий, ожидающих одобрения."""
    user_id = callback.from_user.id
    if not db.is_global_admin(user_id):
        return await callback.answer("❌ У вас нет прав.", show_alert=True)
        
    await state.clear()
    events = db.get_pending_events()
    kb = get_events_list_kb(events, is_admin=True)
    
    await UIService.show_menu(
        state,
        callback,
        "⏳ <b>Мероприятия на модерации</b>\nВыберите мероприятие для проверки:",
        reply_markup=kb
    )

@router.callback_query(F.data == "event_create")
async def start_event_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EventCreation.waiting_for_title)
    await UIService.show_menu(
        state,
        callback,
        "Отлично! Введите <b>Название</b> мероприятия (например, 'Поход на Ала-Арчу'):",
        reply_markup=get_event_cancel_kb()
    )

@router.message(EventCreation.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    if not message.text:
        return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста, введите <b>текстовое</b> название мероприятия.")
        
    await state.update_data(title=message.text.strip()[:100])
    await state.set_state(EventCreation.waiting_for_dates)
    
    await UIService.show_menu(
        state,
        message,
        "Теперь введите <b>Даты</b> (например, '10-12 Июля' или 'Каждые выходные'):",
        reply_markup=get_event_cancel_kb()
    )

@router.message(EventCreation.waiting_for_dates)
async def process_event_dates(message: Message, state: FSMContext):
    if not message.text:
        return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста, введите <b>текстовые</b> даты мероприятия.")
        
    data = await state.get_data()
    title = data.get("title")
    dates = message.text.strip()[:100]
    user_id = message.from_user.id
    
    is_admin = db.is_global_admin(user_id)
    
    import config
    # Если аудит админов выключен, то админы сразу получают is_approved = 1. Иначе 0.
    # Обычные юзеры всегда 0.
    if is_admin and not getattr(config, 'REQUIRE_ADMIN_EVENT_AUDIT', True):
        is_approved = 1
    else:
        is_approved = 0
    
    event_id = db.create_event(title, dates, "", user_id, is_approved)
    
    if event_id > 0:
        db.add_event_participant(event_id, user_id)
        db.add_event_lead(event_id, user_id)
        
        if is_approved:
            success_text = "✅ <b>Мероприятие успешно создано и опубликовано!</b>"
        else:
            success_text = "⏳ <b>Мероприятие отправлено на модерацию администраторам.</b>"
            await EventService.notify_admins_for_approval(message.bot, event_id)
            
        await show_events_list(message, state, custom_text=success_text)
    else:
        # При ошибке — выходим из FSM и шлем меню с ошибкой
        await UIService.finish_input(state, message, reset_state=True)
        await show_events_list(message, state, custom_text="❌ Ошибка при создании мероприятия. Попробуйте еще раз.")

@router.callback_query(F.data.startswith("event_view:"))
async def view_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    event = db.get_event_details(event_id)
    if not event:
        return await callback.answer("❌ Мероприятие не найдено.", show_alert=True)
        
    card_text = EventService.format_event_card(event_id)
    is_participant = db.is_event_participant(event_id, user_id)
    can_edit = EventService.can_edit_event(user_id, event_id)
    is_admin = db.is_global_admin(user_id)
    
    # Если мероприятие на модерации и смотрит админ — даем кнопки модерации
    if not event['is_approved'] and is_admin:
        kb = get_event_moderation_kb(event_id)
    else:
        kb = get_event_card_kb(event_id, is_participant, can_edit)
        
    await UIService.show_menu(state, callback, card_text, reply_markup=kb)

@router.callback_query(F.data.startswith("event_join:"))
async def join_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    db.add_event_participant(event_id, callback.from_user.id)
    # Здесь в будущем будет хук Google Sheets
    await view_event(callback, state)

@router.callback_query(F.data.startswith("event_leave:"))
async def leave_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    db.remove_event_participant(event_id, callback.from_user.id)
    # Здесь в будущем будет хук Google Sheets
    await view_event(callback, state)

@router.callback_query(F.data.startswith("event_delete:"))
async def delete_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    if EventService.can_edit_event(user_id, event_id):
        db.delete_event(event_id)
        await callback.answer("🗑 Мероприятие удалено.", show_alert=True)
        await show_events_list(callback, state)
    else:
        await callback.answer("❌ У вас нет прав.", show_alert=True)

@router.callback_query(F.data.startswith("event_approve:"))
async def approve_event_handler(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    if not db.is_global_admin(callback.from_user.id):
        return await callback.answer("❌ Нет прав.", show_alert=True)
        
    if db.approve_event(event_id):
        await callback.message.edit_text(callback.message.html_text + "\n\n✅ <b>Одобрено</b>", reply_markup=None, parse_mode="HTML")
        await callback.answer("✅ Мероприятие опубликовано.")
    else:
        await callback.answer("❌ Ошибка при одобрении.", show_alert=True)

@router.callback_query(F.data.startswith("event_reject:"))
async def reject_event_handler(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    if not db.is_global_admin(callback.from_user.id):
        return await callback.answer("❌ Нет прав.", show_alert=True)
        
    db.delete_event(event_id)
    await callback.message.edit_text(callback.message.html_text + "\n\n❌ <b>Отклонено</b>", reply_markup=None, parse_mode="HTML")
    await callback.answer("❌ Мероприятие отклонено и удалено.")
