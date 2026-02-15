"""Tests for the agent registry and delegate_to_agent tool."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables.config import var_child_runnable_config

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
    @patch("AI.tools.delegate_to_agent._run_delegation", new_callable=AsyncMock)
    def test_successful_delegation(
        self, mock_delegation, mock_get_writer, mock_get_config
    ):
        mock_get_writer.return_value = MagicMock()
        mock_delegation.return_value = "delegated response"
        agent = MagicMock()
        registry.register("doc_agent", agent)

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(
                agent_name="doc_agent", prompt="Summarize the file"
            )
        )
        assert result == "delegated response"
        mock_delegation.assert_called_once()

    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_unknown_agent_returns_error(self, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        registry.register("general_agent", MagicMock())

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(agent_name="nonexistent", prompt="hello")
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

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(agent_name="doc_agent", prompt="hello")
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
        )

        # Simulate an active delegation for this user+agent
        _active_delegations.add(("user-1", "doc_agent"))
        try:
            result = asyncio.run(
                delegate_to_agent_tool.coroutine(agent_name="doc_agent", prompt="hello")
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

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(agent_name="doc_agent", prompt="hello")
        )
        assert "Error" in result
        assert "failed" in result.lower()
        assert "LLM timeout" in result

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_stream_context_isolated_during_delegation(
        self, mock_get_writer, mock_get_config
    ):
        """The parent's stream writer context must be reset to None while the
        delegated agent runs, so the delegated agent's tools don't write
        into the parent stream."""
        mock_get_writer.return_value = MagicMock()

        config_value_during_invoke = []

        async def capturing_invoke(prompt, *, session_id, user_id):
            """Record var_child_runnable_config value at invocation time."""
            config_value_during_invoke.append(var_child_runnable_config.get(None))
            return "ok"

        agent = MagicMock()
        agent.invoke = capturing_invoke
        registry.register("doc_agent", agent)

        # Pre-set a non-None value to simulate the parent's stream context.
        sentinel = {"fake": "config"}
        parent_token = var_child_runnable_config.set(sentinel)
        try:
            from AI.tools.delegate_to_agent import delegate_to_agent_tool

            result = asyncio.run(
                delegate_to_agent_tool.coroutine(agent_name="doc_agent", prompt="hello")
            )

            assert result == "ok"
            # During agent.invoke, the config must have been None.
            assert len(config_value_during_invoke) == 1
            assert config_value_during_invoke[0] is None

            # After delegation, the parent config must be restored.
            assert var_child_runnable_config.get(None) is sentinel
        finally:
            var_child_runnable_config.reset(parent_token)
