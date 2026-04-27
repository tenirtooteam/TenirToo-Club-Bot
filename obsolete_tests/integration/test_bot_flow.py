import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from aiogram import Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import admin, user, common, moderator
from middlewares.access_check import UserManagerMiddleware, ForumUtilityMiddleware, AccessGuardMiddleware
from database import db

@pytest.fixture
def dp():
    dispatcher = Dispatcher(storage=MemoryStorage())
    
    # Регистрация мидлварей (как в main.py)
    dispatcher.message.outer_middleware(UserManagerMiddleware())
    dispatcher.message.outer_middleware(ForumUtilityMiddleware())
    dispatcher.message.outer_middleware(AccessGuardMiddleware())
    
    # Регистрация роутеров с проверкой, чтобы не было RuntimeError: Router is already attached
    # В тестах мы можем "отвязывать" роутеры перед привязкой для изоляции
    for r in [common.router, user.router, admin.router, moderator.router]:
        r._parent_router = None # Сбрасываем старую привязку напрямую (через приватное поле)
        dispatcher.include_router(r)
    
    return dispatcher

@pytest.mark.asyncio
async def test_start_command_integration(dp, mock_bot):
    # Имитируем команду /start от обычного юзера
    user = types.User(id=555, is_bot=False, first_name="Test", last_name="User")
    chat = types.Chat(id=555, type="private")
    message = types.Message(message_id=1, date=datetime.now(), chat=chat, from_user=user, text="/start")
    
    update = types.Update(update_id=1, message=message)
    
    # Мокаем ответ бота
    # В aiogram 3 вызов message.answer превращается в вызов bot.send_message
    mock_bot.send_message = AsyncMock(return_value=types.Message(message_id=2, date=datetime.now(), chat=chat, text="Welcome"))
    
    # Прогоняем апдейт через диспетчер
    await dp.feed_update(mock_bot, update)
    
    # Проверяем, что юзер зарегистрировался в БД (мидлварь сработала)
    assert db.user_exists(555) is True
    
    # Проверяем, что бот что-то ответил (хендлер сработал)
    mock_bot.assert_called()

@pytest.mark.asyncio
async def test_stealth_moderation_integration(dp, mock_bot):
    # Группа, топик 10 ограничен через прямой доступ другого юзера
    db.register_topic_if_not_exists(10)
    db.add_user(999, "Other", "User")
    db.grant_direct_access(999, 10)
    
    # Юзер 666 без доступа пишет в топик 10
    user = types.User(id=666, is_bot=False, first_name="Intruder", last_name="")
    chat = types.Chat(id=-100123, type="supergroup")
    message = types.Message(message_id=100, date=datetime.now(), chat=chat, from_user=user, 
                            text="Hello", message_thread_id=10)
    
    # Привязываем бота к сообщению для работы мидлварей
    message._bot = mock_bot
    mock_bot.id = 999
    
    update = types.Update(update_id=2, message=message)
    
    # Мокаем удаление сообщения
    mock_bot.delete_message = AsyncMock()
    
    # Прогоняем
    await dp.feed_update(mock_bot, update)
    
    # Сообщение должно быть удалено AccessGuardMiddleware
    mock_bot.assert_called()
    # Можно проверить конкретный метод
    args, _ = mock_bot.call_args
    from aiogram.methods import DeleteMessage
    assert isinstance(args[0], DeleteMessage)

@pytest.mark.asyncio
async def test_admin_access_integration(dp, mock_bot):
    admin_id = 777
    db.add_user(admin_id, "Boss", "")
    
    # Мокаем конфиг
    with patch("services.permission_service.PermissionService.is_global_admin", return_value=True):
        user = types.User(id=admin_id, is_bot=False, first_name="Boss")
        chat = types.Chat(id=admin_id, type="private")
        message = types.Message(message_id=1, date=datetime.now(), chat=chat, from_user=user, text="/admin")
        
        mock_bot.send_message = AsyncMock(return_value=types.Message(message_id=2, date=datetime.now(), chat=chat, text="Admin Panel"))
        
        update = types.Update(update_id=3, message=message)
        await dp.feed_update(mock_bot, update)
        
        # Проверяем, что пустило в админку
        mock_bot.assert_called()
        args, _ = mock_bot.call_args
        from aiogram.methods import SendMessage
        assert isinstance(args[0], SendMessage)
        assert "Панель управления" in args[0].text
