import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.fsm.context import FSMContext
from services.ui_service import UIService
import keyboards as kb

@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    return state

@pytest.fixture
def mock_callback():
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message = AsyncMock()
    return callback

@pytest.mark.asyncio
async def test_navigator_simple_routes_stability(mock_state, mock_callback):
    """
    Проверяет стабильность всех 'простых' роутов навигатора.
    Гарантирует отсутствие TypeError при вызове kb_func.
    """
    # Список ключей для проверки (согласно ui_service.py)
    test_keys = [
        "admin_main", "user_main", "user_profile_view", "user_topics",
        "manage_groups", "manage_users", "all_topics_list", 
        "roles_dashboard", "roles_faq", "list_users_roles", "moderator",
        "templates_faq"
    ]
    
    # Патчим зависимости, чтобы не лезть в БД и не слать сообщения
    with patch("services.ui_service.UIService.sterile_show", AsyncMock()) as mock_show:
        with patch("services.permission_service.PermissionService.is_global_admin", return_value=True):
            with patch("services.permission_service.PermissionService.get_manageable_topics", return_value=[1]):
                with patch("database.db.get_user_name", return_value="Test User"):
                    with patch("database.db.get_user_group_templates", return_value=[]):
                        with patch("database.db.get_user_roles", return_value=[]):
                            with patch("database.db.get_user_available_topics", return_value=[]):
                                
                                for key in test_keys:
                                    # Сбрасываем мок перед каждым тестом
                                    mock_show.reset_mock()
                                    
                                    # Вызываем навигатор
                                    # Если в коде есть TypeError: 'NoneType' object is not callable, тест упадет здесь
                                    await UIService.generic_navigator(mock_state, mock_callback, key)
                                    
                                    # Проверяем, что либо вызвался show_menu, либо произошел редирект (рекурсивный вызов)
                                    # Для редиректов (templates_faq) или специальных карточек (user_profile_view)
                                    # мы просто проверяем, что нет исключений.

@pytest.mark.asyncio
async def test_navigator_help_route_stability(mock_state, mock_callback):
    """Проверка роутинга справок help:{key}:{back_data}"""
    with patch("handlers.common.show_help_view", AsyncMock()) as mock_help:
        await UIService.generic_navigator(mock_state, mock_callback, "help:templates:admin_main")
        mock_help.assert_called_once_with(mock_state, mock_callback, key="templates", back_data="admin_main")

@pytest.mark.asyncio
async def test_navigator_parameterized_routes_smoke(mock_state, mock_callback):
    """Smoke-тест параметризованных роутов (инфо-карточки)."""
    routes = ["user_info_1", "group_info_1", "topic_global_view_1", "topic_in_group_1_1"]
    
    with patch("services.ui_service.UIService.show_user_detail", AsyncMock()):
        with patch("services.ui_service.UIService.show_group_detail", AsyncMock()):
            with patch("services.ui_service.UIService.show_topic_detail", AsyncMock()):
                for route in routes:
                    await UIService.generic_navigator(mock_state, mock_callback, route)
