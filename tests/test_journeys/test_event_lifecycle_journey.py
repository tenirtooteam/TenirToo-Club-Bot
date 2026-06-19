# -*- coding: utf-8 -*-
import pytest
from unittest.mock import AsyncMock, patch
from database import db
from handlers.events import reject_event_handler, delete_event_init, join_event, leave_event
from handlers.common import confirm_execution
from services.management_service import ManagementService
import config
from aiogram.methods import SendMessage

@pytest.mark.asyncio
async def test_event_rejection_journey(db_setup, mock_bot, user_session):
    # 1. Setup creator and create a pending event
    creator_id = 11111
    db.add_user(creator_id, "Creator", "User")
    
    event_id = db.create_event(
        title="Summit Elbrus",
        start_date="2026-08-01",
        end_date="2026-08-10",
        start_iso="2026-08-01",
        end_iso="2026-08-10",
        creator_id=creator_id
    )
    # Event is pending by default (is_approved=0)
    
    # Create audit request for event approval
    req_id = db.create_audit_request(creator_id, "event_approval", event_id)
    
    # 2. Admin rejects the event
    admin_id = config.ADMIN_ID
    db.add_user(admin_id, "Admin", "User")
    db.grant_role(admin_id, db.get_role_id("admin"))
    
    session = user_session(user_id=admin_id, chat_id=admin_id)
    
    with patch("services.event_service.EventService.notify_admins_for_approval", new_callable=AsyncMock):
        await session.send_callback(
            handler=reject_event_handler,
            callback_data=f"event_reject:{event_id}"
        )
        
    # Check that event was deleted from DB (ManagementService.resolve_request with "rejected" deletes event)
    details = db.get_event_details(event_id)
    assert details is None or details.get("event_id") is None
    
    # Audit request must be resolved (either status changed or request deleted)
    req = db.get_audit_request(req_id)
    assert req is None or req.status == "rejected"


@pytest.mark.asyncio
async def test_event_destructive_deletion_journey(db_setup, mock_bot, user_session):
    # 1. Setup creator and create approved event
    creator_id = 22222
    db.add_user(creator_id, "Creator", "User")
    
    event_id = db.create_event(
        title="Hike in Ala-Archa",
        start_date="2026-06-30",
        end_date=None,
        start_iso="2026-06-30",
        end_iso=None,
        creator_id=creator_id
    )
    db.approve_event(event_id) # Set approved
    
    session = user_session(user_id=creator_id, chat_id=creator_id)
    
    # 2. Trigger delete event screen (requires confirmation keyboard)
    await session.send_callback(
        handler=delete_event_init,
        callback_data=f"event_delete:{event_id}"
    )
    
    # Check that bot sent confirmation prompt
    calls = mock_bot.mock_calls
    assert len(calls) > 0
    
    # 3. Confirm deletion
    # confirm_exe_event_del:{event_id}:0
    await session.send_callback(
        handler=confirm_execution,
        callback_data=f"confirm_exe_event_del:{event_id}:0"
    )
    
    # Verify event is deleted in DB
    details = db.get_event_details(event_id)
    assert details is None or details.get("event_id") is None


@pytest.mark.asyncio
async def test_event_leave_journey(db_setup, mock_bot, user_session):
    # 1. Setup event, creator, and participant
    creator_id = 33333
    participant_id = 44444
    
    db.add_user(creator_id, "Creator", "User")
    db.add_user(participant_id, "Participant", "User")
    
    event_id = db.create_event(
        title="Trek to Kol-Tor",
        start_date="2026-07-05",
        end_date=None,
        start_iso="2026-07-05",
        end_iso=None,
        creator_id=creator_id
    )
    db.approve_event(event_id)
    
    # Participant directly joins event (since it's approved and they write directly)
    # Note: normally event_join submits a request, but we can toggle it to test leave flow
    db.add_event_participant(event_id, participant_id)
    
    assert db.is_event_participant(event_id, participant_id)
    
    # 2. Participant decides to leave event
    session = user_session(user_id=participant_id, chat_id=participant_id)
    
    await session.send_callback(
        handler=leave_event,
        callback_data=f"event_leave:{event_id}"
    )
    
    # Verify they are no longer a participant
    assert not db.is_event_participant(event_id, participant_id)


@pytest.mark.asyncio
async def test_participation_request_rejection_journey(db_setup, mock_bot, user_session):
    # 1. Setup event and applicant
    creator_id = 55555
    applicant_id = 66666
    
    db.add_user(creator_id, "Creator", "User")
    db.add_user(applicant_id, "Applicant", "User")
    
    event_id = db.create_event(
        title="Peak Lenin Expedition",
        start_date="2026-07-20",
        end_date=None,
        start_iso="2026-07-20",
        end_iso=None,
        creator_id=creator_id
    )
    db.approve_event(event_id)
    
    # 2. Applicant joins event (creates pending request)
    session_app = user_session(user_id=applicant_id, chat_id=applicant_id)
    await session_app.send_callback(
        handler=join_event,
        callback_data=f"event_join:{event_id}"
    )
    
    # Verify request is created in DB
    req_id = ManagementService.get_user_pending_request_id(applicant_id, "event_participation", event_id)
    assert req_id is not None
    
    # 3. Admin rejects participation request
    admin_id = config.ADMIN_ID
    db.add_user(admin_id, "Admin", "User")
    db.grant_role(admin_id, db.get_role_id("admin"))
    
    success, msg = await ManagementService.resolve_request(mock_bot, req_id, "rejected", comment="Rejected by admin.")
    assert success
    
    # Verify applicant is not added as participant
    assert not db.is_event_participant(event_id, applicant_id)
    
    # Verify request is resolved
    req = db.get_audit_request(req_id)
    assert req.status == "rejected"
