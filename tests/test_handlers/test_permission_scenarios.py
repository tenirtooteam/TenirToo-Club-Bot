import pytest
from unittest.mock import AsyncMock, patch
from handlers.admin import IsGlobalAdmin
from database import db

@pytest.mark.asyncio
async def test_admin_filter_allow(create_context, db_setup):
    """Проверка, что фильтр пропускает админа."""
    user_id = 999
    # 1. Даем права админа в тестовой БД
    db.grant_role(user_id, "admin")
    
    # 2. Создаем контекст
    _, _, message, _ = await create_context(user_id=user_id)
    
    # 0. Обеспечиваем наличие юзера и роли [CC-1]
    db.add_user(user_id, "Admin", "User")
    role_id = db.get_role_id("admin")
    db.grant_role(user_id, role_id)
    
    # 2. Создаем контекст
    _, _, message, _ = await create_context(user_id=user_id)
    
    # 3. Проверяем фильтр
    filter_obj = IsGlobalAdmin()
    result = await filter_obj(message)
    assert result is True

@pytest.mark.asyncio
async def test_admin_filter_deny(create_context, db_setup):
    """Проверка, что фильтр блокирует обычного пользователя."""
    user_id = 555 # Обычный юзер без ролей
    
    # 2. Создаем контекст
    _, _, message, _ = await create_context(user_id=user_id)
    
    # 3. Проверяем фильтр
    filter_obj = IsGlobalAdmin()
    result = await filter_obj(message)
    assert result is False, "Фильтр должен заблокировать обычного пользователя"

@pytest.mark.asyncio
async def test_moderator_topic_access(db_setup):
    """Проверка логики прав модератора топика [PL-2.2.51]."""
    from services.permission_service import PermissionService
    user_id = 777
    topic_id = 10
    
    # Подготовка данных для FK
    db.add_user(user_id, "Mod", "Tester")
    db.register_topic_if_not_exists(topic_id)
    role_id = db.get_role_id("moderator")
    
    # Сначала прав нет
    assert not PermissionService.is_moderator_of_topic(user_id, topic_id)
    
    # Даем роль
    db.grant_role(user_id, role_id, topic_id)
    
    # Теперь права есть
    assert PermissionService.is_moderator_of_topic(user_id, topic_id)
    # Но для другого топика прав всё еще нет
    assert not PermissionService.is_moderator_of_topic(user_id, 11)
