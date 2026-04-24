import pytest
from services.help_service import HelpService

def test_help_service_get_existing_key():
    """Verify that HelpService returns correct text for an existing key."""
    text = HelpService.get_help("templates")
    assert "О шаблонах групп" in text
    assert "Синхронизировать" in text

def test_help_service_get_missing_key():
    """Verify that HelpService returns a fallback message for missing keys."""
    text = HelpService.get_help("non_existent_key_123")
    assert "информация для данного раздела пока не добавлена" in text
    assert "⚠️" in text

def test_help_service_content_is_str():
    """Ensure that the registry values are all strings."""
    for key, value in HelpService.HELP_CONTENT.items():
        assert isinstance(key, str)
        assert isinstance(value, str)
