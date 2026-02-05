"""User upsert logic for Google OAuth login."""

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from BE.database import get_session_factory
from BE.logger import setup_logger
from BE.models import User

logger = setup_logger(__name__)


async def upsert_user(
    email: str, name: str, picture: str, google_sub: str
) -> str:
    """Create or update a user by google_sub, returning the user's UUID id."""
    factory = get_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        async with session.begin():
            stmt = pg_insert(User).values(
                email=email,
                name=name,
                picture=picture,
                google_sub=google_sub,
                created_at=now,
                last_login_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["google_sub"],
                set_={
                    "email": email,
                    "name": name,
                    "picture": picture,
                    "last_login_at": now,
                },
            ).returning(User.id)
            result = await session.execute(stmt)
            user_id = result.scalar_one()
            logger.info("Upserted user %s (google_sub=%s)", user_id, google_sub)
            return user_id
