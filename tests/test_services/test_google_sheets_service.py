import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.google_sheets_service import GoogleSheetsService

@pytest.mark.asyncio
async def test_export_users_formatting():
    """Проверяет правильность форматирования данных для выгрузки пользователей."""
    mock_users = [
        (1, "Ivan", "Ivanov", "admin, moderator"),
        (2, "Petr", None, "user")
    ]
    
    with patch("services.google_sheets_service.GoogleSheetsService.get_client") as mock_get_client:
        mock_sh = AsyncMock()
        mock_worksheet = AsyncMock()
        mock_client = AsyncMock()
        
        mock_get_client.return_value = mock_client
        mock_client.open_by_key.return_value = mock_sh
        mock_sh.worksheet.return_value = mock_worksheet
        
        with patch("config.SPREADSHEET_ID", "test_id"):
            success = await GoogleSheetsService.export_users(mock_users)
            
            assert success is True
            # Проверяем, что в update переданы правильные данные
            args, kwargs = mock_worksheet.update.call_args
            data = kwargs.get("values")
            
            assert data[0] == ["User ID", "First Name", "Last Name", "Roles"]
            assert data[1] == ["1", "Ivan", "Ivanov", "admin, moderator"]
            assert data[2] == ["2", "Petr", "", "user"]

@pytest.mark.asyncio
async def test_export_groups_formatting():
    """Проверяет правильность форматирования данных для выгрузки групп."""
    mock_groups = [
        {'id': 101, 'name': 'Alpha', 'topics': ['News', 'General']},
        {'id': 102, 'name': 'Beta', 'topics': []}
    ]
    
    with patch("services.google_sheets_service.GoogleSheetsService.get_client") as mock_get_client:
        mock_sh = AsyncMock()
        mock_worksheet = AsyncMock()
        mock_client = AsyncMock()
        
        mock_get_client.return_value = mock_client
        mock_client.open_by_key.return_value = mock_sh
        mock_sh.worksheet.return_value = mock_worksheet
        
        with patch("config.SPREADSHEET_ID", "test_id"):
            success = await GoogleSheetsService.export_groups(mock_groups)
            
            assert success is True
            args, kwargs = mock_worksheet.update.call_args
            data = kwargs.get("values")
            
            assert data[0] == ["Group ID", "Group Name", "Topics"]
            assert data[1] == ["101", "Alpha", "News, General"]
            assert data[2] == ["102", "Beta", ""]
