import pytest
from unittest.mock import AsyncMock, patch
from handlers.admin import process_group_add, AdminStates
from database import db

@pytest.mark.asyncio
async def test_create_group_flow(create_context, db_setup):
    """Тест создания группы: Ввод названия -> Создание в БД."""
    user_id = 999
    group_name = "New Alpine Group"
    
    # 1. Создаем контекст сообщения
    _, _, message, state = await create_context(user_id=user_id, text=group_name)
    await state.set_state(AdminStates.waiting_for_group_name)
    
    # 2. Мокаем UIService, так как он делает много UI-работы
    with patch("services.ui_service.UIService.show_admin_dashboard", new_callable=AsyncMock) as mock_dash:
        # Вызываем хендлер
        await process_group_add(message, state)
        
        # 3. ПРОВЕРКИ
        # Группа должна появиться в БД
        groups = db.get_all_groups()
        assert any(g[1] == group_name for g in groups), "Группа должна быть создана в БД"
        
        # Дашборд должен быть показан
        assert mock_dash.called
        assert "создана" in mock_dash.call_args[1].get("text", "").lower()

@pytest.mark.asyncio
async def test_delete_group_flow(create_callback, db_setup):
    """Тест удаления группы через ManagementService."""
    from services.management_service import ManagementService
    
    # 1. Создаем группу заранее
    db.create_group("To Be Deleted")
    groups = db.get_all_groups()
    group_id = groups[0][0]
    
    # 2. Вызываем удаление (имитируем подтверждение)
    # Патчим синк, так как он запускает фоновую задачу [CP-3.27]
    with patch("services.management_service.ManagementService._trigger_sheets_sync") as mock_sync:
        success, msg, next_kb = ManagementService.execute_deletion("group_del", group_id)
        
        assert success is True
        assert len(db.get_all_groups()) == 0, "Группа должна быть удалена из БД"
        assert next_kb == "manage_groups"
