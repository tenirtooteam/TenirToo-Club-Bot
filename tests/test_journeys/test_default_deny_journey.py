import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message
import config
from database import db
from middlewares.access_check import AccessGuardMiddleware
from services.permission_service import PermissionService

@pytest.mark.asyncio
async def test_default_deny_unconfigured_topic_blocks_user(create_context, mock_bot):
    """
    Верификация Default Deny: Сообщение в не настроенном топике удаляется для обычного пользователя.
    """
    user_id = 555
    topic_id = 777
    db.add_user(user_id, "Test", "User")
    db.register_topic_if_not_exists(topic_id)
    
    # Убеждаемся, что топик пустой (не настроен)
    assert not db.is_topic_restricted(topic_id)
    
    _, _, message, state = await create_context(user_id=user_id, chat_id=config.GROUP_ID, thread_id=topic_id, chat_type="supergroup")
    
    # Мокаем handler и метод удаления
    next_handler = AsyncMock()
    
    middleware = AccessGuardMiddleware()
    
    # Запускаем мидлварь
    with patch("aiogram.types.Message.delete", new_callable=AsyncMock) as mock_delete:
        await middleware(next_handler, message, {"state": state})
    
    # Проверяем: сообщение удалено, handler НЕ вызван
    mock_delete.assert_called_once()
    next_handler.assert_not_called()

@pytest.mark.asyncio
async def test_default_deny_unconfigured_topic_allows_admin_with_immunity(create_context, mock_bot, monkeypatch):
    """
    Админ может писать в не настроенный топик, если IMMUNITY_FOR_ADMINS = True.
    """
    admin_id = config.ADMIN_ID
    topic_id = 888
    db.add_user(admin_id, "Admin", "User")
    db.register_topic_if_not_exists(topic_id)
    db.grant_role(admin_id, "superadmin")
    
    _, _, message, state = await create_context(user_id=admin_id, chat_id=config.GROUP_ID, thread_id=topic_id, chat_type="supergroup")
    
    next_handler = AsyncMock()
    middleware = AccessGuardMiddleware()
    
    with patch("middlewares.access_check.IMMUNITY_FOR_ADMINS", True):
        with patch("aiogram.types.Message.delete", new_callable=AsyncMock) as mock_delete:
            await middleware(next_handler, message, {"state": state})
    
    # Проверяем: сообщение ПРИНЯТО (handler вызван)
    next_handler.assert_called_once()
    mock_delete.assert_not_called()

@pytest.mark.asyncio
async def test_default_deny_unconfigured_topic_blocks_admin_without_immunity(create_context, mock_bot, monkeypatch):
    """
    Админ БЛОКИРУЕТСЯ в не настроенном топике, если IMMUNITY_FOR_ADMINS = False (режим теста). [USER-REMINDER]
    """
    admin_id = config.ADMIN_ID
    topic_id = 999
    db.add_user(admin_id, "Admin", "User")
    db.register_topic_if_not_exists(topic_id)
    db.grant_role(admin_id, "superadmin")
    
    _, _, message, state = await create_context(user_id=admin_id, chat_id=config.GROUP_ID, thread_id=topic_id, chat_type="supergroup")
    
    next_handler = AsyncMock()
    middleware = AccessGuardMiddleware()
    
    with patch("middlewares.access_check.IMMUNITY_FOR_ADMINS", False):
        with patch("aiogram.types.Message.delete", new_callable=AsyncMock) as mock_delete:
            await middleware(next_handler, message, {"state": state})
    
    # Проверяем: сообщение УДАЛЕНО (handler НЕ вызван), так как Default Deny работает для всех при IMMUNITY=False
    mock_delete.assert_called_once()
    next_handler.assert_not_called()

@pytest.mark.asyncio
async def test_default_deny_reverts_to_restricted_if_users_added(create_context, mock_bot):
    """
    Если в топик добавлен хотя бы один юзер, Default Deny сменяется на обычный Whitelist.
    """
    user_id = 111
    topic_id = 222
    db.add_user(user_id, "Allowed", "User")
    db.register_topic_if_not_exists(topic_id)
    db.grant_direct_access(user_id, topic_id)
    
    assert db.is_topic_restricted(topic_id)
    
    _, _, message, state = await create_context(user_id=user_id, chat_id=config.GROUP_ID, thread_id=topic_id, chat_type="supergroup")
    
    next_handler = AsyncMock()
    middleware = AccessGuardMiddleware()
    
    await middleware(next_handler, message, {"state": state})
    
    # Проверяем: доступ разрешен
    next_handler.assert_called_once()
