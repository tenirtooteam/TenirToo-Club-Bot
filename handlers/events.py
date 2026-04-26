import logging
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import keyboards as kb
from services.ui_service import UIService
from services.event_service import EventService
from services.management_service import ManagementService
from services.permission_service import PermissionService

logger = logging.getLogger(__name__)
router = Router()

class EventCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_dates = State()

@router.callback_query(F.data == "event_list")
async def show_events_list(event_or_msg: CallbackQuery | Message, state: FSMContext, custom_text: str = None):
    # [CC-1] Sterile UI: Не используем state.clear(), чтобы не сломать трекинг меню
    await state.set_state(None)
    user_id = event_or_msg.from_user.id
    
    # [CC-3] Данные получаем через EventService или db (GET разрешен)
    events = EventService.get_active_events()
    is_admin = PermissionService.is_global_admin(user_id)
    
    text = custom_text or "🏔 <b>Мероприятия Клуба</b>\nЗдесь вы можете записаться на походы и тренировки."
    # [CC-2] Используем kb фасад
    reply_markup = kb.get_events_list_kb(events, is_admin)
    
    # [CC-4] Используем UIService для отображения меню
    await UIService.sterile_show(state, event_or_msg, text, reply_markup=reply_markup)

@router.callback_query(F.data == "event_pending_list")
async def show_pending_events(callback: CallbackQuery, state: FSMContext):
    """Список мероприятий, ожидающих одобрения."""
    user_id = callback.from_user.id
    # [CC-9] Используем PermissionService
    if not PermissionService.is_global_admin(user_id):
        return await callback.answer("❌ У вас нет прав.", show_alert=True)
        
    await state.set_state(None)
    events = EventService.get_pending_events()
    reply_markup = kb.get_events_list_kb(events, is_admin=True)
    
    await UIService.sterile_show(
        state,
        callback,
        "⏳ <b>Мероприятия на модерации</b>\nВыберите мероприятие для проверки:",
        reply_markup=reply_markup
    )

@router.callback_query(F.data == "event_create")
async def start_event_creation(callback: CallbackQuery, state: FSMContext):
    # [CC-10] Sterile UI: очистка перед началом нового ввода
    await UIService.terminate_input(state, callback.message, reset_state=True)
    
    await UIService.sterile_ask(
        state, 
        callback, 
        "Отлично! Введите <b>Название</b> мероприятия (например, 'Поход на Ала-Арчу'):", 
        EventCreation.waiting_for_title,
        reply_markup=kb.get_event_cancel_kb()
    )

@router.message(EventCreation.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    if not message.text:
        return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста, введите <b>текстовое</b> название мероприятия.")
        
    await state.update_data(title=message.text.strip()[:100])
    # [CC-4] Переход к следующему шагу через UIService.sterile_show (сброс текста промпта)
    await UIService.sterile_show(
        state,
        message,
        "Теперь введите <b>Даты</b> (например, '10-12 Июля' или 'Каждые выходные'):",
        reply_markup=kb.get_event_cancel_kb()
    )
    await state.set_state(EventCreation.waiting_for_dates)

@router.message(EventCreation.waiting_for_dates)
async def process_event_dates(message: Message, state: FSMContext):
    if not message.text:
        return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста, введите <b>текстовое</b> даты мероприятия.")
        
    data = await state.get_data()
    title = data.get("title")
    dates = message.text.strip()[:100]
    user_id = message.from_user.id
    
    is_admin = PermissionService.is_global_admin(user_id)
    
    import config
    # [CC-9] Логика одобрения
    is_approved = 0
    if is_admin and not getattr(config, 'REQUIRE_ADMIN_EVENT_AUDIT', True):
        is_approved = 1
    
    # [CC-3] Все мутации через ManagementService
    event_id = ManagementService.create_event_action(title, dates, user_id, is_approved)
    
    if event_id > 0:
        if is_approved:
            success_text = "✅ <b>Мероприятие успешно создано и опубликовано!</b>"
        else:
            success_text = "⏳ <b>Мероприятие отправлено на модерацию администраторам.</b>"
            # Регистрируем заявку на аудит [CC-1]
            ManagementService.submit_request(user_id, "event_approval", event_id)
            await EventService.notify_admins_for_approval(message.bot, event_id)
            
        await show_events_list(message, state, custom_text=success_text)
    else:
        await UIService.show_temp_message(state, message, "❌ Ошибка при создании мероприятия. Попробуйте еще раз.")
        await show_events_list(message, state)

@router.callback_query(F.data.startswith("event_view:"))
async def view_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    event = EventService.get_event_details(event_id)
    if not event:
        return await callback.answer("❌ Мероприятие не найдено.", show_alert=True)
        
    card_text = EventService.format_event_card(event_id)
    is_participant = EventService.is_event_participant(event_id, user_id)
    can_edit = EventService.can_edit_event(user_id, event_id)
    is_admin = PermissionService.is_global_admin(user_id)
    
    if not event['is_approved'] and is_admin:
        reply_markup = kb.get_event_moderation_kb(event_id)
    else:
        reply_markup = kb.get_event_card_kb(event_id, is_participant, can_edit)
        
    await UIService.sterile_show(state, callback, card_text, reply_markup=reply_markup)

@router.callback_query(F.data.startswith("event_join:"))
async def join_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    if EventService.is_event_participant(event_id, user_id):
        return await callback.answer("⚠️ Вы уже участвуете в этом мероприятии.", show_alert=True)

    # Проверяем, нет ли уже активной заявки [CC-1]
    existing_req = ManagementService.get_user_pending_request_id(user_id, "event_participation", event_id)
    if existing_req:
        return await callback.answer("⏳ Ваша заявка на участие уже находится на рассмотрении.", show_alert=True)

    # Регистрируем заявку на участие [CC-1]
    ManagementService.submit_request(user_id, "event_participation", event_id)
    await callback.answer("✅ Ваша заявка на участие отправлена организаторам!", show_alert=True)
    await view_event(callback, state)

@router.callback_query(F.data.startswith("event_leave:"))
async def leave_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    # [CC-3] Мутация через ManagementService (toggle умеет и то и то)
    success, msg = ManagementService.toggle_event_participation(event_id, callback.from_user.id)
    await callback.answer(msg)
    await view_event(callback, state)

@router.callback_query(F.data.startswith("event_delete:"))
async def delete_event_init(callback: CallbackQuery, state: FSMContext):
    # [CC-5] Confirmation Protocol
    event_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    if not EventService.can_edit_event(user_id, event_id):
        return await callback.answer("❌ У вас нет прав.", show_alert=True)
        
    text, back = UIService.get_confirmation_ui("event_del", event_id)
    await UIService.sterile_show(
        state, callback, text,
        reply_markup=kb.confirmation_kb("event_del", event_id, back)
    )

@router.callback_query(F.data.startswith("event_approve:"))
async def approve_event_handler(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    if not PermissionService.is_global_admin(callback.from_user.id):
        return await callback.answer("❌ Нет прав.", show_alert=True)
        
    # Находим ID заявки [CC-1]
    request_id = ManagementService.get_pending_request_id("event_approval", event_id)
    if not request_id:
        await callback.answer("⚠️ Заявка не найдена. Возможно, она уже была обработана.", show_alert=True)
        return await view_event(callback, state)

    # Разрешаем через универсальный сервис [CC-1] [CC-2]
    success, msg = await ManagementService.resolve_request(callback.bot, request_id, "approved")
    
    if not success:
        await callback.answer(msg, show_alert=True)
        return await view_event(callback, state)

    await callback.answer("✅ Мероприятие одобрено")
    await UIService.delete_msg(callback.message)

@router.callback_query(F.data.startswith("event_reject:"))
async def reject_event_handler(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    if not PermissionService.is_global_admin(callback.from_user.id):
        return await callback.answer("❌ Нет прав.", show_alert=True)
        
    # Находим ID заявки [CC-1]
    request_id = ManagementService.get_pending_request_id("event_approval", event_id)
    if not request_id:
        await callback.answer("⚠️ Заявка не найдена или уже обработана.", show_alert=True)
        return await view_event(callback, state)

    # Разрешаем через универсальный сервис [CC-1] [CC-2]
    # Сервис САМ удалит черновик мероприятия при отклонении event_approval
    success, msg = await ManagementService.resolve_request(callback.bot, request_id, "rejected", comment="Отклонено администратором.")
    
    if not success:
        await callback.answer(msg, show_alert=True)
        return await view_event(callback, state)

    await callback.answer("❌ Заявка отклонена")
    await UIService.delete_msg(callback.message)
