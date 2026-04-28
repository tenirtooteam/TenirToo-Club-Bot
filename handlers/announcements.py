# Файл: handlers/announcements.py
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from services.callback_guard import safe_callback
from services.permission_service import PermissionService
from services.announcement_service import AnnouncementService
from services.ui_service import UIService
from database import db
import keyboards as kb

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("an"))
async def cmd_quick_announcement(message: types.Message, state: FSMContext):
    """Хендлер быстрой команды анонса."""
    user_id = message.from_user.id
    topic_id = message.message_thread_id or 0
    
    # 1. Проверка прав (Admin или Moderator топика)
    is_admin = PermissionService.is_global_admin(user_id)
    is_mod = PermissionService.is_moderator_of_topic(user_id, topic_id)
    
    if not (is_admin or is_mod):
        # Молча игнорируем или удаляем, чтобы не мусорить
        await UIService.delete_msg(message)
        return

    # 2. Создаем анонс через сервис
    text, ann_id = await AnnouncementService.create_quick_event(message)
    
    if not ann_id:
        # Ошибка парсинга
        await message.answer(text)
        return

    # 3. Публикуем анонс с кнопкой
    from keyboards.announcements_kb import get_announcement_kb
    is_group = (message.chat.type != "private")
    sent = await message.answer(text, reply_markup=get_announcement_kb(ann_id, is_group=is_group))
    
    # 4. Сохраняем ID сообщения в БД для будущего контроля
    db.update_announcement_metadata(ann_id, message.chat.id, sent.message_id)

    # 5. Стерильность: Удаляем сообщение с командой
    await UIService.delete_msg(message)


@router.callback_query(F.data.startswith("ann_join:"))
@safe_callback()
async def announcement_join_handler(callback: types.CallbackQuery, state: FSMContext = None):
    """Универсальный обработчик клика по кнопке анонса."""
    user_id = callback.from_user.id
    ann_id = int(callback.data.split(":")[1])
    
    # 1. Получаем данные анонса
    ann = db.get_announcement(ann_id)
    if not ann:
        await callback.answer("❌ Анонс не найден или удален.", show_alert=True)
        return
        
    ann_type = ann[1]
    target_id = ann[2]
    topic_id = ann[3]

    # 2. Проверка прав доступа (Только члены топика [RA-2])
    if not PermissionService.can_user_write_in_topic(user_id, topic_id):
        await callback.answer("🚫 У вас нет доступа к этому разделу клуба.", show_alert=True)
        return

    # 3. Выполняем действие в зависимости от типа
    if ann_type == "event":
        from services.management_service import ManagementService
        from services.event_service import EventService
        
        # Получаем код действия (1 - иду, 0 - не иду)
        action_code = callback.data.split(":")[-1]
        
        if action_code == "1":
            msg = ManagementService.add_event_participation_action(target_id, user_id)
            if "записаны" in msg:
                await EventService.notify_organizers_of_direct_join(callback.message.bot, target_id, user_id)
        elif action_code == "0":
            msg = ManagementService.remove_event_participation_action(target_id, user_id)
        else:
            # Старый формат (тоггл) - на всякий случай
            _, msg = ManagementService.toggle_event_participation(target_id, user_id)
            
        await callback.answer(msg, show_alert=True)
        
        # Обновляем ВСЕ анонсы этого мероприятия [CC-2]
        await AnnouncementService.refresh_announcements(callback.message.bot, "event", target_id)
    else:
        await callback.answer("🛠 Этот тип анонса пока в разработке.")

from services.event_service import EventService

@router.callback_query(F.data.startswith("event_announce_init:"))
@safe_callback()
async def event_announce_init_handler(callback: types.CallbackQuery, state: FSMContext):
    """Инициализация анонсирования по кнопке из карточки."""
    user_id = callback.from_user.id
    event_id = int(callback.data.split(":")[1])
    
    # 1. Проверка прав [PL-2.2.15]
    if not EventService.can_edit_event(user_id, event_id):
        return await callback.answer("❌ У вас нет прав на анонсирование этого мероприятия.", show_alert=True)
        
    # 2. Для MVP: анонсируем в тот же топик, где находится пользователь
    # или предлагаем выбрать (в будущем).
    # Пока просто анонсируем в топик по умолчанию или текущий.
    target_topic_id = callback.message.message_thread_id or 0
    
    if target_topic_id == 0:
        return await callback.answer("⚠️ Анонсирование доступно только внутри топиков клуба.", show_alert=True)

    success, msg, ann_id = await AnnouncementService.broadcast_event_announcement(
        callback.bot, event_id, target_topic_id, user_id
    )
    
    await callback.answer(msg, show_alert=True)


