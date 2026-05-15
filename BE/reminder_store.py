"""Async DB helpers for reminder persistence."""

from datetime import datetime

from sqlalchemy import select, update

from BE.database import get_session_factory
from BE.logger import setup_logger
from BE.models import Reminder

logger = setup_logger(__name__)

__all__ = ["insert_reminder", "get_due_reminders", "mark_reminder_sent"]


async def insert_reminder(task: str, remind_at: datetime) -> str:
    """Persist a new reminder and return its id."""
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            reminder = Reminder(task=task, remind_at=remind_at)
            session.add(reminder)
    logger.info("Reminder inserted (id=%s, remind_at=%s)", reminder.id, remind_at)
    return reminder.id


async def get_due_reminders() -> list[Reminder]:
    """Return unsent reminders whose remind_at is on or before now."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Reminder).where(
                Reminder.sent.is_(False),
                Reminder.remind_at <= datetime.now(),
            )
        )
        return list(result.scalars().all())


async def mark_reminder_sent(reminder_id: str) -> None:
    """Mark a reminder as sent."""
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            await session.execute(
                update(Reminder).where(Reminder.id == reminder_id).values(sent=True)
            )
    logger.debug("Reminder marked sent (id=%s)", reminder_id)
