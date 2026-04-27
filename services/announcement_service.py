# Файл: services/announcement_service.py
import logging
from aiogram import types
from database import db
from services.management_service import ManagementService

logger = logging.getLogger(__name__)

class AnnouncementService:
    @staticmethod
    def format_announcement_text(ann_id: int) -> str:
        """Формирует актуальный текст анонса с участниками [PL-5.1.18]."""
        ann = db.get_announcement(ann_id)
        if not ann: return "❌ Анонс не найден."
        
        ann_type, target_id, topic_id, creator_id = ann[1], ann[2], ann[3], ann[4]
        
        if ann_type == "event":
            from services.event_service import EventService
            event = EventService.get_event_details(target_id)
            if not event: return "❌ Мероприятие не найдено."
            
            # Получаем имена участников
            participant_ids = event["participants"]
            user_names = db.get_user_names_by_ids(participant_ids)
            participant_list = "\n".join([f"• {user_names.get(uid, f'ID:{uid}')}" for uid in participant_ids])
            
            creator_name = db.get_user_name(creator_id) or f"ID:{creator_id}"
            topic_name = db.get_topic_name(topic_id) or "Общий чат"
            
            text = (
                f"📢 <b>НОВЫЙ АНОНС</b>\n\n"
                f"📌 <b>{event['title']}</b>\n"
                f"📅 Дата: {event['start_date']}\n"
                f"👤 Организатор: {creator_name}\n"
                f"📍 Локация: {topic_name}\n\n"
                f"👥 <b>Участники ({len(participant_ids)}):</b>\n"
                f"{participant_list or '<i>Пока никого нет</i>'}"
            )
            return text
        
        return "🛠 Тип анонса в разработке."

    @staticmethod
    async def create_quick_event(message: types.Message):
        """Парсит команду /an и создает быстрое мероприятие с анонсом."""
        user_id = message.from_user.id
        topic_id = message.message_thread_id or 0
        
        full_text = message.text.replace("/an", "", 1).strip()
        if not full_text:
            return "❌ Ошибка: Введите текст анонса. Пример: <code>/an Заголовок</code>", None

        lines = full_text.split("\n", 1)
        title = lines[0].strip()[:100]
        
        # Создаем ивент
        event_id = ManagementService.create_quick_event(user_id, title)
        if event_id <= 0:
            return "❌ Ошибка: Не удалось создать мероприятие.", None
        
        # Регистрируем анонс
        ann_id = db.create_announcement(
            a_type="event",
            target_id=event_id,
            topic_id=topic_id,
            creator_id=user_id
        )

        return AnnouncementService.format_announcement_text(ann_id), ann_id

    @staticmethod
    async def broadcast_event_announcement(bot, event_id: int, target_topic_id: int, creator_id: int):
        """Публикует анонс существующего мероприятия в целевой топик."""
        import config
        ann_id = db.create_announcement(
            a_type="event",
            target_id=event_id,
            topic_id=target_topic_id,
            creator_id=creator_id
        )

        text = AnnouncementService.format_announcement_text(ann_id)
        from keyboards.announcements_kb import get_announcement_kb

        sent = await bot.send_message(
            chat_id=config.GROUP_ID, # ФИКС: Используем ID группы, а не топика!
            text=text,
            reply_markup=get_announcement_kb(ann_id, is_group=True),
            message_thread_id=target_topic_id if target_topic_id != 0 else None
        )
        
        # Сохраняем метаданные для возможности обновления из WebApp
        db.update_announcement_metadata(ann_id, config.GROUP_ID, sent.message_id)
        
        return True, "✅ Анонс успешно опубликован!", ann_id
