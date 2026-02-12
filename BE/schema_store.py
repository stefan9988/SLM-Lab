"""PostgreSQL store for extraction schemas."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from BE.database import get_session_factory
from BE.logger import setup_logger
from BE.models import ExtractionSchema

logger = setup_logger(__name__)

__all__ = ["SchemaStore", "create_store"]


class SchemaStore:
    """CRUD operations for extraction schemas in PostgreSQL."""

    def __init__(self) -> None:
        self._factory = get_session_factory()

    async def get_schemas(self, *, user_id: str) -> list[dict]:
        """Return all schemas for a user, ordered by created_at DESC."""
        async with self._factory() as session:
            result = await session.execute(
                select(ExtractionSchema)
                .where(ExtractionSchema.user_id == user_id)
                .order_by(ExtractionSchema.created_at.desc())
            )
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "fields": row.fields,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ]

    async def create_schema(
        self, *, user_id: str, name: str, fields: list[dict]
    ) -> dict:
        """Insert a new schema and return it."""
        schema = ExtractionSchema(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            fields=fields,
        )
        async with self._factory() as session:
            async with session.begin():
                session.add(schema)
            await session.refresh(schema)
            return {
                "id": schema.id,
                "name": schema.name,
                "fields": schema.fields,
                "created_at": schema.created_at.isoformat() if schema.created_at else None,
                "updated_at": schema.updated_at.isoformat() if schema.updated_at else None,
            }

    async def update_schema(
        self, schema_id: str, *, user_id: str, name: str, fields: list[dict]
    ) -> dict | None:
        """Update an existing schema. Returns None if not found or not owned."""
        async with self._factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(ExtractionSchema).where(
                        ExtractionSchema.id == schema_id,
                        ExtractionSchema.user_id == user_id,
                    )
                )
                schema = result.scalar_one_or_none()
                if schema is None:
                    return None
                schema.name = name
                schema.fields = fields
                schema.updated_at = datetime.now(timezone.utc)
            await session.refresh(schema)
            return {
                "id": schema.id,
                "name": schema.name,
                "fields": schema.fields,
                "created_at": schema.created_at.isoformat() if schema.created_at else None,
                "updated_at": schema.updated_at.isoformat() if schema.updated_at else None,
            }

    async def delete_schema(self, schema_id: str, *, user_id: str) -> bool:
        """Delete a schema. Returns False if not found or not owned."""
        async with self._factory() as session:
            async with session.begin():
                result = await session.execute(
                    delete(ExtractionSchema).where(
                        ExtractionSchema.id == schema_id,
                        ExtractionSchema.user_id == user_id,
                    )
                )
                return result.rowcount > 0


_schema_store: SchemaStore | None = None


def create_store() -> SchemaStore | None:
    """Create schema store with graceful fallback."""
    global _schema_store
    if _schema_store is not None:
        return _schema_store

    from BE.config import settings

    if not settings.POSTGRES_ENABLED:
        logger.info("PostgreSQL schema store disabled")
        return None

    try:
        _schema_store = SchemaStore()
        logger.info("PostgreSQL schema store created")
        return _schema_store
    except SQLAlchemyError as exc:
        logger.warning("Failed to create PostgreSQL schema store: %s", exc)
        return None
