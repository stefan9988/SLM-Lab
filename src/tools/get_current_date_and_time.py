from datetime import datetime

from langchain_core.tools import tool
from langgraph.config import get_stream_writer


@tool
def get_current_date_and_time() -> str:
    """Returns the current date and time as a formatted string."""
    writer = get_stream_writer()
    writer("Fetching current date and time...")
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
