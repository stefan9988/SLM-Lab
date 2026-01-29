from langchain_core.tools import tool
from langchain_community.tools import BraveSearch
from langgraph.config import get_stream_writer

from config import settings

_brave = BraveSearch.from_api_key(api_key=settings.BRAVE_SEARCH_API_KEY, search_kwargs={"count": 3})


@tool
def brave_search_tool(query: str) -> str:
    """Search the web using Brave Search engine."""
    writer = get_stream_writer()
    writer(f"Searching the web for: {query}")
    result = _brave.invoke(query)
    writer("Search complete")
    return result
