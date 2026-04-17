import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from database import db

logger = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        # 1. Личные сообщения не фильтруем [cite: 46]
        if event.chat.type == "private":
            return await handler(event, data)

        # 2. АВТО-СИНХРОНИЗАЦИЯ И ЧИСТКА [cite: 47]
        # Перехват ручного переименования топика в Telegram [cite: 47]
        if event.forum_topic_edited:
            new_name = event.forum_topic_edited.name
            topic_id = event.message_thread_id
            if new_name:
                db.update_topic_name(topic_id, new_name)
                logger.info(f"🔄 Топик {topic_id} синхронизирован из Telegram: {new_name}")
            try:
                await event.delete()  # Удаляем сервисное уведомление об изменении [cite: 48]
                return
            except Exception:
                return

        # Удаление сервисных сообщений о создании топиков [cite: 49]
        if event.forum_topic_created:
            try:
                await event.delete()
                return
            except Exception:
                return

        # 3. ИДЕНТИФИКАЦИЯ И АВТО-РЕГИСТРАЦИЯ [cite: 50]
        topic_id = event.message_thread_id if event.message_thread_id else -1
        db.register_topic_if_not_exists(topic_id)  # Авто-обнаружение топика [cite: 50]

        user = event.from_user
        user_id = user.id

        # Автоматическое добавление участника в БД (используем новый members.py через db.py)
        if not db.user_exists(user_id):
            f_name = user.first_name
            l_name = user.last_name or ""

            # Логика именования по умолчанию
            if not f_name and not l_name:
                f_name = f"Пользователь_{user_id}"
                l_name = ""
            elif not f_name:
                f_name = l_name
                l_name = ""

            db.add_user(user_id, f_name, l_name)
            logger.info(f"🆕 Авто-регистрация: {f_name} {l_name} (ID: {user_id})")

        # Иммунитет для самого бота [cite: 50]
        if user_id == event.bot.id:
            return await handler(event, data)

        topic_name = db.get_topic_name(topic_id)
        user_fullname = f"{user.first_name} {user.last_name or ''}".strip()
        log_base = f"{user_fullname} (ID: {user_id}) -> {topic_name} (ID: {topic_id})"

        # 4. МОДЕРАЦИЯ
        # Проверяем, ограничен ли доступ к этому топику
        if db.is_topic_restricted(topic_id):
            # Проверяем, есть ли у пользователя права писать сюда
            if not db.can_write(user_id, topic_id):
                try:
                    await event.delete()
                    logger.info(f"❌ {log_base} | Сообщение УДАЛЕНО (нет доступа) [cite: 52]")
                    return
                except Exception as e:
                    logger.error(f"⚠️ Ошибка модерации: {e}")
                    return

        # 5. УСПЕХ [cite: 53]
        logger.info(f"✅ {log_base} | Сообщение ПРИНЯТО")
        return await handler(event, data)