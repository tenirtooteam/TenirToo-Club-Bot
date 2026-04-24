import pytest
from unittest.mock import AsyncMock, patch
from services.notification_service import NotificationService

@pytest.mark.asyncio
async def test_send_native_all_success():
    bot = AsyncMock()
    chat_id = -100123
    topic_id = 1
    sender_name = "Ivan"
    text = "Hello all!"
    
    # Мокаем список авторизованных пользователей
    mock_users = [
        (111, "User1", "L1"),
        (222, "User2", None)
    ]
    
    with patch("database.db.get_topic_authorized_users", return_value=mock_users):
        await NotificationService.send_native_all(bot, chat_id, topic_id, sender_name, text)
        
        # Проверяем, что сообщение было отправлено
        bot.send_message.assert_called_once()
        args, kwargs = bot.send_message.call_args
        
        assert kwargs["chat_id"] == chat_id
        assert kwargs["message_thread_id"] == topic_id
        assert "Ivan" in kwargs["text"]
        assert "Hello all!" in kwargs["text"]
        # Проверяем наличие невидимых упоминаний (скрыты в HTML ссылках на ID)
        assert 'tg://user?id=111' in kwargs["text"]
        assert 'tg://user?id=222' in kwargs["text"]

@pytest.mark.asyncio
async def test_send_native_all_no_users():
    bot = AsyncMock()
    
    # Нет пользователей - не должно быть отправки
    with patch("database.db.get_topic_authorized_users", return_value=[]):
        await NotificationService.send_native_all(bot, 123, 1, "Ivan", "Text")
        bot.send_message.assert_not_called()
