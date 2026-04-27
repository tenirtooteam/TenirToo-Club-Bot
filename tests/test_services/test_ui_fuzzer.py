# Файл: tests/test_services/test_ui_fuzzer.py
import pytest
import asyncio
import logging
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Dispatcher, types, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

from services.ui_service import UIService
from database import db

# Импортируем все роутеры для регистрации в тестовом диспетчере
from handlers.common import router as common_router
from handlers.admin import router as admin_router
from handlers.moderator import router as moderator_router
from handlers.events import router as events_router
from handlers.user import router as user_router
from handlers.announcements import router as announcements_router

logger = logging.getLogger(__name__)

class UIFuzzer:
    """
    [CP-3.13] Autonomous Deep-UI Fuzzing Crawler.
    Рекурсивно обходит меню, кликает кнопки и вводит текст при смене стейта.
    """
    def __init__(self):
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        
        # Регистрируем роутеры в правильном порядке [PL-2.2.1]
        # Сбрасываем родителя, чтобы избежать RuntimeError при повторных запусках
        for r in [common_router, user_router, admin_router, moderator_router, events_router, announcements_router]:
            r._parent_router = None
            self.dp.include_router(r)
        
        self.visited_callbacks = set()
        self.max_depth = 10
        self.results = [] # Лог ошибок
        
        # Мокаем бота
        self.bot = AsyncMock()
        self.bot.id = 123456789
        
    async def simulate_input(self, user_id: int, chat_id: int, text: str):
        """Симуляция текстового ввода пользователем."""
        message = types.Message(
            message_id=999,
            date=datetime.datetime.now(),
            chat=types.Chat(id=chat_id, type="private"),
            from_user=types.User(id=user_id, is_bot=False, first_name="TestUser"),
            text=text
        )
        await self.dp.feed_update(self.bot, types.Update(update_id=1, message=message))

    async def simulate_click(self, user_id: int, chat_id: int, callback_data: str, message_id: int = 100):
        """Симуляция клика по inline-кнопке."""
        callback = types.CallbackQuery(
            id="1",
            from_user=types.User(id=user_id, is_bot=False, first_name="TestUser"),
            chat_instance="1",
            message=types.Message(
                message_id=message_id,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type="private"),
                text="Menu Context"
            ),
            data=callback_data
        )
        await self.dp.feed_update(self.bot, types.Update(update_id=1, callback_query=callback))

    async def run_crawl(self, start_command: str, user_id: int, chat_id: int):
        """Запуск рекурсивного обхода с глобальным перехватом кнопок."""
        # Очередь для обхода (callback_data, depth)
        queue = asyncio.Queue()
        
        def _extract_buttons(markup, current_depth):
            if not markup or not hasattr(markup, 'inline_keyboard'):
                return
            for row in markup.inline_keyboard:
                for btn in row:
                    if btn.callback_data and btn.callback_data not in self.visited_callbacks:
                        logger.info(f"   found node: {btn.callback_data}")
                        queue.put_nowait((btn.callback_data, current_depth + 1))
                        self.visited_callbacks.add(btn.callback_data)

        # Глобально патчим методы отправки сообщений
        # Это позволит видеть кнопки даже если они не через UIService
        with patch("aiogram.Bot.send_message", new_callable=AsyncMock) as mock_send, \
             patch("aiogram.Bot.edit_message_text", new_callable=AsyncMock) as mock_edit_bot, \
             patch("aiogram.types.Message.answer", new_callable=AsyncMock) as mock_answer, \
             patch("aiogram.types.Message.edit_text", new_callable=AsyncMock) as mock_edit_msg:
            
            async def process_all_mocks(depth):
                for m in [mock_send, mock_edit_bot, mock_answer, mock_edit_msg]:
                    for call in m.call_args_list:
                        markup = call.kwargs.get('reply_markup')
                        _extract_buttons(markup, depth)
                    m.reset_mock()

            # 1. Стартуем с команды
            message = types.Message(
                message_id=999,
                date=datetime.datetime.now(),
                chat=types.Chat(id=chat_id, type="private"),
                from_user=types.User(id=user_id, is_bot=False, first_name="TestUser"),
                text=start_command
            )
            logger.info(f"🚀 Starting deep crawl with command: {start_command}")
            await self.dp.feed_update(self.bot, types.Update(update_id=1, message=message))
            await process_all_mocks(0)
            
            # 2. Цикл обхода
            while not queue.empty():
                callback_data, depth = await queue.get()
                if depth > self.max_depth: continue
                
                logger.info(f"➡️ Depth {depth} | Clicking: {callback_data}")
                with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock):
                    await self.simulate_click(user_id, chat_id, callback_data)
                
                # После клика мог смениться стейт
                state: FSMContext = self.dp.fsm.get_context(self.bot, chat_id, user_id)
                current_state = await state.get_state()
                if current_state:
                    logger.info(f"FSM State: {current_state}. Injecting payload.")
                    await self.simulate_input(user_id, chat_id, "Fuzzer Payload")
                
                await process_all_mocks(depth)

@pytest.mark.asyncio
async def test_admin_journey_fuzzer():
    """Фаззинг-тест всей админ-панели и ивентов."""
    fuzzer = UIFuzzer()
    from handlers.admin import IsGlobalAdmin
    with patch.object(IsGlobalAdmin, "__call__", return_value=True), \
         patch("database.db.get_all_users", return_value=[]), \
         patch("database.db.get_all_groups", return_value=[]), \
         patch("database.db.get_all_unique_topics", return_value=[]), \
         patch("services.permission_service.PermissionService.is_global_admin", return_value=True), \
         patch("services.permission_service.PermissionService.get_user_display_name", return_value="Test Admin"):
        
        await fuzzer.run_crawl("/admin", user_id=123, chat_id=123)
        
    assert len(fuzzer.visited_callbacks) > 5 # Теперь должно быть гораздо больше
    logger.info(f"Visited {len(fuzzer.visited_callbacks)} unique UI nodes.")
