import re

from langchain_core.tools import tool
from langgraph.config import get_config, get_stream_writer

from BE.async_utils import run_async_from_sync
from BE.logger import setup_logger
from BE.vector_store import search_chunks

logger = setup_logger(__name__)

_MAX_QUERIES = 10

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@tool
def search_chunks_tool(
    file_id: str, queries: list[str], num_results: int = 5
) -> str:
    """Search within an uploaded document for relevant text chunks.

    Uses hybrid search (semantic similarity + keyword matching) to find
    the most relevant sections of a document.  Call this when the user
    asks a question about an uploaded file and you need to find specific
    passages.

    Args:
        file_id: The UUID of the uploaded file (from the attachment annotation).
        queries: A list of search queries describing what to look for.
        num_results: Number of results to return (default 5, max 20).
    """
    logger.info(
        "search_chunks_tool invoked (file_id=%s, queries=%d)",
        file_id,
        len(queries),
    )
    writer = get_stream_writer()
    writer(f"Searching document chunks (file_id={file_id})")

    if not _UUID_RE.match(file_id):
        logger.warning("Invalid UUID format: %s", file_id)
        return "Error: Invalid file_id format — expected a UUID."

    config = get_config()
    user_id: str = config.get("configurable", {}).get("user_id", "")
    if not user_id:
        logger.warning("No user_id in config — cannot verify file ownership")
        return "Error: Unable to verify file ownership."

    if not queries:
        return "Error: At least one search query is required."

    if len(queries) > _MAX_QUERIES:
        queries = queries[:_MAX_QUERIES]

    num_results = max(1, min(num_results, 20))

    try:
        results = run_async_from_sync(
            search_chunks(
                queries=queries,
                file_id=file_id,
                user_id=user_id,
                limit=num_results,
            )
        )
    except Exception as exc:
        logger.error("search_chunks_tool error: %s", exc)
        return f"Error: Failed to search document — {exc}"

    if not results:
        writer("No matching chunks found")
        return "No matching chunks found for the given queries."

    parts = []
    for i, r in enumerate(results, 1):
        page_info = f" [Page {r['page_number']}]" if r.get("page_number") is not None else ""
        parts.append(
            f"[{i}] Chunk {r['chunk_index']}{page_info} (score: {r['score']:.4f})\n"
            f"{r['chunk_text']}"
        )

    writer(f"Found {len(results)} matching chunks")
    logger.info(
        "search_chunks_tool complete (file_id=%s, results=%d)",
        file_id,
        len(results),
    )
    return "\n\n---\n\n".join(parts)
