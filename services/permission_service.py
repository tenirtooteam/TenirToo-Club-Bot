# Файл: services/permission_service.py
import logging
from typing import Optional
from database import db
from config import ADMIN_ID

logger = logging.getLogger(__name__)


class PermissionService:
    @staticmethod
    def is_superadmin(user_id: int) -> bool:
        """
        Проверяет, является ли пользователь суперадмином.
        Суперадмин определяется по ADMIN_ID из .env и дополнительно проверяется наличие роли 'superadmin' в БД.
        """
        if user_id != ADMIN_ID:
            return False
        # Дополнительная проверка в БД (на случай ручного вмешательства)
        roles = db.get_user_roles(user_id)
        for role_name, topic_id in roles:
            if role_name == 'superadmin':
                return True
        # Если по какой-то причине записи нет, но ID совпадает, считаем суперадмином
        logger.warning(f"⚠️ ADMIN_ID {user_id} не имеет роли 'superadmin' в БД. Доступ разрешён по ID.")
        return True

    @staticmethod
    def is_global_admin(user_id: int) -> bool:
        """
        Проверяет, является ли пользователь глобальным админом (superadmin или admin).
        """
        # Сначала быстро проверяем суперадмина по ID
        if user_id == ADMIN_ID:
            return True
        return db.is_global_admin(user_id)

    @staticmethod
    def is_moderator_of_topic(user_id: int, topic_id: int) -> bool:
        """
        Проверяет, является ли пользователь модератором конкретного топика.
        """
        return db.is_moderator_of_topic(user_id, topic_id)

    @staticmethod
    def can_manage_topic(user_id: int, topic_id: int) -> bool:
        """
        Проверяет, имеет ли пользователь права на управление топиком.
        Права есть у: суперадмина, глобального админа, модератора этого топика.
        """
        if PermissionService.is_global_admin(user_id):
            return True
        return PermissionService.is_moderator_of_topic(user_id, topic_id)

    @staticmethod
    def can_manage_user_roles(user_id: int, target_user_id: int, topic_id: Optional[int] = None) -> bool:
        """
        Проверяет, может ли пользователь управлять ролями другого пользователя.
        - Суперадмин и глобальный админ могут всё.
        - Модератор топика может назначать/снимать модераторов только в своём топике.
        """
        if PermissionService.is_global_admin(user_id):
            return True
        if topic_id is None:
            # Модератор не может назначать глобальные роли
            return False
        return PermissionService.is_moderator_of_topic(user_id, topic_id)

    @staticmethod
    def get_manageable_topics(user_id: int) -> list:
        """
        Возвращает список ID топиков, которыми пользователь может управлять.
        Для глобального админа — все топики (возвращаем специальный маркер).
        Для модератора — только его топики.
        """
        if PermissionService.is_global_admin(user_id):
            # Возвращаем все топики из БД
            return db.get_all_unique_topics()
        # Для модератора: ищем топики, где он модератор
        roles = db.get_user_roles(user_id)
        topics = []
        for role_name, topic_id in roles:
            if role_name == 'moderator' and topic_id is not None:
                topics.append(topic_id)
        return topics