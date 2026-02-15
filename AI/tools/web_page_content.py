import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from BE.logger import setup_logger

logger = setup_logger(__name__)

MAX_RETURN_CHARS = 500_000
REQUEST_TIMEOUT = 30.0
MAX_CONTENT_BYTES = 5_000_000  # 5 MB

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SLM-Lab/1.0; +https://github.com/)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _extract_text(html: str) -> str:
    """Parse HTML and return readable plain text."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


@tool
async def web_page_content_tool(url: str) -> str:
    """Fetch and extract readable text content from a web page.

    Use this tool when you need to read the full content of a web page,
    for example after finding a relevant URL via brave_search_tool.

    Args:
        url: The full URL of the web page to fetch (must start with http:// or https://).
    """
    logger.info("web_page_content_tool invoked (url=%s)", url)
    writer = get_stream_writer()
    writer(f"Fetching web page: {url}")

    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT,
            headers=_HEADERS,
            max_redirects=5,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Timeout fetching URL: %s", url)
        return f"Error: Request timed out after {REQUEST_TIMEOUT}s."
    except httpx.TooManyRedirects:
        logger.warning("Too many redirects for URL: %s", url)
        return "Error: Too many redirects."
    except httpx.HTTPStatusError as exc:
        logger.warning("HTTP %d for URL: %s", exc.response.status_code, url)
        return f"Error: HTTP {exc.response.status_code}."
    except httpx.RequestError as exc:
        logger.warning("Request error for URL %s: %s", url, exc)
        return f"Error: Could not fetch URL — {exc.__class__.__name__}."

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        return f"Error: Unsupported content type '{content_type}'. This tool only reads HTML/text pages."

    raw = response.text
    if len(raw.encode("utf-8", errors="replace")) > MAX_CONTENT_BYTES:
        raw = raw[: MAX_CONTENT_BYTES // 2]

    text = _extract_text(raw)

    if not text.strip():
        return "Warning: Page fetched successfully but no readable text content was found."

    if len(text) > MAX_RETURN_CHARS:
        text = text[:MAX_RETURN_CHARS] + (
            f"\n\n[Content truncated — showed first {MAX_RETURN_CHARS:,} of "
            f"{len(text):,} characters]"
        )

    logger.info(
        "web_page_content_tool complete (url=%s, length=%d)", url, len(text)
    )
    writer("Page fetched successfully")
    return text
