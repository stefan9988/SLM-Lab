"""PostgreSQL archive store for long-term message persistence."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from BE.database import get_session_factory
from BE.logger import setup_logger
from BE.models import Message, Session

logger = setup_logger(__name__)

__all__ = ["PostgresArchiveStore", "create_store"]


class PostgresArchiveStore:
    """Stores conversation history permanently in PostgreSQL."""

    def __init__(self) -> None:
        self._factory = get_session_factory()

    async def save_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        metadata: dict[str, str] | None = None,
        user_id: str = "",
    ) -> None:
        """Upsert session and replace its messages."""
        metadata = metadata or {}
        now = datetime.now(timezone.utc)

        async with self._factory() as session:
            async with session.begin():
                # Upsert session row
                values = {
                    "id": session_id,
                    "user_id": user_id,
                    "created_at": now,
                    "updated_at": now,
                    "model_name": metadata.get("model", None),
                    "provider": metadata.get("provider", None),
                }
                stmt = pg_insert(Session).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "updated_at": now,
                        "model_name": metadata.get("model", None),
                        "provider": metadata.get("provider", None),
                    },
                )
                await session.execute(stmt)

                # Replace messages: delete old, insert new
                await session.execute(
                    delete(Message).where(Message.session_id == session_id)
                )
                for msg in messages:
                    session.add(
                        Message(
                            session_id=session_id,
                            role=msg.get("type", ""),
                            content=msg.get("content", ""),
                            thinking=msg.get("thinking"),
                            model=msg.get("model"),
                            provider=msg.get("provider"),
                            timestamp=datetime.fromisoformat(msg["timestamp"])
                            if msg.get("timestamp")
                            else now,
                            additional_kwargs=msg.get("additional_kwargs"),
                        )
                    )

    async def get_messages(
        self, session_id: str, user_id: str = ""
    ) -> list[dict[str, Any]]:
        """Retrieve full message history for a session."""
        async with self._factory() as session:
            # Verify ownership if user_id provided
            if user_id:
                ownership = await session.execute(
                    select(Session.id).where(
                        Session.id == session_id, Session.user_id == user_id
                    )
                )
                if ownership.scalar_one_or_none() is None:
                    return []

            result = await session.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.id)
            )
            rows = result.scalars().all()
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "thinking": m.thinking,
                    "model": m.model,
                    "provider": m.provider,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    "additional_kwargs": m.additional_kwargs,
                }
                for m in rows
            ]

    async def get_all_sessions(self, user_id: str = "") -> list[dict[str, Any]]:
        """List all archived sessions with metadata, filtered by user."""
        async with self._factory() as session:
            query = select(Session).order_by(Session.updated_at.desc())
            if user_id:
                query = query.where(Session.user_id == user_id)
            result = await session.execute(query)
            rows = result.scalars().all()
            return [
                {
                    "id": s.id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                    "model_name": s.model_name,
                    "provider": s.provider,
                }
                for s in rows
            ]

    async def delete_session(self, session_id: str, user_id: str = "") -> bool:
        """Delete an archived session and its messages."""
        async with self._factory() as session:
            async with session.begin():
                # Delete session with ownership filter first
                delete_sess = delete(Session).where(Session.id == session_id)
                if user_id:
                    delete_sess = delete_sess.where(Session.user_id == user_id)
                result = await session.execute(delete_sess)
                if result.rowcount == 0:
                    return False

                # Only delete messages if session was owned by the user
                await session.execute(
                    delete(Message).where(Message.session_id == session_id)
                )
                return True


_archive_store: PostgresArchiveStore | None = None


def create_store() -> PostgresArchiveStore | None:
    """Create archive store with graceful fallback."""
    global _archive_store
    if _archive_store is not None:
        return _archive_store

    from BE.config import settings

    if not settings.POSTGRES_ENABLED:
        logger.info("PostgreSQL archive disabled")
        return None

    try:
        _archive_store = PostgresArchiveStore()
        logger.info("PostgreSQL archive store created")
        return _archive_store
    except SQLAlchemyError as exc:
        logger.warning("Failed to create PostgreSQL archive store: %s", exc)
        return None
