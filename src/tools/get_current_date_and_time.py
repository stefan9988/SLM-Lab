from datetime import datetime

from langchain_core.tools import tool


@tool
def get_current_date_and_time() -> str:
    """Returns the current date and time as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")