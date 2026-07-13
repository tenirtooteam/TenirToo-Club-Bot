"""Characterization tests for feature 008 №20 — Dedup Permission Layer.

These tests capture the CURRENT observable behavior of the permission layer
(`database/permissions.py::can_write` and
`services/permission_service.py::PermissionService.is_superadmin`) as a baseline.
They are GREEN on the unmodified code and MUST stay green after the cleanup —
the change removes dead/duplicate code without altering behavior (R-PROC-3).

Fixtures: isolated per-test DB via the autouse `db_setup` fixture in
tests/conftest.py; ADMIN_ID is pinned to 999999999 by the autouse
`mock_config_ids` fixture (R-TEST-1).
"""
import config
from database import db
from services.permission_service import PermissionService

TOPIC_ID = 555


def _grant_superadmin_role(user_id: int) -> None:
    """Assign a real 'superadmin' role row in the isolated DB."""
    role_id = db.get_role_id("superadmin")
    assert role_id, "seed role 'superadmin' must exist after init_db()"
    db.grant_role(user_id, role_id, None)


def _seed_user_and_topic(user_id: int) -> None:
    """Satisfy the FKs of direct_topic_access (users, topic_names) before grant."""
    db.add_user(user_id, "Test", "User")
    db.update_topic_name(TOPIC_ID, "Test Topic")


# --- User Story 1: single point of direct-access check -----------------------

def test_can_write_true_when_direct_access_granted():
    """[US1] User with a direct_topic_access row → can_write True."""
    user_id = 123
    _seed_user_and_topic(user_id)
    assert db.grant_direct_access(user_id, TOPIC_ID) is True
    assert db.can_write(user_id, TOPIC_ID) is True


def test_can_write_false_when_no_direct_access():
    """[US1] User without a direct_topic_access row → can_write False."""
    assert db.can_write(456, TOPIC_ID) is False


def test_direct_access_duplicate_removed():
    """[US1] The dead duplicate has_direct_access is gone from the layer;
    can_write is the single point of direct-access checking.
    """
    assert not hasattr(db, "has_direct_access")
    from database import permissions
    assert not hasattr(permissions, "has_direct_access")


# --- User Story 2: honest is_superadmin semantics ----------------------------

def test_is_superadmin_true_for_admin_with_role():
    """[US2] user_id == ADMIN_ID and a real superadmin role in DB → True."""
    admin_id = config.ADMIN_ID
    db.add_user(admin_id, "Admin", "Root")
    _grant_superadmin_role(admin_id)
    assert PermissionService.is_superadmin(admin_id) is True


def test_is_superadmin_true_for_admin_without_role():
    """[US2] Key case: user_id == ADMIN_ID with NO superadmin role row still
    returns True — the result is independent of the DB (ADMIN_ID is authoritative).
    """
    assert PermissionService.is_superadmin(config.ADMIN_ID) is True


def test_is_superadmin_false_for_non_admin():
    """[US2] Any other user id → False."""
    assert PermissionService.is_superadmin(config.ADMIN_ID + 1) is False
