"""Tests for BE.schema_store using an in-memory SQLite backend."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
def schema_store(run, async_engine, session_factory):
    """Create tables, insert test users, and return a SchemaStore wired to SQLite."""
    from BE.schema_store import SchemaStore

    run(create_tables(async_engine))
    run(insert_test_users(session_factory))

    store = SchemaStore.__new__(SchemaStore)
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
            session.add(User(
                id=TEST_USER_ID,
                email="test@example.com",
                google_sub="google-sub-123",
                name="Test User",
                picture="",
                created_at=now,
                last_login_at=now,
            ))
            session.add(User(
                id=TEST_USER_ID_2,
                email="other@example.com",
                google_sub="google-sub-456",
                name="Other User",
                picture="",
                created_at=now,
                last_login_at=now,
            ))


class TestSchemaStore:
    def test_get_schemas_empty(self, run, schema_store):
        result = run(schema_store.get_schemas(user_id=TEST_USER_ID))
        assert result == []

    def test_create_schema(self, run, schema_store):
        fields = [{"id": "f1", "key": "title", "description": "The title"}]
        result = run(schema_store.create_schema(
            user_id=TEST_USER_ID, name="Invoice", fields=fields
        ))
        assert result["name"] == "Invoice"
        assert result["fields"] == fields
        assert result["id"] is not None
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_get_schemas(self, run, schema_store):
        run(schema_store.create_schema(
            user_id=TEST_USER_ID, name="Schema A", fields=[]
        ))
        run(schema_store.create_schema(
            user_id=TEST_USER_ID, name="Schema B", fields=[]
        ))
        result = run(schema_store.get_schemas(user_id=TEST_USER_ID))
        assert len(result) == 2
        # Ordered by created_at DESC, so B first
        assert result[0]["name"] == "Schema B"
        assert result[1]["name"] == "Schema A"

    def test_update_schema(self, run, schema_store):
        created = run(schema_store.create_schema(
            user_id=TEST_USER_ID, name="Original", fields=[]
        ))
        new_fields = [{"id": "f1", "key": "amount", "description": "Total"}]
        updated = run(schema_store.update_schema(
            created["id"], user_id=TEST_USER_ID, name="Updated", fields=new_fields
        ))
        assert updated is not None
        assert updated["name"] == "Updated"
        assert updated["fields"] == new_fields

    def test_update_schema_not_found(self, run, schema_store):
        result = run(schema_store.update_schema(
            "nonexistent", user_id=TEST_USER_ID, name="X", fields=[]
        ))
        assert result is None

    def test_update_schema_wrong_user(self, run, schema_store):
        created = run(schema_store.create_schema(
            user_id=TEST_USER_ID, name="Mine", fields=[]
        ))
        result = run(schema_store.update_schema(
            created["id"], user_id=TEST_USER_ID_2, name="Stolen", fields=[]
        ))
        assert result is None

    def test_delete_schema(self, run, schema_store):
        created = run(schema_store.create_schema(
            user_id=TEST_USER_ID, name="To Delete", fields=[]
        ))
        deleted = run(schema_store.delete_schema(created["id"], user_id=TEST_USER_ID))
        assert deleted is True
        result = run(schema_store.get_schemas(user_id=TEST_USER_ID))
        assert len(result) == 0

    def test_delete_schema_not_found(self, run, schema_store):
        deleted = run(schema_store.delete_schema("nonexistent", user_id=TEST_USER_ID))
        assert deleted is False

    def test_delete_schema_wrong_user(self, run, schema_store):
        created = run(schema_store.create_schema(
            user_id=TEST_USER_ID, name="Mine", fields=[]
        ))
        deleted = run(schema_store.delete_schema(created["id"], user_id=TEST_USER_ID_2))
        assert deleted is False
        # Original user still has it
        result = run(schema_store.get_schemas(user_id=TEST_USER_ID))
        assert len(result) == 1

    def test_cross_user_isolation(self, run, schema_store):
        run(schema_store.create_schema(
            user_id=TEST_USER_ID, name="User A Schema", fields=[]
        ))
        run(schema_store.create_schema(
            user_id=TEST_USER_ID_2, name="User B Schema", fields=[]
        ))
        a_schemas = run(schema_store.get_schemas(user_id=TEST_USER_ID))
        b_schemas = run(schema_store.get_schemas(user_id=TEST_USER_ID_2))
        assert len(a_schemas) == 1
        assert a_schemas[0]["name"] == "User A Schema"
        assert len(b_schemas) == 1
        assert b_schemas[0]["name"] == "User B Schema"


class TestCreateStoreFactory:
    @patch("BE.config.settings")
    def test_disabled_returns_none(self, mock_settings):
        from BE import schema_store

        schema_store._schema_store = None
        mock_settings.POSTGRES_ENABLED = False
        result = schema_store.create_store()
        assert result is None

    @patch("BE.schema_store.get_session_factory")
    @patch("BE.config.settings")
    def test_fallback_on_error(self, mock_settings, mock_factory):
        from sqlalchemy.exc import SQLAlchemyError

        from BE import schema_store

        mock_factory.side_effect = SQLAlchemyError("no pg")
        schema_store._schema_store = None
        mock_settings.POSTGRES_ENABLED = True
        result = schema_store.create_store()
        assert result is None
