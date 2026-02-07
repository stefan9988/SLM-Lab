"""Tests for AI.agents.base.Agent class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from AI.agents.base import Agent
from BE.session_store import InMemoryStore


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def run(event_loop):
    return event_loop.run_until_complete


@pytest.fixture
def mock_graph():
    return MagicMock()


@pytest.fixture
def agent_no_history(mock_graph):
    with patch("AI.agents.base.create_agent", return_value=mock_graph):
        llm = MagicMock()
        llm.__class__.__name__ = "MockLLM"
        return Agent(llm=llm, tools=[], maintain_history=False)


@pytest.fixture
def agent_with_history(mock_graph):
    with patch("AI.agents.base.create_agent", return_value=mock_graph):
        llm = MagicMock()
        llm.__class__.__name__ = "MockLLM"
        return Agent(llm=llm, tools=[], maintain_history=True)


class TestGetInputMessages:
    def test_no_history_returns_single_human_message(self, run, agent_no_history):
        msgs = run(agent_no_history._get_input_messages("hello", "s1", user_id="u1"))
        assert len(msgs) == 1
        assert isinstance(msgs[0], HumanMessage)
        assert msgs[0].content == "hello"

    def test_with_history_includes_prior_messages(self, run, agent_with_history):
        prior = [HumanMessage(content="a"), AIMessage(content="b")]
        run(agent_with_history._store.save_messages("s1", prior, user_id="u1"))
        msgs = run(agent_with_history._get_input_messages("c", "s1", user_id="u1"))
        assert len(msgs) == 3
        assert msgs[-1].content == "c"


class TestInvoke:
    def test_returns_content(self, run, agent_no_history, mock_graph):
        mock_graph.invoke.return_value = {"messages": [AIMessage(content="response")]}
        result = run(agent_no_history.invoke("hi", "s1", user_id="u1"))
        assert result == "response"

    def test_history_maintained_across_calls(self, run, agent_with_history, mock_graph):
        mock_graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="hi"),
                AIMessage(content="hello"),
            ]
        }
        run(agent_with_history.invoke("hi", "s1", user_id="u1"))

        # Second call should include history
        run(agent_with_history.invoke("follow up", "s1", user_id="u1"))
        second_call_msgs = mock_graph.invoke.call_args[0][0]["messages"]
        assert len(second_call_msgs) == 3  # 2 history + 1 new


class TestStream:
    def test_ai_chunk_with_content_yields_token(self, run, agent_no_history, mock_graph):
        chunk = AIMessageChunk(content="hi")
        mock_graph.stream.return_value = iter(
            [
                ("messages", (chunk, {})),
            ]
        )

        async def collect():
            return [event async for event in agent_no_history.stream("hi", "s1", user_id="u1")]

        events = run(collect())
        assert events == [{"type": "token", "content": "hi"}]

    def test_ai_chunk_with_tool_call_yields_status(self, run, agent_no_history, mock_graph):
        chunk = AIMessageChunk(
            content="",
            tool_call_chunks=[{"name": "mytool", "args": "", "id": "1", "index": 0}],
        )
        mock_graph.stream.return_value = iter(
            [
                ("messages", (chunk, {})),
            ]
        )

        async def collect():
            return [event async for event in agent_no_history.stream("hi", "s1", user_id="u1")]

        events = run(collect())
        assert len(events) == 1
        assert events[0]["type"] == "status"
        assert "mytool" in events[0]["content"]

    def test_tool_message_yields_status(self, run, agent_no_history, mock_graph):
        chunk = ToolMessage(content="result", tool_call_id="1")
        mock_graph.stream.return_value = iter(
            [
                ("messages", (chunk, {})),
            ]
        )

        async def collect():
            return [event async for event in agent_no_history.stream("hi", "s1", user_id="u1")]

        events = run(collect())
        assert events == [{"type": "status", "content": "Tool returned result"}]

    def test_custom_stream_mode_yields_status(self, run, agent_no_history, mock_graph):
        mock_graph.stream.return_value = iter(
            [
                ("custom", "Processing..."),
            ]
        )

        async def collect():
            return [event async for event in agent_no_history.stream("hi", "s1", user_id="u1")]

        events = run(collect())
        assert events == [{"type": "status", "content": "Processing..."}]


class TestHistory:
    def test_unknown_session_returns_empty(self, run, agent_no_history):
        assert run(agent_no_history.get_history("unknown", user_id="u1")) == []

    def test_after_invoke_returns_messages(self, run, agent_with_history, mock_graph):
        mock_graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="hi"),
                AIMessage(content="hello"),
            ]
        }
        run(agent_with_history.invoke("hi", "s1", user_id="u1"))
        history = run(agent_with_history.get_history("s1", user_id="u1"))
        assert len(history) == 2
        assert history[0]["role"] == "human"
        assert history[1]["role"] == "ai"

    def test_clear_then_empty(self, run, agent_with_history, mock_graph):
        mock_graph.invoke.return_value = {
            "messages": [HumanMessage(content="hi"), AIMessage(content="hello")]
        }
        run(agent_with_history.invoke("hi", "s1", user_id="u1"))
        run(agent_with_history.clear_history("s1", user_id="u1"))
        assert run(agent_with_history.get_history("s1", user_id="u1")) == []
