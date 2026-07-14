"""
Тесты feature 010 — Sheets-синк: дебаунс, владение фоновой задачей, shutdown-flush,
устранение N+1 по ролям (№17).

TDD (R-PROC-3): тесты пишутся ПЕРВЫМИ (RED), затем реализация (GREEN).
Мок-ассерты проверяют args+kwargs (R-TEST-3).
БД изолирована через autouse-фикстуру db_setup (tests/conftest.py).
"""
import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest

from database import db
import services.management_service as ms
from services.management_service import ManagementService


# --- Общие helper'ы (T001) ---

def _mock_exports():
    """
    Патчит все экспортные корутины GoogleSheetsService на AsyncMock.
    Возвращает контекст-менеджер-стек словарём {name: AsyncMock} после входа.
    Использовать как: with _exports_patched() as m: ...
    """
    return {
        "export_users": patch("services.google_sheets_service.GoogleSheetsService.export_users", new_callable=AsyncMock),
        "export_groups": patch("services.google_sheets_service.GoogleSheetsService.export_groups", new_callable=AsyncMock),
        "export_events": patch("services.google_sheets_service.GoogleSheetsService.export_events", new_callable=AsyncMock),
        "export_event_participants": patch("services.google_sheets_service.GoogleSheetsService.export_event_participants", new_callable=AsyncMock),
    }


class _exports_patched:
    """Контекст: патчит все export_* и отдаёт dict со стартованными моками."""
    def __enter__(self):
        self._patchers = _mock_exports()
        self.mocks = {name: p.start() for name, p in self._patchers.items()}
        return self.mocks

    def __exit__(self, *exc):
        for p in self._patchers.values():
            p.stop()
        return False


WINDOW = 0.05  # малое окно коалесценции для детерминированных тестов


@pytest.fixture(autouse=True)
def _small_debounce_window(monkeypatch):
    """Патчит окно дебаунса на малое значение — тесты не ждут прод-2с."""
    monkeypatch.setattr(ms, "SHEETS_SYNC_DEBOUNCE_SECONDS", WINDOW)


@pytest.fixture(autouse=True)
def _clean_pending_syncs():
    """Изоляция реестра pending-задач между тестами."""
    ms._pending_syncs.clear()
    yield
    ms._pending_syncs.clear()


def _seed_user_with_role(user_id: int, role_name: str, topic_id=None):
    db.add_user(user_id, f"U{user_id}", "T")
    if topic_id is not None:
        db.register_topic_if_not_exists(topic_id)  # FK user_roles.topic_id → topic_names
    rid = db.get_role_id(role_name)
    db.grant_role(user_id, rid, topic_id)


# ============================================================================
# Phase 2 (Foundational) — T002: батч-фетч ролей (устранение N+1, FR-006)
# ============================================================================

class TestGetRolesForUsers:
    """FR-006 / SC-005: пакетное получение ролей вместо N+1-цикла."""

    def test_returns_roles_grouped_by_user(self):
        _seed_user_with_role(1, "moderator", topic_id=100)
        _seed_user_with_role(2, "admin", topic_id=None)
        db.add_user(3, "U3", "T")  # без ролей

        result = db.get_roles_for_users([1, 2, 3])

        assert (("moderator", 100)) in result[1]
        assert (("admin", None)) in result[2]
        assert result[3] == []  # присутствует ключ, пустой список

    def test_admin_id_gets_synthesized_superadmin(self):
        from config import ADMIN_ID
        db.add_user(ADMIN_ID, "Boss", "")

        result = db.get_roles_for_users([ADMIN_ID])

        assert ("superadmin", None) in result[ADMIN_ID]

    def test_empty_input_returns_empty_mapping(self):
        assert db.get_roles_for_users([]) == {}


# ============================================================================
# Phase 3 (US2) — T005: владение фоновой задачей, логирование ошибок
# ============================================================================

@pytest.mark.asyncio
class TestBackgroundTaskOwnership:
    """FR-003/FR-004, SC-002/SC-003/SC-006: задача владеется, ошибки логируются."""

    async def test_trigger_holds_task_reference_then_releases(self):
        with _exports_patched() as mocks:
            db.add_user(1, "A", "B")
            ManagementService._trigger_sheets_sync("users")

            # Реестр удерживает задачу до завершения (нет GC-гонки).
            assert len(ms._pending_syncs) == 1
            task = next(iter(ms._pending_syncs.values()))

            await task

            # После завершения ключ снят из реестра (add_done_callback).
            assert len(ms._pending_syncs) == 0
            assert task.done() and not task.cancelled()
            assert task.exception() is None
            mocks["export_users"].assert_awaited()

    async def test_task_exception_is_logged_not_swallowed(self, caplog):
        with patch(
            "services.google_sheets_service.GoogleSheetsService.export_users",
            new_callable=AsyncMock, side_effect=Exception("boom"),
        ), patch("services.google_sheets_service.GoogleSheetsService.export_groups", new_callable=AsyncMock), \
           patch("services.google_sheets_service.GoogleSheetsService.export_events", new_callable=AsyncMock), \
           patch("services.google_sheets_service.GoogleSheetsService.export_event_participants", new_callable=AsyncMock):
            db.add_user(1, "A", "B")
            with caplog.at_level(logging.ERROR, logger=ms.logger.name):
                ManagementService._trigger_sheets_sync("users")
                task = next(iter(ms._pending_syncs.values()))
                await task

            # Ошибка задачи зафиксирована в логах, а не проглочена.
            assert any("boom" in r.getMessage() for r in caplog.records)
            # Задача завершилась штатно (исключение поглощено try/except внутри), не destroyed.
            assert task.done() and task.exception() is None


# ============================================================================
# Phase 4 (US1) — T009: коалесценция всплеска триггеров
# ============================================================================

@pytest.mark.asyncio
class TestDebounceCoalescing:
    """FR-001/FR-002, SC-001: всплеск триггеров одного ключа → одна выгрузка."""

    async def test_rapid_triggers_same_mode_export_once(self):
        with _exports_patched() as mocks:
            db.add_user(1, "A", "B")
            for _ in range(5):
                ManagementService._trigger_sheets_sync("users")

            # Выжила ровно одна задача под ключом (остальные отменены).
            assert len(ms._pending_syncs) == 1

            await asyncio.sleep(WINDOW * 4)

            mocks["export_users"].assert_awaited_once()

    async def test_different_modes_each_export_once(self):
        with _exports_patched() as mocks:
            db.add_user(1, "A", "B")
            ManagementService._trigger_sheets_sync("users")
            ManagementService._trigger_sheets_sync("groups")

            # Разные ключи ведутся независимо.
            assert len(ms._pending_syncs) == 2

            await asyncio.sleep(WINDOW * 4)

            mocks["export_users"].assert_awaited_once()
            mocks["export_groups"].assert_awaited_once()

    async def test_event_participants_distinct_entities_not_merged(self):
        details = {"participants": [], "leads": [], "title": "T"}
        with _exports_patched() as mocks, patch(
            "services.event_service.EventService.get_event_details", return_value=details
        ):
            ManagementService._trigger_sheets_sync("event_participants", 10)
            ManagementService._trigger_sheets_sync("event_participants", 20)

            # Разные entity_id не склеиваются в один ключ.
            assert len(ms._pending_syncs) == 2

            await asyncio.sleep(WINDOW * 4)

            assert mocks["export_event_participants"].await_count == 2


# ============================================================================
# Phase 5 (US3) — T012: shutdown-flush
# ============================================================================

@pytest.mark.asyncio
class TestShutdownFlush:
    """FR-005, SC-004: остановка немедленно прогоняет отложенные выгрузки."""

    async def test_flush_runs_pending_immediately(self):
        with _exports_patched() as mocks:
            db.add_user(1, "A", "B")
            ManagementService._trigger_sheets_sync("users")

            # flush не ждёт окна коалесценции — выгрузка происходит немедленно.
            await ManagementService.flush_pending_syncs()

            mocks["export_users"].assert_awaited_once()
            assert len(ms._pending_syncs) == 0

    async def test_flush_multiple_keys(self):
        with _exports_patched() as mocks:
            db.add_user(1, "A", "B")
            ManagementService._trigger_sheets_sync("users")
            ManagementService._trigger_sheets_sync("groups")

            await ManagementService.flush_pending_syncs()

            mocks["export_users"].assert_awaited_once()
            mocks["export_groups"].assert_awaited_once()
            assert len(ms._pending_syncs) == 0

    async def test_flush_empty_registry_is_noop(self):
        with _exports_patched() as mocks:
            await ManagementService.flush_pending_syncs()

            for m in mocks.values():
                m.assert_not_awaited()
            assert len(ms._pending_syncs) == 0
