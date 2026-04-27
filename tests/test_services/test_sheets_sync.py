import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.google_sheets_service import GoogleSheetsService
import config

@pytest.mark.asyncio
async def test_sheets_export_missing_config(db_setup):
    """Тест поведения при отсутствии SPREADSHEET_ID."""
    with patch("config.SPREADSHEET_ID", None):
        result = await GoogleSheetsService.export_users([])
        assert result is False

@pytest.mark.asyncio
async def test_sheets_export_network_error(db_setup):
    """Тест обработки сетевой ошибки при экспорте."""
    with patch("config.SPREADSHEET_ID", "fake_id"):
        # Мокаем клиент так, чтобы он выбрасывал исключение
        with patch.object(GoogleSheetsService, "get_client", side_effect=Exception("API Error")):
            result = await GoogleSheetsService.export_users([(1, "Test", "User", "Admin")])
            assert result is False
            # Проверяем, что бот не упал, а просто вернул False

@pytest.mark.asyncio
async def test_sheets_export_success_mock(db_setup):
    """Имитация успешного экспорта (проверка цепочки вызовов)."""
    with patch("config.SPREADSHEET_ID", "fake_id"):
        mock_client = AsyncMock()
        mock_sh = AsyncMock()
        mock_ws = AsyncMock()
        
        mock_client.open_by_key.return_value = mock_sh
        mock_sh.worksheet.return_value = mock_ws
        
        with patch.object(GoogleSheetsService, "get_client", return_value=mock_client):
            result = await GoogleSheetsService.export_users([(1, "Test", "User", "Admin")])
            
            assert result is True
            assert mock_client.open_by_key.called
            assert mock_sh.worksheet.called
            assert mock_ws.update.called # Проверяем, что данные были отправлены
