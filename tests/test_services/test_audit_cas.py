import pytest
from unittest.mock import AsyncMock, patch

from database import db
from services.management_service import ManagementService


def _seed_pending_participation():
    """Создаёт одобренный поход и pending-заявку на участие от др. пользователя."""
    db.add_user(1, "Creator", "One")
    db.add_user(2, "Joiner", "Two")
    event_id = db.create_event("Поход", "1 июня", None, 1, 1, "2026-06-01", None)
    req_id = db.create_audit_request(2, "event_participation", event_id)
    return event_id, req_id


@pytest.mark.asyncio
async def test_concurrent_resolve_only_one_wins(mock_bot, db_setup):
    """
    BUG-5: два резолва, оба прошедшие pre-check со статусом pending (гонка через
    await), должны дать ровно один сайд-эффект + одно уведомление. Атомарный CAS
    в БД пропускает только первого.
    """
    event_id, req_id = _seed_pending_participation()
    pending_snapshot = db.get_audit_request(req_id)  # оба «прочитали» pending

    with patch("services.management_service.db.get_audit_request", return_value=pending_snapshot), \
         patch("services.management_service.NotificationService.send_to_users", new_callable=AsyncMock) as mock_notify:
        ok1, _ = await ManagementService.resolve_request(mock_bot, req_id, "approved")
        ok2, _ = await ManagementService.resolve_request(mock_bot, req_id, "approved")

    assert ok1 is True, "Первый резолв должен выиграть переход"
    assert ok2 is False, "Второй резолв обязан проиграть гонку (CAS)"
    assert mock_notify.call_count == 1, "Уведомление ровно одно — без дублей"
    assert db.is_event_participant(event_id, 2)


@pytest.mark.asyncio
async def test_already_resolved_is_noop(mock_bot, db_setup):
    """BUG-5: повторный резолв уже обработанной заявки — no-op, без сайд-эффектов."""
    _, req_id = _seed_pending_participation()

    with patch("services.management_service.NotificationService.send_to_users", new_callable=AsyncMock) as mock_notify:
        ok1, _ = await ManagementService.resolve_request(mock_bot, req_id, "approved")
        ok2, _ = await ManagementService.resolve_request(mock_bot, req_id, "approved")

    assert ok1 is True
    assert ok2 is False
    assert mock_notify.call_count == 1


@pytest.mark.asyncio
async def test_deleted_between_read_and_cas_fails_closed(mock_bot, db_setup):
    """
    C1 (spec BUG-5 edge): заявка удалена после первичного чтения, но до CAS →
    resolve_audit_request возвращает False (rowcount==0), 0 сайд-эффектов, 0 уведомлений.
    """
    event_id, req_id = _seed_pending_participation()
    pending_snapshot = db.get_audit_request(req_id)
    db.delete_audit_request(req_id)  # исчезла в полёте

    with patch("services.management_service.db.get_audit_request", return_value=pending_snapshot), \
         patch("services.management_service.NotificationService.send_to_users", new_callable=AsyncMock) as mock_notify:
        ok, _ = await ManagementService.resolve_request(mock_bot, req_id, "approved")

    assert ok is False, "Fail-closed: пропавшую заявку резолвить нельзя"
    assert mock_notify.call_count == 0, "Проигравший/пустой CAS не шлёт уведомление"
    assert not db.is_event_participant(event_id, 2), "Никаких сайд-эффектов при проигранном CAS"
