"""Tests for document agent caller restriction via the delegation tool."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from AI.agents import registry

# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

_CONFIG_GENERAL = {"configurable": {"user_id": "user-1", "agent_name": "general_agent"}}
_CONFIG_OTHER = {"configurable": {"user_id": "user-1", "agent_name": "other_agent"}}
_CONFIG_EMPTY = {"configurable": {"user_id": "user-1", "agent_name": ""}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_document_agent():
    agent = AsyncMock()
    agent.invoke = AsyncMock(return_value="extracted data")
    registry.register("document_agent", agent, allowed_callers={"general_agent"})
    return agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDocumentAgentDelegation:
    def setup_method(self):
        registry.clear()

    def teardown_method(self):
        registry.clear()

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_GENERAL)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    @patch("AI.tools.delegate_to_agent._run_delegation", new_callable=AsyncMock)
    def test_document_agent_allowed_by_general_agent(
        self, mock_delegation, mock_writer, mock_get_config
    ):
        mock_writer.return_value = MagicMock()
        mock_delegation.return_value = "extracted data"
        _register_document_agent()

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(
                agent_name="document_agent", prompt="Extract the invoice date."
            )
        )
        assert result == "extracted data"

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_OTHER)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_document_agent_blocked_for_unknown_caller(
        self, mock_writer, mock_get_config
    ):
        mock_writer.return_value = MagicMock()
        _register_document_agent()

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(
                agent_name="document_agent", prompt="Extract the invoice date."
            )
        )
        assert "Error" in result
        assert "general_agent" in result
        assert "other_agent" in result

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_EMPTY)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_document_agent_blocked_for_empty_caller(
        self, mock_writer, mock_get_config
    ):
        mock_writer.return_value = MagicMock()
        _register_document_agent()

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(
                agent_name="document_agent", prompt="Extract the invoice date."
            )
        )
        assert "Error" in result
