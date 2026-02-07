from langchain_core.tools import tool
from langchain_community.tools import BraveSearch
from langgraph.config import get_stream_writer

from BE.logger import setup_logger

logger = setup_logger(__name__)

_brave: BraveSearch | None = None


def _get_brave() -> BraveSearch:
    global _brave
    if _brave is None:
        from BE.config import settings

        _brave = BraveSearch.from_api_key(
            api_key=settings.BRAVE_SEARCH_API_KEY, search_kwargs={"count": 3}
        )
    return _brave


@tool
def brave_search_tool(query: str) -> str:
    """Search the web using Brave Search engine."""
    logger.info("brave_search_tool invoked (query=%s)", query)
    writer = get_stream_writer()
    writer(f"Searching the web for: {query}")
    try:
        result = _get_brave().invoke(query)
        logger.info("brave_search_tool complete (result_length=%d)", len(result))
        writer("Search complete")
        return result
    except Exception:
        logger.error("brave_search_tool failed", exc_info=True)
        raise
