import re

from langchain_core.tools import tool
from langgraph.config import get_config, get_stream_writer

from BE.file_store import get_file_content
from BE.logger import setup_logger

logger = setup_logger(__name__)

MAX_RETURN_CHARS = 500_000

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@tool
async def read_file_content_tool(file_id: str) -> str:
    """Read the text content of an uploaded file by its file_id.

    Use this tool when the user attaches a file and you need to read its
    contents.  The file_id is found in the attachment annotation, e.g.
    ``[Attached file: report.pdf (file_id: abc-123)]``.

    Args:
        file_id: The UUID of the uploaded file.
    """
    logger.info("read_file_content_tool invoked (file_id=%s)", file_id)
    writer = get_stream_writer()
    writer("Reading file…")

    if not _UUID_RE.match(file_id):
        logger.warning("Invalid UUID format: %s", file_id)
        return "Error: Invalid file_id format — expected a UUID."

    config = get_config()
    user_id: str = config.get("configurable", {}).get("user_id", "")
    if not user_id:
        logger.warning("No user_id in config — cannot verify file ownership")
        return "Error: Unable to verify file ownership."

    try:
        content = await get_file_content(file_id, user_id=user_id)
    except FileNotFoundError as exc:
        logger.warning("File not found: %s", exc)
        return f"Error: {exc}"
    except ValueError as exc:
        logger.warning("Unsupported file: %s", exc)
        return f"Error: {exc}"
    except RuntimeError as exc:
        logger.warning("Runtime error reading file: %s", exc)
        return f"Error: {exc}"

    if len(content) > MAX_RETURN_CHARS:
        content = content[:MAX_RETURN_CHARS] + (
            f"\n\n[Content truncated — showed first {MAX_RETURN_CHARS:,} of "
            f"{len(content):,} characters]"
        )

    logger.info(
        "read_file_content_tool complete (file_id=%s, length=%d)",
        file_id,
        len(content),
    )
    writer("File read")
    return content
