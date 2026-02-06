"""Async utilities for background task execution with retry logic."""

import asyncio
from typing import Any, Callable, Coroutine

from BE.logger import setup_logger

logger = setup_logger(__name__)

__all__ = ["init_loop", "run_with_retry", "schedule_background_task"]

_main_loop: asyncio.AbstractEventLoop | None = None


def init_loop() -> None:
    """Capture the main event loop. Call from an async context during startup."""
    global _main_loop
    _main_loop = asyncio.get_running_loop()


async def run_with_retry(
    coro_func: Callable[[], Coroutine[Any, Any, Any]],
    *,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 30.0,
    task_name: str = "background_task",
) -> bool:
    """Execute an async function with timeout and exponential backoff retry.

    Args:
        coro_func: A callable that returns a coroutine (not the coroutine itself).
        max_retries: Maximum number of retry attempts.
        retry_delay: Initial delay between retries in seconds.
        timeout: Timeout for each attempt in seconds.
        task_name: Name for logging purposes.

    Returns:
        True if the task succeeded, False otherwise.
    """
    for attempt in range(max_retries):
        try:
            await asyncio.wait_for(coro_func(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.error(
                "%s attempt %d/%d timed out after %.1fs",
                task_name,
                attempt + 1,
                max_retries,
                timeout,
            )
        except Exception as exc:
            logger.error(
                "%s attempt %d/%d failed: %s",
                task_name,
                attempt + 1,
                max_retries,
                exc,
                exc_info=True,
            )

        if attempt < max_retries - 1:
            delay = retry_delay * (2**attempt)
            logger.debug("%s retrying in %.1fs", task_name, delay)
            await asyncio.sleep(delay)

    logger.error("%s failed after %d attempts", task_name, max_retries)
    return False


def schedule_background_task(
    coro_func: Callable[[], Coroutine[Any, Any, Any]],
    *,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 30.0,
    task_name: str = "background_task",
) -> bool:
    """Schedule a fire-and-forget background task with retry logic.

    Args:
        coro_func: A callable that returns a coroutine (not the coroutine itself).
        max_retries: Maximum number of retry attempts.
        retry_delay: Initial delay between retries in seconds.
        timeout: Timeout for each attempt in seconds.
        task_name: Name for logging purposes.

    Returns:
        True if the task was scheduled, False if no event loop is running.
    """
    async def _run_task() -> None:
        await run_with_retry(
            coro_func,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            task_name=task_name,
        )

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run_task())
        return True
    except RuntimeError:
        pass

    if _main_loop is not None and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(_run_task(), _main_loop)
        return True

    logger.debug("No event loop available, skipping %s", task_name)
    return False
