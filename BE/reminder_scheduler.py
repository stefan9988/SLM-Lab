"""Background polling loop that fires due reminders via the reminder agent."""

import asyncio

from BE.logger import setup_logger
from BE.reminder_store import get_due_reminders, mark_reminder_sent

logger = setup_logger(__name__)

_POLL_INTERVAL = 30  # seconds


async def run_reminder_scheduler(agent) -> None:
    """Poll for due reminders every 30 seconds and process them via the reminder agent."""
    logger.info("Reminder scheduler started (poll interval=%ds)", _POLL_INTERVAL)
    while True:
        try:
            reminders = await get_due_reminders()
            for reminder in reminders:
                try:
                    # Mark sent before invoking — at-most-once delivery
                    await mark_reminder_sent(reminder.id)
                    prompt = (
                        "[SYSTEM REMINDER] Execute the following scheduled task and "
                        "deliver the result to the user via send_telegram_message_tool:"
                        f"\n\n{reminder.task}"
                    )
                    await agent.invoke(
                        prompt,
                        session_id=f"reminder_{reminder.id}",
                        user_id="reminder_scheduler",
                    )
                    logger.info("Reminder processed (id=%s)", reminder.id)
                except Exception:
                    logger.error(
                        "Failed to process reminder (id=%s)", reminder.id, exc_info=True
                    )
        except Exception:
            logger.error("Reminder scheduler poll error", exc_info=True)

        await asyncio.sleep(_POLL_INTERVAL)
