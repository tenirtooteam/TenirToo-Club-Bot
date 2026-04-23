# Файл: services/management_service.py
import logging
import math
import html
from aiogram.types import User
from database import db
from services.permission_service import PermissionService

logger = logging.getLogger(__name__)


class ManagementService:
    """
    Единый сервис управления сущностями проекта (Пользователи, Группы, Роли).
    Обслуживает как хендлеры администратора, так и модератора.
    """

    # Лимиты для строк (защита UI)
    MAX_NAME_LENGTH = 64

    # Лимиты SQLite INTEGER (64-бит со знаком)
    SQLITE_MIN_INT = -9223372036854775808
    SQLITE_MAX_INT = 9223372036854775807

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
    def _parse_and_validate_id(user_input: str) -> tuple[int, str]:
        """
        Внутренний помощник для безопасного парсинга ID.
        Возвращает (ID, error_signal).
        Если ID валиден, error_signal = "".
        Если не число, error_signal = "SEARCH_REQUIRED".
        Если число вне диапазона, error_signal = "❌ Ошибка: ID вне диапазона БД."
        """
        if not user_input.isdigit():
            return 0, "SEARCH_REQUIRED"

        val = int(user_input)
        if not (ManagementService.SQLITE_MIN_INT <= val <= ManagementService.SQLITE_MAX_INT):
            return 0, "❌ Ошибка: ID слишком длинный для базы данных."

        return val, ""

    @staticmethod
    def add_user(user_data_text: str) -> tuple[bool, str]:
        """Логика создания нового пользователя."""
        parts = user_data_text.split()
        if len(parts) < 3:
            return False, "❌ Формат: ID Имя Фамилия"

        user_id, err = ManagementService._parse_and_validate_id(parts[0])
        if err:
            # Для добавления пользователя SEARCH_REQUIRED — это тоже ошибка формата
            msg = err if err != "SEARCH_REQUIRED" else "❌ ID должен быть числом."
            return False, msg

        f_name, l_name = html.escape(parts[1]), html.escape(parts[2])
        if len(f_name) > ManagementService.MAX_NAME_LENGTH or len(l_name) > ManagementService.MAX_NAME_LENGTH:
            return False, f"❌ Ошибка: Имя/Фамилия не должны превышать {ManagementService.MAX_NAME_LENGTH} симв."

        if db.add_user(user_id, f_name, l_name):
            return True, f"✅ Пользователь {f_name} добавлен!"

        return False, f"❌ Ошибка: ID {user_id} уже занят или сбой БД."

    @staticmethod
    def create_group(name: str) -> tuple[bool, str]:
        """Логика создания новой группы доступа."""
        name = html.escape(name.strip())
        if not name:
            return False, "❌ Название группы не может быть пустым."
        
        if len(name) > ManagementService.MAX_NAME_LENGTH:
            return False, f"❌ Ошибка: Название не должно превышать {ManagementService.MAX_NAME_LENGTH} симв."

        group_id = db.create_group(name)
        if group_id > 0:
            return True, f"✅ Группа <b>{name}</b> создана!"

        return False, "❌ Не удалось создать группу в базе данных."

    @staticmethod
    def assign_moderator_role(user_input: str, topic_id: int) -> tuple[bool, str]:
        """Логика назначения пользователя модератором топика."""
        target_user_id, err = ManagementService._parse_and_validate_id(user_input)
        if err:
            return False, err

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
        target_user_id, err = ManagementService._parse_and_validate_id(user_input)
        if err:
            return False, err

        if not db.user_exists(target_user_id):
            return False, "❌ Пользователь не найден в системе."

        if db.grant_direct_access(target_user_id, topic_id):
            return True, "✅ Прямой доступ выдан."

        return False, "❌ Ошибка: Доступ уже есть или сбой БД."

    @staticmethod
    def get_entity_name(entity_type: str, entity_id: int) -> str:
        """Возвращает название сущности для вывода в UI."""
        if entity_type == "group":
            return db.get_group_name(entity_id) or f"Группа {entity_id}"
        elif entity_type == "topic":
            return db.get_topic_name(entity_id) or f"Топик {entity_id}"
        elif entity_type == "user":
            return db.get_user_name(entity_id) or f"Пользователь {entity_id}"
        return "Неизвестная сущность"

    @staticmethod
    def execute_deletion(action: str, target_id: int, extra_id: int = 0) -> tuple[bool, str, str]:
        """
        Выполняет удаление и возвращает (успех, сообщение, следующий_колбэк).
        Следующий колбэк указывает, какое меню показать после успеха.
        """
        if action == "group_del":
            db.delete_group(target_id)
            return True, "✅ Группа удалена", "manage_groups"
            
        elif action in ["topic_del", "mod_topic_del"]:
            # target_id — топик, extra_id — группа
            db.remove_topic_from_group(extra_id, target_id)
            
            if action == "mod_topic_del":
                 return True, "✅ Топик убран из группы", f"mod_topic_groups_{target_id}"
            return True, "✅ Топик убран из группы", f"group_topics_list_{extra_id}"
            
        elif action == "global_topic_del":
            db.delete_topic(target_id)
            return True, "✅ Топик полностью удален", "all_topics_list"
            
        elif action == "user_del":
            db.delete_user(target_id)
            return True, "✅ Пользователь удален", "manage_users"

        elif action.startswith("role_rev"):
            # Отзыв любой роли (админ)
            role_id = int(action.split("_")[-1]) if action != "role_rev" else 0
            t_id = None if extra_id == 0 else extra_id
            db.revoke_role(target_id, role_id, t_id)
            return True, "✅ Роль отозвана", f"user_roles_manage_{target_id}"

        elif action == "mod_rem":
            # Снятие модератора (вызывается модератором)
            role_id = db.get_role_id("moderator")
            db.revoke_role(target_id, role_id, extra_id)
            return True, "✅ Модератор удалён", f"mod_topic_moderators_{extra_id}"

        return False, "❌ Ошибка: неизвестное действие", "admin_main"
