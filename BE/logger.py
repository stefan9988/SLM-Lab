"""Centralized logging configuration for SLM-Lab."""

import logging
import os
import re

__all__ = ["setup_logger", "redact_url"]


def redact_url(url: str) -> str:
    """Redact password from a URL for safe logging.

    Args:
        url: URL that may contain credentials.

    Returns:
        URL with password replaced by asterisks.
    """
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1****\2", url)


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI color codes based on log level."""

    COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(name: str, level: str | None = None) -> logging.Logger:
    """Create and return a configured logger.

    Args:
        name: Logger name (typically __name__).
        level: Log level string. Defaults to LOG_LEVEL env var or INFO.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level = level or os.environ.get("LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    handler = logging.StreamHandler()
    handler.setFormatter(
        ColoredFormatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")
    )
    logger.addHandler(handler)

    return logger
