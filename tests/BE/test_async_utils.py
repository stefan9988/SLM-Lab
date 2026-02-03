"""Tests for BE.async_utils module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from BE.async_utils import run_with_retry, schedule_background_task


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def run(event_loop):
    """Helper to run coroutines in the test event loop."""
    return event_loop.run_until_complete


class TestRunWithRetry:
    """Tests for run_with_retry function."""

    def test_success_on_first_attempt(self, run):
        """Task succeeds on first attempt."""
        mock_func = AsyncMock(return_value="success")

        result = run(
            run_with_retry(
                mock_func,
                max_retries=3,
                retry_delay=0.01,
                timeout=1.0,
                task_name="test_task",
            )
        )

        assert result is True
        assert mock_func.call_count == 1

    def test_success_after_retry(self, run):
        """Task fails once then succeeds."""
        mock_func = AsyncMock(side_effect=[ValueError("fail"), "success"])

        result = run(
            run_with_retry(
                mock_func,
                max_retries=3,
                retry_delay=0.01,
                timeout=1.0,
                task_name="test_task",
            )
        )

        assert result is True
        assert mock_func.call_count == 2

    def test_failure_after_max_retries(self, run):
        """Task fails all retries."""
        mock_func = AsyncMock(side_effect=ValueError("always fails"))

        result = run(
            run_with_retry(
                mock_func,
                max_retries=3,
                retry_delay=0.01,
                timeout=1.0,
                task_name="test_task",
            )
        )

        assert result is False
        assert mock_func.call_count == 3

    def test_timeout_triggers_retry(self, run):
        """Task timeout triggers retry."""
        call_count = 0

        async def counted_slow():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(10)

        result = run(
            run_with_retry(
                counted_slow,
                max_retries=2,
                retry_delay=0.01,
                timeout=0.05,
                task_name="test_task",
            )
        )

        assert result is False
        assert call_count == 2

    def test_exponential_backoff(self, run):
        """Verify exponential backoff delays."""
        mock_func = AsyncMock(side_effect=[ValueError("1"), ValueError("2"), "success"])
        delays = []

        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.001)

        with patch("BE.async_utils.asyncio.sleep", mock_sleep):
            result = run(
                run_with_retry(
                    mock_func,
                    max_retries=3,
                    retry_delay=0.1,
                    timeout=1.0,
                    task_name="test_task",
                )
            )

        assert result is True
        assert len(delays) == 2
        assert delays[0] == pytest.approx(0.1)
        assert delays[1] == pytest.approx(0.2)


class TestScheduleBackgroundTask:
    """Tests for schedule_background_task function."""

    def test_schedules_task_with_running_loop(self, run, event_loop):
        """Task is scheduled when event loop is running."""
        executed = asyncio.Event()

        async def set_executed():
            executed.set()

        async def test_coro():
            result = schedule_background_task(
                set_executed,
                max_retries=1,
                retry_delay=0.01,
                timeout=1.0,
                task_name="test_task",
            )
            assert result is True
            await asyncio.wait_for(executed.wait(), timeout=1.0)

        run(test_coro())

    def test_returns_false_without_running_loop(self):
        """Returns False when no event loop is running."""

        async def dummy():
            pass

        result = schedule_background_task(
            dummy,
            max_retries=1,
            retry_delay=0.01,
            timeout=1.0,
            task_name="test_task",
        )

        assert result is False

    def test_retries_on_failure(self, run):
        """Background task retries on failure."""
        call_count = 0
        completed = asyncio.Event()

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            completed.set()

        async def test_coro():
            result = schedule_background_task(
                failing_then_success,
                max_retries=3,
                retry_delay=0.01,
                timeout=1.0,
                task_name="test_task",
            )
            assert result is True
            await asyncio.wait_for(completed.wait(), timeout=1.0)

        run(test_coro())
        assert call_count == 2
