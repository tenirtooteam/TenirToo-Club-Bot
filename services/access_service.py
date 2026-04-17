# Файл: services/access_service.py
import logging
from database import db
from aiogram.types import User

logger = logging.getLogger(__name__)


class AccessService:
    @staticmethod
    async def ensure_user_registered(user: User):
        """Проверяет наличие пользователя и регистрирует при необходимости."""
        user_id = user.id
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

    @staticmethod
    def can_user_write_in_topic(user_id: int, topic_id: int) -> bool:
        """Проверка прав на запись в конкретный топик."""
        # Если топик не ограничен — писать можно всем
        if not db.is_topic_restricted(topic_id):
            return True
        # Если ограничен — проверяем права
        return db.can_write(user_id, topic_id)
