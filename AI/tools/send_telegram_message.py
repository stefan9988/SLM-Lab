import httpx
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from BE.logger import setup_logger

logger = setup_logger(__name__)


@tool
def send_telegram_message_tool(msg: str) -> str:
    """
    Send a Telegram message to the configured user.

    Args:
        msg: The message text to send
    """
    from telegram_bot.config import settings

    logger.info("send_telegram_message_tool invoked")
    writer = get_stream_writer()
    writer("Sending Telegram message…")

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": settings.TELEGRAM_ALLOWED_USER_ID, "text": msg}

    try:
        response = httpx.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("send_telegram_message_tool complete")
        writer("Telegram message sent")
        return "Message sent successfully"
    except Exception:
        logger.error("send_telegram_message_tool failed", exc_info=True)
        raise
