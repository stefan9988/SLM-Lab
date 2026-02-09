"""Async service for saving uploaded files to PostgreSQL."""

import base64
from typing import Optional
from uuid import uuid4

from BE.logger import setup_logger

logger = setup_logger(__name__)


def _decode_data_url(data_url: str) -> bytes:
    """Strip the ``data:<mime>;base64,`` prefix and base64-decode to raw bytes."""
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    return base64.b64decode(data_url)


async def save_file(
    original_name: str,
    mime_type: str,
    data_url_content: str,
    size_bytes: int,
    user_id: str,
    session_id: str | None = None,
) -> Optional[str]:
    """Decode a data-URL file and persist it in the ``file_uploads`` table.

    Returns the UUID primary key on success, or ``None`` on any failure
    (PostgreSQL disabled, empty content, invalid base64, DB error) so callers
    can degrade gracefully.
    """
    from BE.config import settings

    if not settings.POSTGRES_ENABLED:
        logger.debug("PostgreSQL disabled — skipping file save for %s", original_name)
        return None

    if not data_url_content or not data_url_content.strip():
        logger.warning("Empty content for file %s — skipping", original_name)
        return None

    try:
        raw_bytes = _decode_data_url(data_url_content)
    except Exception:
        logger.warning("Invalid base64 data for file %s — skipping", original_name)
        return None

    if len(raw_bytes) == 0:
        logger.warning("Decoded 0 bytes for file %s — skipping", original_name)
        return None

    try:
        from BE.database import get_session_factory
        from BE.models import FileUpload

        factory = get_session_factory()
        async with factory() as session:
            file_id = str(uuid4())
            upload = FileUpload(
                id=file_id,
                original_name=original_name,
                mime_type=mime_type,
                size_bytes=size_bytes,
                content=raw_bytes,
                user_id=user_id,
                session_id=session_id,
            )
            session.add(upload)
            await session.commit()
            logger.info(
                "Saved file %s (id=%s, %d bytes)", original_name, file_id, len(raw_bytes)
            )
            return file_id
    except Exception as exc:
        logger.warning("Failed to save file %s to DB: %s", original_name, exc)
        return None
