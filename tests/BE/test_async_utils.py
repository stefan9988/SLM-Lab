"""Tests for BE.async_utils module."""

import asyncio
import threading
from unittest.mock import AsyncMock, patch

import pytest

import BE.async_utils as async_utils_module
from BE.async_utils import init_loop, run_with_retry, schedule_background_task


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


class TestInitLoop:
    """Tests for init_loop and cross-thread scheduling."""

    def setup_method(self):
        """Reset _main_loop before each test."""
        async_utils_module._main_loop = None

    def teardown_method(self):
        """Reset _main_loop after each test."""
        async_utils_module._main_loop = None

    def test_init_loop_captures_running_loop(self):
        """init_loop stores the current event loop."""
        assert async_utils_module._main_loop is None

        async def _init():
            init_loop()

        asyncio.run(_init())
        assert async_utils_module._main_loop is not None

    def test_schedule_from_worker_thread_via_init_loop(self):
        """schedule_background_task works from a non-event-loop thread
        when init_loop has been called."""
        executed = threading.Event()
        loop = asyncio.new_event_loop()

        async def _init_and_wait():
            init_loop()
            # Spawn a worker thread that schedules a background task
            thread_result = {}

            def worker():
                async def set_flag():
                    executed.set()

                thread_result["scheduled"] = schedule_background_task(
                    set_flag,
                    max_retries=1,
                    retry_delay=0.01,
                    timeout=1.0,
                    task_name="cross_thread_test",
                )

            t = threading.Thread(target=worker)
            t.start()
            t.join(timeout=2.0)

            assert thread_result["scheduled"] is True
            # Give the scheduled coroutine time to execute
            await asyncio.sleep(0.1)

        loop.run_until_complete(_init_and_wait())
        loop.close()
        assert executed.is_set()

    def test_schedule_fails_without_init_loop_and_no_event_loop(self):
        """Without init_loop, scheduling from a plain thread returns False."""
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
