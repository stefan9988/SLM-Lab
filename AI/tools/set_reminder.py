"""Tool for scheduling Telegram reminders."""

from datetime import datetime

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from BE.logger import setup_logger

logger = setup_logger(__name__)

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@tool
async def set_reminder_tool(task: str, remind_at: str) -> str:
    """Schedule a reminder. When the time comes, an agent will execute the task and
    deliver the result to the user via Telegram.

    Call get_current_date_and_time first to determine the current local time, then
    set remind_at to a future value in the same "YYYY-MM-DD HH:MM:SS" format.

    Args:
        task: A fully self-contained instruction for the agent to execute at reminder time.
              The agent that runs this task will have NO memory of the current conversation,
              so every detail needed to carry out the task must be included here — names,
              locations, URLs, quantities, preferences, or any other context the user provided.
              Write it as an explicit, unambiguous directive.
              Good:  "Check the weather forecast for Belgrade for tomorrow and send a summary
                      to the user."
              Good:  "Remind the user to take their 20mg dose of lisinopril."
              Bad:   "Check the weather" (missing location)
              Bad:   "Remind the user about the meeting" (missing all details)
        remind_at: Target date/time in "YYYY-MM-DD HH:MM:SS" format (local server time).
                   Must be in the future. Example: "2026-06-01 14:00:00".
    """
    logger.info("set_reminder_tool invoked (remind_at=%s)", remind_at)
    writer = get_stream_writer()
    writer("Setting reminder…")

    try:
        remind_dt = datetime.strptime(remind_at, _DATETIME_FORMAT)
    except ValueError:
        return (
            f'Error: Invalid remind_at format "{remind_at}". Use "YYYY-MM-DD HH:MM:SS".'
        )

    if remind_dt <= datetime.now():
        return f"Error: remind_at ({remind_at}) must be in the future."

    try:
        from BE.reminder_store import insert_reminder

        reminder_id = await insert_reminder(task, remind_dt)
    except Exception as exc:
        logger.error("set_reminder_tool failed to insert reminder", exc_info=True)
        return f"Error: Failed to save reminder — {exc}"

    logger.info("set_reminder_tool complete (id=%s)", reminder_id)
    writer("Reminder set")
    return f'Reminder set for {remind_at}: "{task}"'
