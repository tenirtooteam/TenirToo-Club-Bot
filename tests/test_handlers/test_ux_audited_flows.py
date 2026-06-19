import pytest
from unittest.mock import AsyncMock, patch
from database import db
from handlers.events import show_event_card
from services.management_service import ManagementService

@pytest.mark.asyncio
async def test_pending_event_view_restriction_for_member(db_setup, create_callback, mock_bot):
    """
    Test that a pending event shows a truncated card without action buttons to a normal member.
    """
    creator_id = 1001
    member_id = 777
    db.add_user(creator_id, "Creator", "User")
    db.add_user(member_id, "Member", "User")

    # Create event in pending state (is_approved=0)
    event_id = db.create_event("Pending Walk", "2026-05-15", None, creator_id, is_approved=0)

    callback, state = await create_callback(user_id=member_id, data=f"event_view:{event_id}")

    # We patch sterile_show to inspect the keyboard and text shown
    with patch("services.ui_service.UIService.sterile_show", new_callable=AsyncMock) as mock_show:
        await show_event_card(callback, event_id, state)

        # Verify show was called
        assert mock_show.called
        args, kwargs = mock_show.call_args
        card_text = args[2] if len(args) > 2 else kwargs.get("text", "")
        reply_markup = args[3] if len(args) > 3 else kwargs.get("reply_markup")

        # Check text states it's on moderation
        assert "на модерации" in card_text.lower()

        # Check keyboard doesn't have "Иду" or "Не иду" actions
        buttons = []
        if reply_markup and hasattr(reply_markup, "inline_keyboard"):
            for row in reply_markup.inline_keyboard:
                for btn in row:
                    buttons.append(btn.text)

        assert "✅ Иду" not in buttons
        assert "🚫 Не иду" not in buttons
        assert "🚶 Отменить заявку" not in buttons

@pytest.mark.asyncio
async def test_cancel_join_request_flow(db_setup, create_callback, mock_bot):
    """
    Test that canceling a join request removes the audit request and updates the UI.
    """
    creator_id = 1001
    applicant_id = 888
    db.add_user(creator_id, "Creator", "User")
    db.add_user(applicant_id, "Applicant", "User")

    # Approved event so they can click "join"
    event_id = db.create_event("Approved Walk", "2026-05-15", None, creator_id, is_approved=1)

    # Create a pending audit request manually
    req_id = db.create_audit_request(applicant_id, "event_participation", event_id)
    assert req_id is not None

    # Simulate callback event_cancel_join:{event_id}
    callback, state = await create_callback(user_id=applicant_id, data=f"event_cancel_join:{event_id}")

    # We'll import inside the handler call to avoid import errors before the handler exists
    from handlers.events import cancel_join_handler

    with patch("aiogram.types.CallbackQuery.answer", new_callable=AsyncMock) as mock_answer, \
         patch("handlers.events.view_event", new_callable=AsyncMock) as mock_view:
        await cancel_join_handler(callback, state)

        mock_answer.assert_called_once_with("✅ Заявка на участие отменена.", show_alert=True)
        assert mock_view.called

    # Check that audit request is gone
    check_req_id = ManagementService.get_user_pending_request_id(applicant_id, "event_participation", event_id)
    assert check_req_id is None
