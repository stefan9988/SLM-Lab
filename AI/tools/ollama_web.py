from urllib.parse import urlparse

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from BE.config import settings
from BE.logger import setup_logger
from ollama import Client

logger = setup_logger(__name__)


def _get_client() -> Client:
    """Create an Ollama client with the API key configured."""
    return Client(
        host=settings.OLLAMA_BASE_URL,
        headers={"authorization": f"Bearer {settings.OLLAMA_API_KEY}"},
    )


@tool
def ollama_web_search_tool(query: str) -> str:
    """Search the web using Ollama's built-in web search."""
    logger.info("ollama_web_search_tool invoked (query=%s)", query)
    writer = get_stream_writer()
    writer(f'Searching for "{query}"…')
    try:
        client = _get_client()
        response = client.web_search(query)
        result = str(response)
        logger.info("ollama_web_search_tool complete (result_length=%d)", len(result))
        writer("Search complete")
        return result
    except Exception:
        logger.error("ollama_web_search_tool failed", exc_info=True)
        raise


@tool
def ollama_web_fetch_tool(url: str) -> str:
    """Fetch content from a URL using Ollama's web fetch capability."""
    logger.info("ollama_web_fetch_tool invoked (url=%s)", url)
    writer = get_stream_writer()
    writer(f"Fetching {urlparse(url).netloc}…")
    try:
        client = _get_client()
        result = client.web_fetch(url)
        result_str = str(result)
        logger.info(
            "ollama_web_fetch_tool complete (result_length=%d)", len(result_str)
        )
        writer("Page fetched")
        return result_str
    except Exception:
        logger.error("ollama_web_fetch_tool failed", exc_info=True)
        raise
