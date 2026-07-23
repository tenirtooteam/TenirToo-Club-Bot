import pytest
from unittest.mock import AsyncMock, patch

from database import db
from services.management_service import ManagementService


def _seed_approved_event_with_pending_participation():
    """Одобренный поход + pending-заявка на участие от другого пользователя."""
    db.add_user(1, "Creator", "One")
    db.add_user(2, "Joiner", "Two")
    event_id = db.create_event("Поход", "1 июня", None, 1, 1, "2026-06-01", None)
    req_id = db.create_audit_request(2, "event_participation", event_id)
    return event_id, req_id


@pytest.mark.asyncio
async def test_approved_participation_refreshes_announcement(mock_bot, db_setup):
    """
    node-3 (FR-004): одобрение заявки на участие ОБНОВЛЯЕТ публичные анонсы похода
    (состав/capacity-метр остаются правдивыми) и НЕ шлёт ложное уведомление о
    «прямом входе» (текст notify_organizers_of_direct_join для модерируемого approve — ложь).
    """
    event_id, req_id = _seed_approved_event_with_pending_participation()

    with patch("services.announcement_service.AnnouncementService.refresh_announcements",
               new_callable=AsyncMock) as mock_refresh, \
         patch("services.event_service.EventService.notify_organizers_of_direct_join",
               new_callable=AsyncMock) as mock_direct_join, \
         patch("services.management_service.NotificationService.send_to_users",
               new_callable=AsyncMock) as mock_notify:
        ok, _ = await ManagementService.resolve_request(mock_bot, req_id, "approved")

    assert ok is True, "Одобрение должно выиграть переход"
    assert db.is_event_participant(event_id, 2), "Заявитель добавлен в состав"
    mock_refresh.assert_awaited_once_with(mock_bot, "event", event_id)
    mock_direct_join.assert_not_awaited()  # модерируемое одобрение != прямой вход
    assert mock_notify.call_count == 1, "Заявитель уведомлён ровно один раз"


@pytest.mark.asyncio
async def test_rejected_participation_does_not_refresh(mock_bot, db_setup):
    """
    Отклонение заявки на участие состав НЕ меняет → рефреш анонса не требуется
    (никакой публичной лжи не возникает).
    """
    event_id, req_id = _seed_approved_event_with_pending_participation()

    with patch("services.announcement_service.AnnouncementService.refresh_announcements",
               new_callable=AsyncMock) as mock_refresh, \
         patch("services.management_service.NotificationService.send_to_users",
               new_callable=AsyncMock):
        ok, _ = await ManagementService.resolve_request(mock_bot, req_id, "rejected")

    assert ok is True
    assert not db.is_event_participant(event_id, 2), "Отклонение не добавляет в состав"
    mock_refresh.assert_not_awaited()
