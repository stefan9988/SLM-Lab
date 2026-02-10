"""Async service for saving and retrieving uploaded files from PostgreSQL."""

import base64
import os
from typing import Optional
from uuid import uuid4

from BE.logger import setup_logger

logger = setup_logger(__name__)

MAX_READABLE_SIZE = 10 * 1024 * 1024  # 10 MB

_TEXT_MIME_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-yaml",
    "application/yaml",
    "application/toml",
    "application/csv",
)

_TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
    ".java", ".c", ".cpp", ".h", ".hpp", ".rs", ".go", ".rb", ".sh",
    ".bat", ".ps1", ".sql", ".log", ".ini", ".cfg", ".conf", ".env",
}


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


def _is_text_mime(mime_type: str) -> bool:
    """Return True if *mime_type* is a known textual MIME type."""
    mime_lower = mime_type.lower()
    return any(mime_lower.startswith(prefix) for prefix in _TEXT_MIME_PREFIXES)


def _looks_like_text_extension(filename: str) -> bool:
    """Return True if *filename* has a known text file extension."""
    _, ext = os.path.splitext(filename)
    return ext.lower() in _TEXT_EXTENSIONS


def _extract_pdf_text(raw: bytes) -> str:
    """Extract text from a PDF byte buffer using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    pages: list[str] = []
    with fitz.open(stream=raw, filetype="pdf") as doc:
        for page in doc:
            pages.append(page.get_text())
    return "\n".join(pages)


async def get_file_content(file_id: str) -> str:
    """Retrieve and return the text content of an uploaded file.

    Raises:
        RuntimeError: If PostgreSQL is disabled.
        FileNotFoundError: If the file_id does not exist.
        ValueError: If the file content is binary / unreadable.
    """
    from BE.config import settings

    if not settings.POSTGRES_ENABLED:
        raise RuntimeError("PostgreSQL is disabled — cannot read file content")

    from BE.database import get_session_factory
    from BE.models import FileUpload
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(FileUpload).where(FileUpload.id == file_id)
        )
        upload = result.scalar_one_or_none()

    if upload is None:
        raise FileNotFoundError(f"No file found with id '{file_id}'")

    raw: bytes = upload.content
    if len(raw) > MAX_READABLE_SIZE:
        raise ValueError(
            f"File is too large to read ({len(raw)} bytes, max {MAX_READABLE_SIZE})"
        )

    mime = (upload.mime_type or "").lower()
    name = upload.original_name or ""

    # PDF extraction
    if mime == "application/pdf" or name.lower().endswith(".pdf"):
        return _extract_pdf_text(raw)

    # Known text MIME type
    if _is_text_mime(mime):
        return raw.decode("utf-8")

    # Known text extension
    if _looks_like_text_extension(name):
        return raw.decode("utf-8")

    # Fallback: try UTF-8 decode
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(
            f"File '{name}' appears to be binary and cannot be read as text"
        )
