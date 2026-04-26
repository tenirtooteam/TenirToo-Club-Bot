import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import InlineKeyboardMarkup
import keyboards as kb
from services.ui_service import UIService
from services.help_service import HelpService

@pytest.mark.asyncio
async def test_all_keyboards_callback_validity():
    """
    Системный тест целостности UI:
    Проверяет все клавиатуры на наличие 'битых' ссылок и корректность справки.
    """
    # 1. Список функций клавиатур для проверки
    kb_functions = [
        (kb.user_main_kb, []),
        (kb.main_admin_kb, []),
        (kb.groups_list_kb, []),
        (kb.users_list_kb, []),
        (kb.all_topics_kb, []),
        (kb.event_list_kb if hasattr(kb, "event_list_kb") else kb.get_events_list_kb, [[]]), # events=[]
        (kb.user_profile_kb, []),
        (kb.user_topics_list_kb, [1]), # user_id=1
    ]

    # 2. Список известных валидных команд (роутинг)
    # Эти команды либо есть в UIService.generic_navigator, либо имеют явные хендлеры
    valid_static_commands = {
        "landing", "admin_main", "user_main", "manage_groups", "manage_users", 
        "all_topics_list", "roles_dashboard", "roles_faq", "list_users_roles",
        "moderator", "templates_faq", "event_list", "event_pending_list",
        "close_menu", "add_group_start", "sheets_export_all", "sheets_import_all",
        "event_create", "user_topics", "user_profile_view", "add_user_start"
    }

    def is_valid_callback(data: str):
        if not data: return True
        # Статика
        if data in valid_static_commands: return True
        # Пагинация
        if "_pg_" in data: return True
        # Справка (проверяем ключ и возврат)
        if data.startswith("help:"):
            parts = data.split(":")
            if parts[1] not in HelpService.HELP_CONTENT: return False
            if len(parts) > 2 and not is_valid_callback(parts[2]): return False
            return True
        # Параметризованные (проверяем префиксы)
        prefixes = [
            "group_info_", "user_info_", "u_topic_info_", "role_assign_", 
            "event_view:", "event_join:", "event_leave:", "event_edit:", "event_delete:",
            "mod_topic_select_", "mod_topic_groups_", "mod_users_manage_", "mod_topic_moderators_",
            "tmpl_act_start_", "add_topic_to_", "group_topics_list_"
        ]
        return any(data.startswith(p) for p in prefixes)

    # 3. Обход всех клавиатур
    errors = []
    for func, args in kb_functions:
        try:
            markup = func(*args)
            if not isinstance(markup, InlineKeyboardMarkup):
                continue
            
            for row in markup.inline_keyboard:
                for button in row:
                    cd = button.callback_data
                    if not is_valid_callback(cd):
                        errors.append(f"Broken callback '{cd}' in {func.__name__}")
        except Exception as e:
            errors.append(f"Error calling {func.__name__}: {e}")

    assert not errors, f"UI Integrity violations found:\n" + "\n".join(errors)

@pytest.mark.asyncio
async def test_help_return_path_logic():
    """
    Проверяет, что каждая справка в ключевых меню возвращает пользователя 
    в корректное место (не вызывает зависаний).
    """
    test_cases = [
        (kb.user_main_kb(), "main_menu", "landing"),
        (kb.main_admin_kb(), "admin_menu", "landing"),
        (kb.get_events_list_kb([]), "events", "event_list"),
    ]

    for markup, expected_key, expected_back in test_cases:
        help_button = None
        for row in markup.inline_keyboard:
            for btn in row:
                if btn.text == "❓":
                    help_button = btn
                    break
        
        assert help_button is not None, "Help button missing in menu"
        cd = help_button.callback_data
        parts = cd.split(":")
        assert parts[1] == expected_key, f"Wrong help key: {parts[1]}"
        assert parts[2] == expected_back, f"Help back-link '{parts[2]}' might cause a hang if not handled"
