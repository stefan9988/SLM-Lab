"""Tests for BE.reminder_store using an in-memory SQLite backend."""

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from BE.models import Base, Reminder


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def async_engine():
    return create_async_engine("sqlite+aiosqlite://", echo=False)


@pytest.fixture
def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def run(event_loop):
    return event_loop.run_until_complete


@pytest.fixture
def store(run, async_engine, session_factory, monkeypatch):
    """Create tables and patch get_session_factory to use the in-memory SQLite engine."""
    from BE import reminder_store

    run(_create_tables(async_engine))
    monkeypatch.setattr(reminder_store, "get_session_factory", lambda: session_factory)
    return reminder_store


async def _create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class TestInsertReminder:
    def test_inserts_and_returns_id(self, run, store):
        remind_at = datetime.now() + timedelta(hours=1)
        reminder_id = run(store.insert_reminder("Buy milk", remind_at))
        assert isinstance(reminder_id, str)
        assert len(reminder_id) > 0

    def test_stored_reminder_is_unsent(self, run, store, session_factory):
        remind_at = datetime.now() + timedelta(hours=1)
        reminder_id = run(store.insert_reminder("Take medicine", remind_at))

        async def fetch():
            async with session_factory() as session:
                from sqlalchemy import select

                result = await session.execute(
                    select(Reminder).where(Reminder.id == reminder_id)
                )
                return result.scalar_one()

        reminder = run(fetch())
        assert reminder.task == "Take medicine"
        assert reminder.sent is False
        assert reminder.remind_at == remind_at


class TestGetDueReminders:
    def test_returns_past_due_unsent(self, run, store):
        past = datetime.now() - timedelta(minutes=5)
        run(store.insert_reminder("Overdue task", past))
        due = run(store.get_due_reminders())
        assert len(due) == 1
        assert due[0].task == "Overdue task"

    def test_excludes_future_reminders(self, run, store):
        future = datetime.now() + timedelta(hours=2)
        run(store.insert_reminder("Future task", future))
        due = run(store.get_due_reminders())
        assert len(due) == 0

    def test_excludes_already_sent(self, run, store):
        past = datetime.now() - timedelta(minutes=1)
        reminder_id = run(store.insert_reminder("Already sent", past))
        run(store.mark_reminder_sent(reminder_id))
        due = run(store.get_due_reminders())
        assert len(due) == 0

    def test_returns_multiple_due(self, run, store):
        past = datetime.now() - timedelta(minutes=1)
        run(store.insert_reminder("First", past))
        run(store.insert_reminder("Second", past))
        due = run(store.get_due_reminders())
        assert len(due) == 2


class TestMarkReminderSent:
    def test_marks_sent(self, run, store, session_factory):
        past = datetime.now() - timedelta(minutes=1)
        reminder_id = run(store.insert_reminder("Check email", past))
        run(store.mark_reminder_sent(reminder_id))

        async def fetch():
            async with session_factory() as session:
                from sqlalchemy import select

                result = await session.execute(
                    select(Reminder).where(Reminder.id == reminder_id)
                )
                return result.scalar_one()

        reminder = run(fetch())
        assert reminder.sent is True
