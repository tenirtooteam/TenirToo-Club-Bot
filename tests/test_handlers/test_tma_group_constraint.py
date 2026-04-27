import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup
from handlers.announcements import cmd_quick_announcement
import config
from database import db

def simulate_telegram_server_validation(text, reply_markup=None, **kwargs):
    """Мок для message.answer, который симулирует ошибку Telegram (BUTTON_TYPE_INVALID)
    если web_app используется в групповом чате."""
    if reply_markup and isinstance(reply_markup, InlineKeyboardMarkup):
        for row in reply_markup.inline_keyboard:
            for btn in row:
                if btn.web_app is not None:
                    raise TelegramBadRequest(
                        method="sendMessage",
                        message="Bad Request: BUTTON_TYPE_INVALID"
                    )
    # Возвращаем успешный ответ, если все ок
    mock_sent = MagicMock(message_id=999, chat=MagicMock(id=123))
    f = asyncio.Future()
    f.set_result(mock_sent)
    return f

@pytest.mark.asyncio
async def test_quick_announcement_group_web_app_constraint(create_context, db_setup):
    """
    Тест проверяет, что команда /an в группе не отправляет кнопку web_app,
    так как это вызывает BUTTON_TYPE_INVALID на сервере Telegram.
    """
    user_id = 123
    topic_id = 42
    
    db.add_user(user_id, "Admin", "User")
    db.grant_role(user_id, db.get_role_id("admin"))
    db.register_topic_if_not_exists(topic_id)
    
    _, _, message, state = await create_context(
        user_id=user_id, 
        text="/an Hike to Peak\nGreat view guaranteed",
        thread_id=topic_id,
        chat_type="supergroup" # Указываем, что это группа
    )
    
    with patch("config.WEBAPP_URL", "https://club.tenirtoo.kg"), \
         patch("services.ui_service.UIService.delete_msg", new_callable=AsyncMock), \
         patch("aiogram.types.Message.answer", side_effect=simulate_telegram_server_validation) as mock_answer:
        
        # Если код не адаптирован к группам, этот вызов бросит TelegramBadRequest
        # Тест должен пройти без исключений, если архитектура правильная.
        await cmd_quick_announcement(message, state)
        
        # Проверяем, что в клавиатуре именно две кнопки и нет web_app
        call_args = mock_answer.call_args
        kb = call_args.kwargs.get("reply_markup")
        assert kb is not None
        
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert len(buttons) == 2
        assert "Иду" in buttons[0].text
        assert "Не иду" in buttons[1].text
        assert buttons[0].web_app is None
        assert buttons[1].web_app is None
        assert "ann_join" in buttons[0].callback_data
