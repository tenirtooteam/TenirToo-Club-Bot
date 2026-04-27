import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from handlers.announcements import cmd_quick_announcement, announcement_join_handler
from database import db

@pytest.mark.asyncio
async def test_quick_announcement_success(create_context, db_setup):
    """Тест команды /an: Создание анонса админом."""
    user_id = 123
    topic_id = 42
    
    # 1. Даем права
    db.add_user(user_id, "Admin", "User")
    db.grant_role(user_id, db.get_role_id("admin"))
    db.register_topic_if_not_exists(topic_id)
    
    # 2. Контекст команды
    _, _, message, state = await create_context(
        user_id=user_id, 
        text="/an Hike to Peak\nGreat view guaranteed",
        thread_id=topic_id
    )
    
    # 3. Мокаем удаление сообщения и ответ
    with patch("services.ui_service.UIService.delete_msg", new_callable=AsyncMock) as mock_del, \
         patch("aiogram.types.Message.answer", new_callable=AsyncMock) as mock_answer:
        
        # Настраиваем mock_answer, чтобы он возвращал объект с message_id
        mock_answer.return_value = MagicMock(message_id=999, chat=MagicMock(id=123))
        
        await cmd_quick_announcement(message, state)
        
        # 4. ПРОВЕРКИ
        assert mock_del.called, "Команда должна быть удалена"
        assert mock_answer.called, "Анонс должен быть опубликован"
        
        # Проверяем БД
        anns = db.get_announcement(1) # Первый анонс
        assert anns is not None
        assert anns[1] == "event"
        assert anns[3] == topic_id

@pytest.mark.asyncio
async def test_quick_announcement_deny(create_context, db_setup):
    """Тест команды /an: Отказ в доступе обычному пользователю."""
    user_id = 444
    
    # 2. Контекст команды
    _, _, message, state = await create_context(user_id=user_id, text="/an Hack the planet")
    
    # 3. Мокаем удаление
    with patch("services.ui_service.UIService.delete_msg", new_callable=AsyncMock) as mock_del:
        await cmd_quick_announcement(message, state)
        
        # 4. ПРОВЕРКИ
        assert mock_del.called, "Команда должна быть молча удалена"
        # Проверяем БД - анонсов быть не должно
        assert db.get_announcement(1) is None
