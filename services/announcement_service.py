# Файл: services/announcement_service.py
import logging
from aiogram import types
from database import db
from services.management_service import ManagementService

logger = logging.getLogger(__name__)

class AnnouncementService:
    @staticmethod
    async def create_quick_event(message: types.Message):
        """
        Парсит команду /an и создает быстрое мероприятие с анонсом.
        Формат: /an Заголовок\nОписание (опционально)
        """
        user_id = message.from_user.id
        topic_id = message.message_thread_id or 0 # 0 если не в топике (редко)
        
        # 1. Извлекаем текст (убираем саму команду)
        full_text = message.text.replace("/an", "", 1).strip()
        if not full_text:
            return "❌ Ошибка: Введите текст анонса. Пример: <code>/an Заголовок\nОписание</code>", None

        # 2. Парсим Заголовок и Описание
        lines = full_text.split("\n", 1)
        title = lines[0].strip()[:100]
        description = lines[1].strip() if len(lines) > 1 else ""

        # 3. Создаем мероприятие через ManagementService (Инкапсуляция [PL-2.1.1])
        event_id = ManagementService.create_quick_event(user_id, title)
        
        if event_id <= 0:
            return "❌ Ошибка: Не удалось создать мероприятие.", None
        
        # 4. Создаем запись об анонсе в БД
        ann_id = db.create_announcement(
            a_type="event",
            target_id=event_id,
            topic_id=topic_id,
            creator_id=user_id
        )

        # 5. Формируем текст анонса
        ann_text = (
            f"📢 <b>НОВЫЙ АНОНС</b>\n\n"
            f"📌 <b>{title}</b>\n"
            f"{description}\n\n"
            f"👤 Организатор: {message.from_user.full_name}\n"
            f"📍 Локация: {db.get_topic_name(topic_id) or 'Общий чат'}"
        )
        
        return ann_text, ann_id

    @staticmethod
    async def broadcast_event_announcement(bot, event_id: int, target_topic_id: int, creator_id: int):
        """
        Публикует анонс существующего мероприятия в целевой топик.
        """
        event = db.get_event_details(event_id)
        if not event:
            return False, "❌ Мероприятие не найдено."

        # 1. Создаем анонс-диспетчер
        ann_id = db.create_announcement(
            a_type="event",
            target_id=event_id,
            topic_id=target_topic_id,
            creator_id=creator_id
        )

        # 2. Формируем текст
        from services.event_service import EventService
        title = event['title']
        description = "Присоединяйтесь к нам!" # Можно расширить
        
        ann_text = (
            f"📢 <b>АНОНС МЕРОПРИЯТИЯ</b>\n\n"
            f"📌 <b>{title}</b>\n"
            f"📅 Дата: {event['start_date']}\n\n"
            f"Кликните кнопку ниже, чтобы записаться! 👇"
        )

        # 3. Публикуем
        from keyboards.announcements_kb import get_announcement_kb
        await bot.send_message(
            chat_id=target_topic_id, # В aiogram Chat ID может быть равен Topic ID если это супергруппа
            text=ann_text,
            reply_markup=get_announcement_kb(ann_id),
            message_thread_id=target_topic_id if target_topic_id != 0 else None
        )
        return True, "✅ Анонс успешно опубликован!"
