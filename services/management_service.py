import logging
import math
from aiogram.types import User
from database import db
from services.permission_service import PermissionService

logger = logging.getLogger(__name__)

class ManagementService:
    """
    Единый сервис управления сущностями проекта (Пользователи, Группы, Роли).
    Обслуживает как хендлеры администратора, так и модератора.
    """

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
            elif not f_name:
                f_name = l_name
                l_name = ""

            db.add_user(user_id, f_name, l_name)
            logger.info(f"🆕 Авто-регистрация: {f_name} {l_name} (ID: {user_id})")

    @staticmethod
    def add_user(user_data_text: str) -> tuple[bool, str]:
        """Логика создания нового пользователя."""
        parts = user_data_text.split()
        if len(parts) < 3 or not parts[0].isdigit():
            return False, "❌ Формат: ID Имя Фамилия"

        user_id = int(parts[0])
        f_name, l_name = parts[1], parts[2]

        if db.add_user(user_id, f_name, l_name):
            return True, f"✅ Пользователь {f_name} добавлен!"
        
        return False, f"❌ Ошибка: ID {user_id} уже занят или сбой БД."

    @staticmethod
    def create_group(name: str) -> tuple[bool, str]:
        """Логика создания новой группы доступа."""
        name = name.strip()
        if not name:
            return False, "❌ Название группы не может быть пустым."

        group_id = db.create_group(name)
        if group_id > 0:
            return True, f"✅ Группа <b>{name}</b> создана!"
        
        return False, "❌ Не удалось создать группу в базе данных."

    @staticmethod
    def assign_moderator_role(user_input: str, topic_id: int) -> tuple[bool, str]:
        """Логика назначения пользователя модератором топика."""
        if not user_input.isdigit():
            return False, "SEARCH_REQUIRED"

        target_user_id = int(user_input)
        if not db.user_exists(target_user_id):
            return False, "❌ Пользователь с таким ID не найден в системе."

        if PermissionService.is_moderator_of_topic(target_user_id, topic_id):
            return False, "❌ Этот пользователь уже является модератором данного топика."

        role_id = db.get_role_id("moderator")
        if role_id == 0:
            return False, "❌ Роль 'moderator' не найдена в БД."

        if db.grant_role(target_user_id, role_id, topic_id):
            return True, "✅ Пользователь назначен модератором топика."
        
        return False, "❌ Не удалось назначить модератора."

    @staticmethod
    def grant_direct_access(user_input: str, topic_id: int) -> tuple[bool, str]:
        """Логика выдачи прямого доступа к топику."""
        if not user_input.isdigit():
            return False, "SEARCH_REQUIRED"

        target_user_id = int(user_input)
        if not db.user_exists(target_user_id):
            return False, "❌ Пользователь не найден в системе."

        if db.grant_direct_access(target_user_id, topic_id):
            return True, "✅ Прямой доступ выдан."
        
        return False, "❌ Ошибка: Доступ уже есть или сбой БД."
