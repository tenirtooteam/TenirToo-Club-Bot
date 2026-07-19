# -*- coding: utf-8 -*-
import pytest
from unittest.mock import AsyncMock, patch
from database import db
from web.routers.dashboard import get_dashboard_init, toggle_event_participation_direct

@pytest.mark.asyncio
async def test_tma_dashboard_init(db_setup, mock_bot):
    user_id = 12345
    db.add_user(user_id, "Elon", "Musk")
    db.update_topic_name(10, "First Topic")
    db.grant_direct_access(user_id, 10)

    # Create an active event
    event_id = db.create_event(
        title="Elbrus Hike",
        start_date="2026-08-01",
        end_date=None,
        start_iso="2026-08-01",
        end_iso=None,
        creator_id=user_id
    )
    db.approve_event(event_id)

    # Call FastAPI controller directly
    response = await get_dashboard_init(user_id=user_id)

    assert response["user_id"] == user_id
    assert response["name"] == "Elon Musk"
    assert response["is_admin"] is False
    assert response["stats"]["events_active"] == 1
    assert response["stats"]["topics_available"] == 1


@pytest.mark.asyncio
async def test_tma_toggle_reactivity(db_setup, mock_bot):
    user_id = 12345
    db.add_user(user_id, "Elon", "Musk")

    event_id = db.create_event(
        title="Kazarman Rally",
        start_date="2026-09-01",
        end_date=None,
        start_iso="2026-09-01",
        end_iso=None,
        creator_id=user_id
    )
    db.approve_event(event_id)

    # Initially, user is not a participant
    assert not db.is_event_participant(event_id, user_id)

    # Patch loader.bot so the lazy import in controller retrieves mock_bot
    with patch("loader.bot", mock_bot):
        # We patch AnnouncementService.refresh_announcements to verify it is called
        with patch("services.announcement_service.AnnouncementService.refresh_announcements", new_callable=AsyncMock) as mock_refresh:
            # Call toggle endpoint (should join)
            # We also need to patch notify_organizers_of_direct_join
            with patch("services.event_service.EventService.notify_organizers_of_direct_join", new_callable=AsyncMock):
                response = await toggle_event_participation_direct(event_id=event_id, action="join", user_id=user_id)

                assert response["success"] is True
                # Verify user is participant now
                assert db.is_event_participant(event_id, user_id)

                # [Feature 014] The dashboard toggle now routes through
                # EventService.apply_participation_change; refresh is invoked at the event
                # level, i.e. it fans out to EVERY published announcement copy (refresh-all),
                # not a single hand-edited message.
                mock_refresh.assert_called_once_with(mock_bot, "event", event_id)
