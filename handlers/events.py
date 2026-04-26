import logging
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
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
    editing_title = State()
    editing_dates = State()

@router.callback_query(F.data == "event_list")
async def show_events_list(event_or_msg: CallbackQuery | Message, state: FSMContext, custom_text: str = None):
    # [CP-3.3] Sterile UI: Не используем state.clear(), чтобы не сломать трекинг меню
    await state.set_state(None)
    user_id = event_or_msg.from_user.id
    
    # [PL-6.7] Данные получаем через EventService или db (GET разрешен)
    events = EventService.get_active_events()
    is_admin = PermissionService.is_global_admin(user_id)
    
    text = custom_text or "🏔 <b>Мероприятия Клуба</b>\nЗдесь вы можете записаться на походы и тренировки."
    # [PL-5.1.13] Используем kb фасад
    reply_markup = kb.get_events_list_kb(events, is_admin)
    
    # [PL-5.1.8] Используем UIService для отображения меню
    await UIService.sterile_show(state, event_or_msg, text, reply_markup=reply_markup)

@router.callback_query(F.data == "event_pending_list")
async def show_pending_events(callback: CallbackQuery, state: FSMContext):
    """Список мероприятий, ожидающих одобрения."""
    user_id = callback.from_user.id
    # [PL-7.1] Используем PermissionService
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
    # [PL-5.1.4] Sterile UI: очистка перед началом нового ввода
    await UIService.terminate_input(state, callback.message, reset_state=True)
    
    # [PL-5.1.11] Sterile Ask
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
        
    # [PL-6.7] Санитизация делегирована сервису
    await state.update_data(title=message.text)
    # [PL-5.1.8] Переход к следующему шагу через UIService.sterile_show
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
    dates = message.text
    user_id = message.from_user.id
    
    is_admin = PermissionService.is_global_admin(user_id)
    
    import config
    # [PL-7.1] Логика одобрения
    is_approved = 0
    if is_admin and not getattr(config, 'REQUIRE_ADMIN_EVENT_AUDIT', True):
        is_approved = 1
    
    # [PL-6.7] Все мутации через ManagementService
    event_id = ManagementService.create_event_action(title, dates, user_id, is_approved)
    
    if event_id > 0:
        if is_approved:
            success_text = "✅ <b>Мероприятие успешно создано и опубликовано!</b>"
        else:
            success_text = "⏳ <b>Мероприятие отправлено на модерацию администраторам.</b>"
            # Регистрируем заявку на аудит [PL-8.1]
            ManagementService.submit_request(user_id, "event_approval", event_id)
            await EventService.notify_admins_for_approval(message.bot, event_id)
            
        await show_events_list(message, state, custom_text=success_text)
    else:
        await UIService.show_temp_message(state, message, "❌ Ошибка при создании мероприятия. Попробуйте еще раз.")
        await show_events_list(message, state)

@router.callback_query(F.data.startswith("event_view:"))
async def view_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    await show_event_card(callback, event_id, state)

async def show_event_card(event_or_msg: CallbackQuery | Message, event_id: int, state: FSMContext):
    """Универсальный помощник для показа карточки мероприятия."""
    user_id = event_or_msg.from_user.id
    event = EventService.get_event_details(event_id)
    if not event:
        if isinstance(event_or_msg, CallbackQuery):
            await event_or_msg.answer("❌ Мероприятие не найдено.", show_alert=True)
        return

    card_text = EventService.format_event_card(event_id)
    is_participant = EventService.is_event_participant(event_id, user_id)
    can_edit = EventService.can_edit_event(user_id, event_id)
    is_admin = PermissionService.is_global_admin(user_id)
    
    if not event['is_approved'] and is_admin:
        reply_markup = kb.get_event_moderation_kb(event_id)
    else:
        reply_markup = kb.get_event_card_kb(event_id, is_participant, can_edit)
        
    await UIService.sterile_show(state, event_or_msg, card_text, reply_markup=reply_markup)

@router.callback_query(F.data.startswith("event_edit:"))
async def edit_event_init(callback: CallbackQuery, state: FSMContext):
    """Начало процесса редактирования."""
    event_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    if not EventService.can_edit_event(user_id, event_id):
        return await callback.answer("❌ У вас нет прав на редактирование.", show_alert=True)
        
    await state.update_data(edit_event_id=event_id)
    await state.set_state(EventCreation.editing_title)
    
    await UIService.sterile_show(
        state, callback, 
        "📝 <b>Редактирование мероприятия</b>\n\nВведите новое название или пришлите <code>/cancel</code> для отмены.",
        reply_markup=kb.get_event_cancel_kb()
    )

@router.message(EventCreation.editing_title)
async def process_editing_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if title.startswith("/"): return # Игнорируем команды
    
    await state.update_data(new_title=title)
    await state.set_state(EventCreation.editing_dates)
    
    await message.answer(
        f"✅ Название принято: <b>{title}</b>\n\nТеперь введите новые даты (например: 15-20 мая) или пришлите <code>/skip</code>, чтобы оставить прежние.",
        reply_markup=kb.get_event_cancel_kb()
    )

@router.message(EventCreation.editing_dates)
async def process_editing_dates(message: Message, state: FSMContext):
    dates = message.text.strip()
    if dates.startswith("/"):
        if dates == "/skip":
            data = await state.get_data()
            event = db.get_event_details(data['edit_event_id'])
            dates = event['start_date']
        else:
            return

    data = await state.get_data()
    event_id = data['edit_event_id']
    new_title = data['new_title']
    
    # [PL-6.7] Мутация через базу
    db.update_event_details(event_id, new_title, dates, "") # end_date пустой пока
    
    await state.clear()
    await message.answer("✅ <b>Изменения сохранены!</b>")
    # Возвращаемся в карточку
    await show_event_card(message, event_id, state)

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
    # [PL-6.7] Мутация через ManagementService
    success, msg = ManagementService.toggle_event_participation(event_id, callback.from_user.id)
    await callback.answer(msg)
    await view_event(callback, state)

@router.callback_query(F.data.startswith("event_delete:"))
async def delete_event_init(callback: CallbackQuery, state: FSMContext):
    # [PL-5.1.10] Confirmation Protocol
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
        
    # Находим ID заявки [PL-8.1]
    request_id = ManagementService.get_pending_request_id("event_approval", event_id)
    if not request_id:
        await callback.answer("⚠️ Заявка не найдена. Возможно, она уже была обработана.", show_alert=True)
        return await view_event(callback, state)
 
    # Разрешаем через универсальный сервис [PL-8.2]
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
        
    # Находим ID заявки [PL-8.1]
    request_id = ManagementService.get_pending_request_id("event_approval", event_id)
    if not request_id:
        await callback.answer("⚠️ Заявка не найдена или уже обработана.", show_alert=True)
        return await view_event(callback, state)

    # Разрешаем через универсальный сервис [PL-8.2]
    # Сервис САМ удалит черновик мероприятия при отклонении event_approval
    success, msg = await ManagementService.resolve_request(callback.bot, request_id, "rejected", comment="Отклонено администратором.")
    
    if not success:
        await callback.answer(msg, show_alert=True)
        return await view_event(callback, state)

    await callback.answer("❌ Заявка отклонена")
    await UIService.delete_msg(callback.message)
