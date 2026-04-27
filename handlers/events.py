import logging
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import db
import keyboards as kb
from services.ui_service import UIService
from services.callback_guard import safe_callback
from services.event_service import EventService
from services.management_service import ManagementService
from services.permission_service import PermissionService
from services.date_service import DateService

logger = logging.getLogger(__name__)
router = Router()

class EventCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_dates = State()
    confirm_date = State()
    waiting_for_end_date = State()
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
        reply_markup=kb.get_event_cancel_kb() # Только отмена на первом шаге
    )

@router.message(EventCreation.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    if not message.text:
        return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста, введите <b>текстовое</b> название мероприятия.")
        
    # [PL-6.7] Санитизация делегирована сервису
    await state.update_data(title=message.text)
    
    # [PL-5.1.16] Heartfelt Ask with Examples
    text = (
        "📅 <b>Когда идем?</b>\n\n"
        "Выбери дату на кнопках или введи текстом.\n"
        "<i>Примеры: \"15 мая\", \"Завтра\", \"10-15 июня\"</i>"
    )
    
    await UIService.sterile_show(
        state,
        message,
        text,
        reply_markup=kb.get_date_picker_kb()
    )
    await state.set_state(EventCreation.waiting_for_dates)

@router.message(EventCreation.waiting_for_dates)
async def process_event_dates(message: Message, state: FSMContext):
    if not message.text:
        return await UIService.show_temp_message(state, message, "⚠️ Пожалуйста, введите <b>дату</b> текстом или выберите на кнопках.")
        
    human, iso_start, iso_end = DateService.parse_smart_date(message.text)
    
    if not iso_start:
        # Если не распарсили - сохраняем как текст, но предупреждаем
        await state.update_data(dates=human, start_iso=None, end_iso=None)
        text = (
            f"⚠️ Не удалось распознать точную дату в \"{human}\".\n"
            "Это мероприятие <b>не попадет</b> в Google Календарь автоматически.\n\n"
            "Всё равно продолжить?"
        )
        await UIService.sterile_show(
            state,
            message,
            text,
            reply_markup=kb.get_date_confirm_kb(iso_start=None)
        )
        return

    await state.update_data(dates=human, start_iso=iso_start, end_iso=iso_end)
    
    text = f"🤖 Я распознал дату: <b>{human}</b>\n\nПодтвердите или измените:"
    await UIService.sterile_show(state, message, text, reply_markup=kb.get_date_confirm_kb(iso_start, iso_end))
    await state.set_state(EventCreation.confirm_date)

@router.callback_query(F.data.startswith("date_preset:"))
@safe_callback()
async def process_date_preset(callback: CallbackQuery, state: FSMContext):
    iso_date = callback.data.split(":")[1]
    # Получаем человеческое название для ISO даты
    human, _, _ = DateService.parse_smart_date(iso_date)
    
    await state.update_data(dates=human, start_iso=iso_date, end_iso=None)
    await UIService.sterile_show(
        state,
        callback,
        f"✅ Выбрано: <b>{human}</b>\n\nЭто мероприятие на один день или будет дата окончания?",
        reply_markup=kb.get_date_confirm_kb(iso_date, None)
    )
    await state.set_state(EventCreation.confirm_date)

@router.callback_query(F.data == "date_retry")
@safe_callback()
async def process_date_retry(callback: CallbackQuery, state: FSMContext):
    await UIService.sterile_show(
        state,
        callback,
        "📅 Введите дату заново.\n<i>Пример: 15 мая или 10-15 июня</i>",
        reply_markup=kb.get_date_picker_kb()
    )
    await state.set_state(EventCreation.waiting_for_dates)

@router.callback_query(F.data.startswith("date_confirm:"))
@safe_callback()
async def process_date_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    parts = callback.data.split(":")
    iso_start = parts[1] if parts[1] != "None" else None
    iso_end = parts[2] if parts[2] not in ["one", "None"] else None
    # Разделяем человеческие даты для корректного хранения [CC-2]
    user_id = callback.from_user.id
    edit_id = data.get("edit_event_id")
    dates = data.get("dates")

    if iso_end:
        if " - " in dates:
            s_human, e_human = dates.split(" - ", 1)
        elif "-" in dates:
            s_human, e_human = dates.split("-", 1)
        else:
            s_human, e_human = dates, None
    else:
        s_human = dates
        e_human = None

    if edit_id:
        # FLOW: Editing [CC-1]
        new_title = data.get("new_title")
        db.update_event_details(edit_id, new_title, s_human, e_human, iso_start, iso_end)
        await state.clear()
        await UIService.sterile_show(state, callback, "✅ <b>Изменения сохранены!</b>")
        # Показываем карточку, так как при редактировании нет аудита
        await show_event_card(callback, edit_id, state)
    else:
        # FLOW: Creation [CC-1]
        title = data.get("title")
        event_id = db.create_event(
            title=title,
            start_date=s_human,
            end_date=e_human, 
            creator_id=user_id,
            is_approved=0,
            start_iso=iso_start,
            end_iso=iso_end
        )
        
        if event_id > 0:
            db.add_event_lead(event_id, user_id)
            ManagementService.submit_request(user_id, "event_approval", event_id)
            await EventService.notify_admins_for_approval(callback.message.bot, event_id)
            
            await state.clear()
            await UIService.sterile_show(
                state,
                callback,
                f"🚀 <b>Мероприятие создано и отправлено на модерацию!</b>\n\n"
                f"Когда администраторы одобрят его, вы получите уведомление.",
                reply_markup=kb.simple_back_kb("event_list")
            )
        else:
            await callback.answer("❌ Ошибка базы данных", show_alert=True)

@router.callback_query(F.data.startswith("date_add_end:"))
@safe_callback()
async def process_date_add_end_start(callback: CallbackQuery, state: FSMContext):
    await UIService.sterile_ask(
        state, 
        callback, 
        "⏳ Введите <b>дату окончания</b> (например: 20 мая):",
        state_to_set=EventCreation.waiting_for_end_date,
        reply_markup=kb.get_event_cancel_kb()
    )

@router.message(EventCreation.waiting_for_end_date)
async def process_event_end_date(message: Message, state: FSMContext):
    human_end, iso_end, _ = DateService.parse_smart_date(message.text)
    if not iso_end:
        return await message.answer("⚠️ Не удалось распознать дату. Попробуй еще раз (например: 20 мая):")
        
    data = await state.get_data()
    start_human = data.get("dates")
    iso_start = data.get("start_iso")
    
    new_human = f"{start_human} - {human_end}"
    await state.update_data(dates=new_human, end_iso=iso_end)
    
    await UIService.sterile_show(
        state,
        message,
        f"✅ Период установлен: <b>{new_human}</b>\n\nВсё верно?",
        reply_markup=kb.get_date_confirm_kb(iso_start, iso_end)
    )
    await state.set_state(EventCreation.confirm_date)

@router.callback_query(F.data.startswith("event_view:"))
@safe_callback()
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
@safe_callback()
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
        reply_markup=kb.get_event_cancel_kb() # [CP-3.11] Изолируем ввод от функциональных кнопок
    )

@router.message(EventCreation.editing_title)
async def process_editing_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if title.startswith("/"): return # Игнорируем команды
    
    await state.update_data(new_title=title)
    await state.set_state(EventCreation.editing_dates)
    
    await UIService.sterile_show(
        state,
        message,
        f"✅ Название принято: <b>{title}</b>\n\nТеперь введите новые даты (например: 15 мая) или выбери на кнопках.\nПришли /skip, чтобы оставить прежние.",
        reply_markup=kb.get_date_picker_kb()
    )

@router.message(EventCreation.editing_dates)
async def process_editing_dates(message: Message, state: FSMContext):
    dates_input = message.text.strip()
    if dates_input.startswith("/") and dates_input != "/skip":
        return

    data = await state.get_data()
    event_id = data['edit_event_id']
    new_title = data['new_title']
    
    if dates_input == "/skip":
        event = db.get_event_details(event_id)
        dates = event['start_date']
        start_iso = event['start_iso']
        end_iso = event['end_iso']
    else:
        human, start_iso, end_iso = DateService.parse_smart_date(dates_input)
        dates = human

    if end_iso:
        if " - " in dates:
            s_human, e_human = dates.split(" - ", 1)
        elif "-" in dates:
            s_human, e_human = dates.split("-", 1)
        else:
            s_human, e_human = dates, None
    else:
        s_human = dates
        e_human = None

    await state.update_data(dates=dates, start_iso=start_iso, end_iso=end_iso)
    
    text = f"🤖 Я распознал дату: <b>{dates}</b>\n\nПодтвердите или измените:"
    await UIService.sterile_show(state, message, text, reply_markup=kb.get_date_confirm_kb(start_iso, end_iso))
    await state.set_state(EventCreation.confirm_date)

@router.callback_query(F.data.startswith("event_join:"))
@safe_callback()
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
@safe_callback()
async def leave_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    # [PL-6.7] Мутация через ManagementService
    success, msg = ManagementService.toggle_event_participation(event_id, callback.from_user.id)
    await callback.answer(msg)
    await view_event(callback, state)

@router.callback_query(F.data.startswith("event_delete:"))
@safe_callback()
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
@safe_callback()
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
@safe_callback()
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
