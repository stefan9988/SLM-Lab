"""Tests for BE.archive_store using an in-memory SQLite backend."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from BE.archive_store import PostgresArchiveStore
from BE.models import Base, User

TEST_USER_ID = "test-user-id"
TEST_USER_ID_2 = "test-user-id-2"


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
    """Create tables, insert test users, and return a PostgresArchiveStore wired to SQLite."""
    from BE.archive_store import PostgresArchiveStore

    run(create_tables(async_engine))
    run(insert_test_users(session_factory))

    store = PostgresArchiveStore.__new__(PostgresArchiveStore)
    store._factory = session_factory
    return store


async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def insert_test_users(factory):
    """Insert test user records needed for FK constraints."""
    now = datetime.now(timezone.utc)
    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=TEST_USER_ID,
                    email="test@example.com",
                    google_sub="google-sub-123",
                    name="Test User",
                    picture="",
                    created_at=now,
                    last_login_at=now,
                )
            )
            session.add(
                User(
                    id=TEST_USER_ID_2,
                    email="other@example.com",
                    google_sub="google-sub-456",
                    name="Other User",
                    picture="",
                    created_at=now,
                    last_login_at=now,
                )
            )


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
        run(
            archive_store.save_messages(
                "s1", msgs, {"model": "m", "provider": "p"}, user_id=TEST_USER_ID
            )
        )
        result = run(archive_store.get_messages("s1", user_id=TEST_USER_ID))
        assert len(result) == 3
        assert result[0]["type"] == "human"
        assert result[0]["content"] == "message 0"
        assert result[1]["type"] == "ai"
        assert result[1]["thinking"] == "thought"

    def test_get_messages_empty_session(self, run, archive_store):
        result = run(archive_store.get_messages("nonexistent", user_id=TEST_USER_ID))
        assert result == []

    def test_save_replaces_messages(self, run, archive_store):
        run(archive_store.save_messages("s1", _make_messages(2), user_id=TEST_USER_ID))
        run(archive_store.save_messages("s1", _make_messages(4), user_id=TEST_USER_ID))
        result = run(archive_store.get_messages("s1", user_id=TEST_USER_ID))
        assert len(result) == 4

    def test_get_all_sessions(self, run, archive_store):
        run(
            archive_store.save_messages(
                "s1", _make_messages(1), {"model": "m1"}, user_id=TEST_USER_ID
            )
        )
        run(
            archive_store.save_messages(
                "s2", _make_messages(1), {"model": "m2"}, user_id=TEST_USER_ID
            )
        )
        sessions = run(archive_store.get_all_sessions(user_id=TEST_USER_ID))
        assert len(sessions) == 2
        ids = {s["id"] for s in sessions}
        assert ids == {"s1", "s2"}

    def test_get_all_sessions_empty(self, run, archive_store):
        sessions = run(archive_store.get_all_sessions(user_id=TEST_USER_ID))
        assert sessions == []

    def test_delete_session(self, run, archive_store):
        run(archive_store.save_messages("s1", _make_messages(2), user_id=TEST_USER_ID))
        deleted = run(archive_store.delete_session("s1", user_id=TEST_USER_ID))
        assert deleted is True
        assert run(archive_store.get_messages("s1", user_id=TEST_USER_ID)) == []
        sessions = run(archive_store.get_all_sessions(user_id=TEST_USER_ID))
        assert len(sessions) == 0

    def test_delete_nonexistent_session(self, run, archive_store):
        deleted = run(archive_store.delete_session("nope", user_id=TEST_USER_ID))
        assert deleted is False

    def test_upsert_session_metadata(self, run, archive_store):
        run(
            archive_store.save_messages(
                "s1",
                _make_messages(1),
                {"model": "m1", "provider": "p1"},
                user_id=TEST_USER_ID,
            )
        )
        run(
            archive_store.save_messages(
                "s1",
                _make_messages(1),
                {"model": "m2", "provider": "p2"},
                user_id=TEST_USER_ID,
            )
        )
        sessions = run(archive_store.get_all_sessions(user_id=TEST_USER_ID))
        assert len(sessions) == 1
        assert sessions[0]["model_name"] == "m2"
        assert sessions[0]["provider"] == "p2"

    def test_cross_user_isolation_get_messages(self, run, archive_store):
        """User B cannot read User A's session messages."""
        run(archive_store.save_messages("s1", _make_messages(2), user_id=TEST_USER_ID))
        result = run(archive_store.get_messages("s1", user_id=TEST_USER_ID_2))
        assert result == []

    def test_cross_user_isolation_get_all_sessions(self, run, archive_store):
        """get_all_sessions only returns the requesting user's sessions."""
        run(archive_store.save_messages("s1", _make_messages(1), user_id=TEST_USER_ID))
        run(
            archive_store.save_messages("s2", _make_messages(1), user_id=TEST_USER_ID_2)
        )
        sessions_a = run(archive_store.get_all_sessions(user_id=TEST_USER_ID))
        sessions_b = run(archive_store.get_all_sessions(user_id=TEST_USER_ID_2))
        assert len(sessions_a) == 1
        assert sessions_a[0]["id"] == "s1"
        assert len(sessions_b) == 1
        assert sessions_b[0]["id"] == "s2"

    def test_cross_user_isolation_delete(self, run, archive_store):
        """User B cannot delete User A's session."""
        run(archive_store.save_messages("s1", _make_messages(2), user_id=TEST_USER_ID))
        deleted = run(archive_store.delete_session("s1", user_id=TEST_USER_ID_2))
        assert deleted is False
        # Original user can still see it
        result = run(archive_store.get_messages("s1", user_id=TEST_USER_ID))
        assert len(result) == 2


class TestGetAllSessionsWithTitles:
    def test_returns_first_human_message_as_title(self, run, archive_store):
        msgs = [
            {
                "type": "human",
                "content": "What is Python?",
                "thinking": None,
                "model": "m",
                "provider": "p",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "additional_kwargs": None,
            },
            {
                "type": "ai",
                "content": "Python is a programming language.",
                "thinking": None,
                "model": "m",
                "provider": "p",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "additional_kwargs": None,
            },
        ]
        run(archive_store.save_messages("s1", msgs, user_id=TEST_USER_ID))
        sessions = run(archive_store.get_all_sessions_with_titles(user_id=TEST_USER_ID))
        assert len(sessions) == 1
        assert sessions[0]["id"] == "s1"
        assert sessions[0]["title"] == "What is Python?"
        assert sessions[0]["updated_at"] is not None

    def test_truncates_long_titles_to_50_chars(self, run, archive_store):
        long_msg = "A" * 100
        msgs = [
            {
                "type": "human",
                "content": long_msg,
                "thinking": None,
                "model": "m",
                "provider": "p",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "additional_kwargs": None,
            },
        ]
        run(archive_store.save_messages("s1", msgs, user_id=TEST_USER_ID))
        sessions = run(archive_store.get_all_sessions_with_titles(user_id=TEST_USER_ID))
        assert len(sessions[0]["title"]) == 50

    def test_session_without_human_message_gets_default_title(self, run, archive_store):
        msgs = [
            {
                "type": "ai",
                "content": "System response",
                "thinking": None,
                "model": "m",
                "provider": "p",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "additional_kwargs": None,
            },
        ]
        run(archive_store.save_messages("s1", msgs, user_id=TEST_USER_ID))
        sessions = run(archive_store.get_all_sessions_with_titles(user_id=TEST_USER_ID))
        assert sessions[0]["title"] == "New Chat"

    def test_empty_returns_empty_list(self, run, archive_store):
        sessions = run(archive_store.get_all_sessions_with_titles(user_id=TEST_USER_ID))
        assert sessions == []

    def test_cross_user_isolation(self, run, archive_store):
        msgs = _make_messages(2)
        run(archive_store.save_messages("s1", msgs, user_id=TEST_USER_ID))
        run(archive_store.save_messages("s2", msgs, user_id=TEST_USER_ID_2))
        sessions_a = run(
            archive_store.get_all_sessions_with_titles(user_id=TEST_USER_ID)
        )
        sessions_b = run(
            archive_store.get_all_sessions_with_titles(user_id=TEST_USER_ID_2)
        )
        assert len(sessions_a) == 1
        assert sessions_a[0]["id"] == "s1"
        assert len(sessions_b) == 1
        assert sessions_b[0]["id"] == "s2"

    def test_ordered_by_updated_at_desc(self, run, archive_store):
        msgs = _make_messages(1)
        run(archive_store.save_messages("s1", msgs, user_id=TEST_USER_ID))
        run(archive_store.save_messages("s2", msgs, user_id=TEST_USER_ID))
        sessions = run(archive_store.get_all_sessions_with_titles(user_id=TEST_USER_ID))
        assert len(sessions) == 2
        # s2 was saved last, so should appear first
        assert sessions[0]["id"] == "s2"
        assert sessions[1]["id"] == "s1"


class TestEnsureSessionExists:
    def test_creates_new_session(self, run, async_engine, session_factory):
        """ensure_session_exists creates a session row when none exists."""
        from BE.archive_store import ensure_session_exists

        run(create_tables(async_engine))
        run(insert_test_users(session_factory))

        with patch(
            "BE.archive_store.get_session_factory", return_value=session_factory
        ):
            run(ensure_session_exists("new-session", TEST_USER_ID))

        # Verify the session was created
        store = PostgresArchiveStore.__new__(PostgresArchiveStore)
        store._factory = session_factory
        sessions = run(store.get_all_sessions(user_id=TEST_USER_ID))
        assert len(sessions) == 1
        assert sessions[0]["id"] == "new-session"

    def test_idempotent_existing_session_not_modified(
        self, run, async_engine, session_factory
    ):
        """Calling ensure_session_exists on an existing session does not overwrite it."""
        from BE.archive_store import ensure_session_exists

        run(create_tables(async_engine))
        run(insert_test_users(session_factory))

        store = PostgresArchiveStore.__new__(PostgresArchiveStore)
        store._factory = session_factory

        # Create session with metadata via save_messages
        run(
            store.save_messages(
                "s1",
                _make_messages(2),
                {"model": "original-model", "provider": "original-provider"},
                user_id=TEST_USER_ID,
            )
        )

        # Call ensure_session_exists on the same session
        with patch(
            "BE.archive_store.get_session_factory", return_value=session_factory
        ):
            run(ensure_session_exists("s1", TEST_USER_ID))

        # Verify the original session metadata is preserved
        sessions = run(store.get_all_sessions(user_id=TEST_USER_ID))
        assert len(sessions) == 1
        assert sessions[0]["model_name"] == "original-model"
        assert sessions[0]["provider"] == "original-provider"

    def test_skipped_when_postgres_disabled(self, run):
        """ensure_session_exists returns immediately when POSTGRES_ENABLED is False."""
        from BE.archive_store import ensure_session_exists

        with (
            patch("BE.config.settings") as mock_settings,
            patch("BE.archive_store.get_session_factory") as mock_factory,
        ):
            mock_settings.POSTGRES_ENABLED = False
            run(ensure_session_exists("s1", TEST_USER_ID))
            mock_factory.assert_not_called()

    def test_graceful_error_handling(self, run):
        """ensure_session_exists logs a warning instead of raising on DB errors."""
        from BE.archive_store import ensure_session_exists

        with patch(
            "BE.archive_store.get_session_factory",
            side_effect=SQLAlchemyError("connection refused"),
        ):
            # Should not raise
            run(ensure_session_exists("s1", TEST_USER_ID))


class TestCreateStoreFactory:
    @patch("BE.config.settings")
    def test_disabled_returns_none(self, mock_settings):
        from BE import archive_store

        archive_store._archive_store = None
        mock_settings.POSTGRES_ENABLED = False
        result = archive_store.create_store()
        assert result is None

    @patch("BE.archive_store.get_session_factory")
    @patch("BE.config.settings")
    def test_fallback_on_error(self, mock_settings, mock_factory):
        from sqlalchemy.exc import SQLAlchemyError

        from BE import archive_store

        mock_factory.side_effect = SQLAlchemyError("no pg")
        archive_store._archive_store = None
        mock_settings.POSTGRES_ENABLED = True
        result = archive_store.create_store()
        assert result is None
