import pytest
import importlib
import logging

# Список критических модулей для проверки импорта
CRITICAL_MODULES = [
    "database.db",
    "services.management_service",
    "services.notification_service",
    "services.ui_service",
    "services.event_service",
    "handlers.admin",
    "handlers.events",
    "handlers.moderator",
    "handlers.common",
    "main"
]

@pytest.mark.parametrize("module_name", CRITICAL_MODULES)
def test_imports_integrity(module_name):
    """
    Проверяет, что модуль может быть импортирован без ошибок (NameError, ImportError и т.д.).
    Это базовый Smoke Test для предотвращения регрессий в импортах.
    """
    try:
        importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(f"❌ КРИТИЧЕСКАЯ ОШИБКА ИМПОРТА в модуле {module_name}: {e}")

def test_management_service_signatures():
    """Проверяет наличие новых методов в ManagementService."""
    from services.management_service import ManagementService
    assert hasattr(ManagementService, "submit_request")
    assert hasattr(ManagementService, "resolve_request")
    assert hasattr(ManagementService, "get_pending_request_id")
