# Файл: middlewares/access_check.py
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from database import db
from services.access_service import AccessService

logger = logging.getLogger(__name__)


class UserManagerMiddleware(BaseMiddleware):
    """Мидлварь для авто-регистрации пользователей."""
    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: Message, data: Dict[str, Any]) -> Any:
        if event.from_user and not event.from_user.is_bot:
            await AccessService.ensure_user_registered(event.from_user)
        return await handler(event, data)


class ForumUtilityMiddleware(BaseMiddleware):
    """Мидлварь для синхронизации топиков и чистки сервисных сообщений (только для групп)."""
    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: Message, data: Dict[str, Any]) -> Any:
        if event.chat.type == "private":
            return await handler(event, data)

        # Синхронизация при ручном переименовании топика в Telegram
        if event.forum_topic_edited:
            new_name = event.forum_topic_edited.name
            topic_id = event.message_thread_id
            if new_name:
                db.update_topic_name(topic_id, new_name)
                logger.info(f"🔄 Топик {topic_id} синхронизирован из Telegram: {new_name}")
            try:
                await event.delete()
            except Exception:
                pass
            return

        # Удаление сервисных сообщений о создании топиков
        if event.forum_topic_created:
            try:
                await event.delete()
            except Exception:
                pass
            return

        # Авто-регистрация топика в БД
        topic_id = event.message_thread_id if event.message_thread_id else -1
        db.register_topic_if_not_exists(topic_id)

        return await handler(event, data)


class AccessGuardMiddleware(BaseMiddleware):
    """Финальный щит — стелс-модерация сообщений в топиках."""
    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: Message, data: Dict[str, Any]) -> Any:
        if event.chat.type == "private" or event.from_user.id == event.bot.id:
            return await handler(event, data)

        topic_id = event.message_thread_id if event.message_thread_id else -1
        user_id = event.from_user.id
        user_fullname = f"{event.from_user.first_name} {event.from_user.last_name or ''}".strip()
        topic_name = db.get_topic_name(topic_id)
        log_base = f"{user_fullname} (ID: {user_id}) -> {topic_name} (ID: {topic_id})"

        if not AccessService.can_user_write_in_topic(user_id, topic_id):
            try:
                await event.delete()
                logger.info(f"❌ {log_base} | Сообщение УДАЛЕНО (нет доступа)")
                return
            except Exception as e:
                logger.error(f"⚠️ Ошибка модерации: {e}")
                return

        logger.info(f"✅ {log_base} | Сообщение ПРИНЯТО")
        return await handler(event, data)