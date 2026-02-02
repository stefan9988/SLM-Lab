"""PostgreSQL archive store for long-term message persistence."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from BE.database import get_session_factory
from BE.logger import setup_logger
from BE.models import Message, Session

logger = setup_logger(__name__)


class PostgresArchiveStore:
    """Stores conversation history permanently in PostgreSQL."""

    def __init__(self) -> None:
        self._factory = get_session_factory()

    async def save_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Upsert session and replace its messages."""
        metadata = metadata or {}
        now = datetime.now(timezone.utc)

        async with self._factory() as session:
            async with session.begin():
                # Upsert session row
                stmt = pg_insert(Session).values(
                    id=session_id,
                    created_at=now,
                    updated_at=now,
                    model_name=metadata.get("model", None),
                    provider=metadata.get("provider", None),
                )
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

    async def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve full message history for a session."""
        async with self._factory() as session:
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

    async def get_all_sessions(self) -> list[dict[str, Any]]:
        """List all archived sessions with metadata."""
        async with self._factory() as session:
            result = await session.execute(
                select(Session).order_by(Session.updated_at.desc())
            )
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

    async def delete_session(self, session_id: str) -> bool:
        """Delete an archived session and its messages."""
        async with self._factory() as session:
            async with session.begin():
                result = await session.execute(
                    delete(Session).where(Session.id == session_id)
                )
                return result.rowcount > 0


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
    except Exception as exc:
        logger.warning("Failed to create PostgreSQL archive store: %s", exc)
        return None
