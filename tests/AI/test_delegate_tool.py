"""Tests for the agent registry and delegate_to_agent tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from AI.agents import registry


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    def setup_method(self):
        registry.clear()

    def teardown_method(self):
        registry.clear()

    def test_register_and_get(self):
        agent = MagicMock()
        registry.register("my_agent", agent)
        assert registry.get("my_agent") is agent

    def test_get_nonexistent_returns_none(self):
        assert registry.get("no_such_agent") is None

    def test_list_agents(self):
        registry.register("a", MagicMock())
        registry.register("b", MagicMock())
        assert sorted(registry.list_agents()) == ["a", "b"]

    def test_clear(self):
        registry.register("agent", MagicMock())
        registry.clear()
        assert registry.list_agents() == []
        assert registry.get("agent") is None


# ---------------------------------------------------------------------------
# Delegate tool tests
# ---------------------------------------------------------------------------

_CONFIG_WITH_USER = {"configurable": {"user_id": "user-1"}}


class TestDelegateToAgentTool:
    def setup_method(self):
        registry.clear()

    def teardown_method(self):
        registry.clear()

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    @patch("AI.tools.delegate_to_agent.run_async_from_sync")
    def test_successful_delegation(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        mock_run.return_value = "delegated response"
        agent = MagicMock()
        registry.register("doc_agent", agent)

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = delegate_to_agent_tool.invoke(
            {"agent_name": "doc_agent", "prompt": "Summarize the file"}
        )
        assert result == "delegated response"
        mock_run.assert_called_once()

    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_unknown_agent_returns_error(self, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        registry.register("general_agent", MagicMock())

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = delegate_to_agent_tool.invoke(
            {"agent_name": "nonexistent", "prompt": "hello"}
        )
        assert "Error" in result
        assert "Unknown agent" in result
        assert "general_agent" in result

    @patch(
        "AI.tools.delegate_to_agent.get_config",
        return_value={"configurable": {}},
    )
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_missing_user_id_returns_error(self, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        registry.register("doc_agent", MagicMock())

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = delegate_to_agent_tool.invoke(
            {"agent_name": "doc_agent", "prompt": "hello"}
        )
        assert "Error" in result
        assert "user identity" in result.lower()

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_circular_delegation_returns_error(self, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        agent = MagicMock()
        registry.register("doc_agent", agent)

        from AI.tools.delegate_to_agent import (
            _active_delegations,
            delegate_to_agent_tool,
            run_async_from_sync,
        )

        # Simulate an active delegation for this user+agent
        _active_delegations.add(("user-1", "doc_agent"))
        try:
            # run_async_from_sync will execute _run_delegation which checks the set
            # We need to let the real _run_delegation run to test the guard
            with patch(
                "AI.tools.delegate_to_agent.run_async_from_sync",
                side_effect=lambda coro: _run_sync(coro),
            ):
                result = delegate_to_agent_tool.invoke(
                    {"agent_name": "doc_agent", "prompt": "hello"}
                )
            assert "Error" in result
            assert "Circular delegation" in result
        finally:
            _active_delegations.discard(("user-1", "doc_agent"))

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_agent_invoke_failure_returns_error(self, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        agent = AsyncMock()
        agent.invoke.side_effect = RuntimeError("LLM timeout")
        registry.register("doc_agent", agent)

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        with patch(
            "AI.tools.delegate_to_agent.run_async_from_sync",
            side_effect=lambda coro: _run_sync(coro),
        ):
            result = delegate_to_agent_tool.invoke(
                {"agent_name": "doc_agent", "prompt": "hello"}
            )
        assert "Error" in result
        assert "failed" in result.lower()
        assert "LLM timeout" in result


# ---------------------------------------------------------------------------
# Helper to run a coroutine synchronously in tests
# ---------------------------------------------------------------------------

import asyncio


def _run_sync(coro):
    """Run a coroutine to completion, creating a loop if necessary."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
