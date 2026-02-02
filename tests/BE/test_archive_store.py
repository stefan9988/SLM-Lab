"""Tests for BE.archive_store using an in-memory SQLite backend."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from BE.models import Base


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def async_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    return engine


@pytest.fixture
def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def run(event_loop):
    """Helper to run coroutines in the test event loop."""
    return event_loop.run_until_complete


@pytest.fixture
def archive_store(run, async_engine, session_factory):
    """Create tables and return a PostgresArchiveStore wired to SQLite."""
    from BE.archive_store import PostgresArchiveStore

    run(create_tables(async_engine))

    store = PostgresArchiveStore.__new__(PostgresArchiveStore)
    store._factory = session_factory
    return store


async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _make_messages(n=2):
    now = datetime.now(timezone.utc).isoformat()
    msgs = []
    for i in range(n):
        role = "human" if i % 2 == 0 else "ai"
        msgs.append(
            {
                "type": role,
                "content": f"message {i}",
                "thinking": "thought" if role == "ai" else None,
                "model": "test-model",
                "provider": "test-provider",
                "timestamp": now,
                "additional_kwargs": {"key": "value"} if role == "ai" else None,
            }
        )
    return msgs


class TestPostgresArchiveStore:
    def test_save_and_get_messages(self, run, archive_store):
        msgs = _make_messages(3)
        run(archive_store.save_messages("s1", msgs, {"model": "m", "provider": "p"}))
        result = run(archive_store.get_messages("s1"))
        assert len(result) == 3
        assert result[0]["role"] == "human"
        assert result[0]["content"] == "message 0"
        assert result[1]["role"] == "ai"
        assert result[1]["thinking"] == "thought"

    def test_get_messages_empty_session(self, run, archive_store):
        result = run(archive_store.get_messages("nonexistent"))
        assert result == []

    def test_save_replaces_messages(self, run, archive_store):
        run(archive_store.save_messages("s1", _make_messages(2)))
        run(archive_store.save_messages("s1", _make_messages(4)))
        result = run(archive_store.get_messages("s1"))
        assert len(result) == 4

    def test_get_all_sessions(self, run, archive_store):
        run(archive_store.save_messages("s1", _make_messages(1), {"model": "m1"}))
        run(archive_store.save_messages("s2", _make_messages(1), {"model": "m2"}))
        sessions = run(archive_store.get_all_sessions())
        assert len(sessions) == 2
        ids = {s["id"] for s in sessions}
        assert ids == {"s1", "s2"}

    def test_get_all_sessions_empty(self, run, archive_store):
        sessions = run(archive_store.get_all_sessions())
        assert sessions == []

    def test_delete_session(self, run, archive_store):
        run(archive_store.save_messages("s1", _make_messages(2)))
        deleted = run(archive_store.delete_session("s1"))
        assert deleted is True
        assert run(archive_store.get_messages("s1")) == []
        sessions = run(archive_store.get_all_sessions())
        assert len(sessions) == 0

    def test_delete_nonexistent_session(self, run, archive_store):
        deleted = run(archive_store.delete_session("nope"))
        assert deleted is False

    def test_upsert_session_metadata(self, run, archive_store):
        run(archive_store.save_messages("s1", _make_messages(1), {"model": "m1", "provider": "p1"}))
        run(archive_store.save_messages("s1", _make_messages(1), {"model": "m2", "provider": "p2"}))
        sessions = run(archive_store.get_all_sessions())
        assert len(sessions) == 1
        assert sessions[0]["model_name"] == "m2"
        assert sessions[0]["provider"] == "p2"


class TestCreateStoreFactory:
    @patch("BE.config.settings")
    def test_disabled_returns_none(self, mock_settings):
        from BE import archive_store

        archive_store._archive_store = None
        mock_settings.POSTGRES_ENABLED = False
        result = archive_store.create_store()
        assert result is None

    @patch("BE.archive_store.get_session_factory", side_effect=Exception("no pg"))
    @patch("BE.config.settings")
    def test_fallback_on_error(self, mock_settings, mock_factory):
        from BE import archive_store

        archive_store._archive_store = None
        mock_settings.POSTGRES_ENABLED = True
        result = archive_store.create_store()
        assert result is None
