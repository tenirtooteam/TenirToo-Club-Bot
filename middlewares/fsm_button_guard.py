# middlewares/fsm_button_guard.py
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

class FsmButtonGuardMiddleware(BaseMiddleware):
    """
    [CP-3.58] Middleware to block and delete callback clicks on obsolete messages
    when the user is inside an active FSM state in private messages.
    """
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if not event.message or event.message.chat.type != "private":
            return await handler(event, data)

        state: FSMContext = data.get("state")
        if not state:
            return await handler(event, data)

        current_state = await state.get_state()
        if current_state is None:
            # No active FSM state, older buttons are safe
            return await handler(event, data)

        state_data = await state.get_data()
        last_menu_id = state_data.get("last_menu_id")

        if last_menu_id is not None and event.message.message_id != last_menu_id:
            # Whitelisted callbacks that should bypass validation
            bypass_exact = {"landing", "close_menu", "admin_confirm_onboarding"}
            bypass_prefixes = ["approve_event:", "reject_event:", "ann_join:"]

            data_str = event.data or ""
            is_bypass = (
                data_str in bypass_exact or
                any(data_str.startswith(p) for p in bypass_prefixes)
            )

            if not is_bypass:
                logger.warning(
                    f"⚠️ Blocked obsolete callback click (message_id: {event.message.message_id}, "
                    f"expected last_menu_id: {last_menu_id}) in state {current_state}."
                )
                try:
                    await event.bot.delete_message(
                        chat_id=event.message.chat.id,
                        message_id=event.message.message_id
                    )
                except Exception as e:
                    logger.error(f"Failed to delete obsolete message: {e}")
                return # Block execution of subsequent handlers

        return await handler(event, data)
