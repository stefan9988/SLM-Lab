"""Tests for document agent tool selection and initialization."""

from unittest.mock import MagicMock, patch

import pytest

from AI.tools import get_document_agent_enabled_tools, DOCUMENT_AGENT_TOOLS
from AI.agents.initialize_agent import init_agent
from AI.prompts.document_agent_prompt import DOCUMENT_AGENT_PROMPT


class TestGetDocumentAgentEnabledTools:
    def test_no_tools_enabled(self):
        settings = MagicMock()
        for setting_name, _ in DOCUMENT_AGENT_TOOLS:
            setattr(settings, setting_name, False)

        tools = get_document_agent_enabled_tools(settings)
        assert tools == []

    def test_all_tools_enabled(self):
        settings = MagicMock()
        for setting_name, _ in DOCUMENT_AGENT_TOOLS:
            setattr(settings, setting_name, True)

        tools = get_document_agent_enabled_tools(settings)
        assert len(tools) == len(DOCUMENT_AGENT_TOOLS)

    def test_single_tool_enabled(self):
        settings = MagicMock()
        for setting_name, _ in DOCUMENT_AGENT_TOOLS:
            setattr(settings, setting_name, False)
        settings.DOCUMENT_AGENT_SEARCH_CHUNKS_TOOL = True

        tools = get_document_agent_enabled_tools(settings)
        assert len(tools) == 1

    def test_returns_correct_tool_instances(self):
        settings = MagicMock()
        for setting_name, _ in DOCUMENT_AGENT_TOOLS:
            setattr(settings, setting_name, False)
        settings.DOCUMENT_AGENT_DATE_TIME_TOOL = True
        settings.DOCUMENT_AGENT_READ_FILE_CONTENT_TOOL = True

        tools = get_document_agent_enabled_tools(settings)
        assert len(tools) == 2
        expected = [
            tool for name, tool in DOCUMENT_AGENT_TOOLS
            if name in ("DOCUMENT_AGENT_DATE_TIME_TOOL", "DOCUMENT_AGENT_READ_FILE_CONTENT_TOOL")
        ]
        assert tools == expected


class TestDocumentAgentInit:
    @patch("AI.agents.initialize_agent._build_llm")
    @patch("AI.agents.base.create_agent")
    def test_initializes_with_document_prompt(self, mock_create, mock_build_llm):
        mock_build_llm.return_value = MagicMock()
        mock_create.return_value = MagicMock()

        agent = init_agent(
            system_prompt=DOCUMENT_AGENT_PROMPT,
            tools=[],
            maintain_history=True,
        )
        from AI.agents.base import Agent

        assert isinstance(agent, Agent)

    @patch("AI.agents.initialize_agent._build_llm")
    @patch("AI.agents.base.create_agent")
    def test_initializes_with_tools(self, mock_create, mock_build_llm):
        mock_build_llm.return_value = MagicMock()
        mock_create.return_value = MagicMock()
        mock_tool = MagicMock()

        agent = init_agent(
            system_prompt=DOCUMENT_AGENT_PROMPT,
            tools=[mock_tool],
            maintain_history=True,
        )
        from AI.agents.base import Agent

        assert isinstance(agent, Agent)

    @patch("AI.agents.initialize_agent._build_llm")
    def test_propagates_exceptions(self, mock_build_llm):
        mock_build_llm.side_effect = ValueError("bad")
        with pytest.raises(ValueError):
            init_agent(system_prompt=DOCUMENT_AGENT_PROMPT)
