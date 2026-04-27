# Файл: tests/test_journeys/test_tma_integration.py
import pytest
from unittest.mock import patch, MagicMock
from keyboards.announcements_kb import get_announcement_kb
from aiogram.types import WebAppInfo

@pytest.mark.asyncio
async def test_announcement_kb_tma_logic():
    """Тест логики клавиатуры анонса: группа vs ЛС."""
    ann_id = 42
    test_url = "https://club.tenirtoo.kg"
    
    # 1. Группа (Две кнопки Иду/Не иду)
    with patch("config.WEBAPP_URL", test_url):
        kb = get_announcement_kb(ann_id, is_group=True)
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert len(buttons) == 2
        assert buttons[0].callback_data == f"ann_join:{ann_id}:1"
        assert buttons[1].callback_data == f"ann_join:{ann_id}:0"
        assert buttons[0].web_app is None

    # 2. Личные сообщения (Кнопка Личного Кабинета)
    with patch("config.WEBAPP_URL", test_url):
        kb = get_announcement_kb(ann_id, is_group=False)
        button = kb.inline_keyboard[0][0]
        assert button.web_app is not None
        assert button.web_app.url == f"{test_url}/?ann_id={ann_id}"
        assert "Личный кабинет" in button.text
