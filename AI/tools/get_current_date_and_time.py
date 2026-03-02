from datetime import datetime

from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from BE.logger import setup_logger

logger = setup_logger(__name__)


@tool
def get_current_date_and_time() -> str:
    """Returns the current date and time as a formatted string."""
    logger.info("get_current_date_and_time invoked")
    writer = get_stream_writer()
    writer("Getting current date and time…")
    result = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.debug("get_current_date_and_time result: %s", result)
    return result
