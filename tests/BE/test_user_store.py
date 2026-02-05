"""Tests for BE.user_store module."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from BE.models import Base, User


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
    return event_loop.run_until_complete


@pytest.fixture
def db_ready(run, async_engine, session_factory):
    """Create tables and patch get_session_factory for user_store."""

    async def _create():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    run(_create())
    with patch("BE.user_store.get_session_factory", return_value=session_factory):
        yield session_factory


class TestUpsertUser:
    def test_creates_new_user(self, run, db_ready):
        from BE.user_store import upsert_user

        user_id = run(
            upsert_user(
                email="alice@example.com",
                name="Alice",
                picture="pic.jpg",
                google_sub="gsub-alice",
            )
        )
        assert user_id  # non-empty UUID string

        # Verify in DB
        factory = db_ready

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    select(User).where(User.google_sub == "gsub-alice")
                )
                u = result.scalar_one()
                assert u.email == "alice@example.com"
                assert u.name == "Alice"
                assert u.id == user_id

        run(_check())

    def test_upsert_updates_on_relogin(self, run, db_ready):
        from BE.user_store import upsert_user

        uid1 = run(
            upsert_user(
                email="bob@example.com",
                name="Bob",
                picture="pic1.jpg",
                google_sub="gsub-bob",
            )
        )
        uid2 = run(
            upsert_user(
                email="bob_new@example.com",
                name="Robert",
                picture="pic2.jpg",
                google_sub="gsub-bob",
            )
        )
        assert uid1 == uid2  # same user

        factory = db_ready

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    select(User).where(User.id == uid1)
                )
                u = result.scalar_one()
                assert u.email == "bob_new@example.com"
                assert u.name == "Robert"
                assert u.picture == "pic2.jpg"

        run(_check())

    def test_idempotent_call(self, run, db_ready):
        from BE.user_store import upsert_user

        uid1 = run(
            upsert_user(
                email="carol@example.com",
                name="Carol",
                picture="",
                google_sub="gsub-carol",
            )
        )
        uid2 = run(
            upsert_user(
                email="carol@example.com",
                name="Carol",
                picture="",
                google_sub="gsub-carol",
            )
        )
        assert uid1 == uid2
