"""Tests for the validation agent: tool selection, registration, caller restriction,
and agent_name propagation through LangGraph config."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from AI.agents import registry
from AI.tools import VALIDATION_AGENT_TOOLS, get_validation_agent_enabled_tools

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides):
    """Return a mock settings object with all validation tool flags set to False,
    then apply any provided overrides."""
    settings = MagicMock()
    for setting_name, _ in VALIDATION_AGENT_TOOLS:
        setattr(settings, setting_name, False)
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


# ---------------------------------------------------------------------------
# TestGetValidationAgentEnabledTools
# ---------------------------------------------------------------------------


class TestGetValidationAgentEnabledTools:
    def test_no_tools_enabled(self):
        settings = _make_settings()
        tools = get_validation_agent_enabled_tools(settings)
        assert tools == []

    def test_all_tools_enabled(self):
        settings = _make_settings(**{name: True for name, _ in VALIDATION_AGENT_TOOLS})
        tools = get_validation_agent_enabled_tools(settings)
        assert len(tools) == len(VALIDATION_AGENT_TOOLS)

    def test_single_tool_enabled(self):
        settings = _make_settings(VALIDATION_AGENT_BRAVE_SEARCH_TOOL=True)
        tools = get_validation_agent_enabled_tools(settings)
        assert len(tools) == 1

    def test_returns_correct_tool_instances(self):
        settings = _make_settings(
            VALIDATION_AGENT_DATE_TIME_TOOL=True,
            VALIDATION_AGENT_WEB_PAGE_CONTENT_TOOL=True,
        )
        tools = get_validation_agent_enabled_tools(settings)
        assert len(tools) == 2
        expected = [
            tool
            for name, tool in VALIDATION_AGENT_TOOLS
            if name
            in (
                "VALIDATION_AGENT_DATE_TIME_TOOL",
                "VALIDATION_AGENT_WEB_PAGE_CONTENT_TOOL",
            )
        ]
        assert tools == expected


# ---------------------------------------------------------------------------
# TestValidationAgentRegistration
# ---------------------------------------------------------------------------


class TestValidationAgentRegistration:
    def setup_method(self):
        registry.clear()

    def teardown_method(self):
        registry.clear()

    def test_register_with_allowed_callers(self):
        agent = MagicMock()
        registry.register("validation_agent", agent, allowed_callers={"general_agent"})
        assert registry.get("validation_agent") is agent
        assert registry.get_allowed_callers("validation_agent") == {"general_agent"}

    def test_unrestricted_agent_returns_none_for_allowed_callers(self):
        agent = MagicMock()
        registry.register("general_agent", agent)
        assert registry.get_allowed_callers("general_agent") is None

    def test_clear_also_clears_allowed_callers(self):
        agent = MagicMock()
        registry.register("validation_agent", agent, allowed_callers={"general_agent"})
        registry.clear()
        assert registry.get("validation_agent") is None
        assert registry.get_allowed_callers("validation_agent") is None


# ---------------------------------------------------------------------------
# TestCallerRestriction
# ---------------------------------------------------------------------------

_CONFIG_GENERAL = {"configurable": {"user_id": "user-1", "agent_name": "general_agent"}}
_CONFIG_DOCUMENT = {
    "configurable": {"user_id": "user-1", "agent_name": "document_agent"}
}
_CONFIG_UNKNOWN = {"configurable": {"user_id": "user-1", "agent_name": ""}}


class TestCallerRestriction:
    def setup_method(self):
        registry.clear()

    def teardown_method(self):
        registry.clear()

    def _register_validation_agent(self):
        agent = AsyncMock()
        agent.invoke = AsyncMock(return_value="verified")
        registry.register("validation_agent", agent, allowed_callers={"general_agent"})
        return agent

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_DOCUMENT)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_disallowed_caller_receives_error(self, mock_writer, mock_get_config):
        mock_writer.return_value = MagicMock()
        self._register_validation_agent()

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(
                agent_name="validation_agent", prompt="Is the sky blue?"
            )
        )
        assert "Error" in result
        assert "general_agent" in result
        assert "document_agent" in result

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_GENERAL)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    @patch("AI.tools.delegate_to_agent._run_delegation", new_callable=AsyncMock)
    def test_allowed_caller_succeeds(
        self, mock_delegation, mock_writer, mock_get_config
    ):
        mock_writer.return_value = MagicMock()
        mock_delegation.return_value = "verified"
        self._register_validation_agent()

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(
                agent_name="validation_agent", prompt="Is the sky blue?"
            )
        )
        assert result == "verified"

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_UNKNOWN)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_empty_caller_name_is_disallowed(self, mock_writer, mock_get_config):
        mock_writer.return_value = MagicMock()
        self._register_validation_agent()

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(
                agent_name="validation_agent", prompt="Is the sky blue?"
            )
        )
        assert "Error" in result

    @patch("AI.tools.delegate_to_agent.get_config", return_value=_CONFIG_GENERAL)
    @patch("AI.tools.delegate_to_agent.get_stream_writer")
    def test_unrestricted_agent_is_callable_by_anyone(
        self, mock_writer, mock_get_config
    ):
        mock_writer.return_value = MagicMock()
        other_agent = AsyncMock()
        other_agent.invoke = AsyncMock(return_value="open result")
        registry.register("open_agent", other_agent)  # no allowed_callers

        from AI.tools.delegate_to_agent import delegate_to_agent_tool

        result = asyncio.run(
            delegate_to_agent_tool.coroutine(agent_name="open_agent", prompt="hello")
        )
        # Should not receive a restriction error (may succeed or hit other errors)
        assert "can only be called by" not in result


# ---------------------------------------------------------------------------
# TestAgentNameInConfig
# ---------------------------------------------------------------------------


class TestAgentNameInConfig:
    @patch("AI.agents.base.create_agent")
    def test_agent_name_in_invoke_config(self, mock_create_agent):
        from AI.agents.base import Agent

        captured_config = []

        mock_graph = MagicMock()

        async def fake_ainvoke(inputs, config=None):
            captured_config.append(config)
            return {"messages": [MagicMock(content="response")]}

        mock_graph.ainvoke = fake_ainvoke
        mock_create_agent.return_value = mock_graph

        llm = MagicMock()
        llm.__class__.__name__ = "MockLLM"
        agent = Agent(llm=llm, tools=[], agent_name="general_agent")

        asyncio.run(agent.invoke("hello", "session-1", user_id="user-1"))

        assert len(captured_config) == 1
        assert captured_config[0]["configurable"]["agent_name"] == "general_agent"

    @patch("AI.agents.base.create_agent")
    def test_agent_name_in_stream_config(self, mock_create_agent):
        from AI.agents.base import Agent

        captured_config = []

        async def fake_astream(inputs, config=None, stream_mode=None):
            captured_config.append(config)
            return
            yield  # make it an async generator

        mock_graph = MagicMock()
        mock_graph.astream = fake_astream
        mock_create_agent.return_value = mock_graph

        llm = MagicMock()
        llm.__class__.__name__ = "MockLLM"
        agent = Agent(llm=llm, tools=[], agent_name="validation_agent")

        async def collect():
            async for _ in agent.stream("hello", "session-1", user_id="user-1"):
                pass

        asyncio.run(collect())

        assert len(captured_config) == 1
        assert captured_config[0]["configurable"]["agent_name"] == "validation_agent"

    @patch("AI.agents.base.create_agent")
    def test_no_agent_name_config_is_none_when_no_user(self, mock_create_agent):
        """When neither user_id nor agent_name are set, config should be None."""
        from AI.agents.base import Agent

        captured_config = []

        mock_graph = MagicMock()

        async def fake_ainvoke(inputs, config=None):
            captured_config.append(config)
            return {"messages": [MagicMock(content="response")]}

        mock_graph.ainvoke = fake_ainvoke
        mock_create_agent.return_value = mock_graph

        llm = MagicMock()
        llm.__class__.__name__ = "MockLLM"
        agent = Agent(llm=llm, tools=[])  # no agent_name

        asyncio.run(agent.invoke("hello", "session-1", user_id=""))

        assert captured_config[0] is None
