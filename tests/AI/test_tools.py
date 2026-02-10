"""Tests for AI.tools module."""

import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from AI.tools import get_enabled_tools, GENERAL_AGENT_TOOLS


class TestGetEnabledTools:
    def test_all_enabled_by_default(self):
        settings = SimpleNamespace(
            GENERAL_AGENT_DATE_TIME_TOOL=True,
            GENERAL_AGENT_BRAVE_SEARCH_TOOL=True,
            GENERAL_AGENT_PYTHON_REPL_TOOL=True,
            GENERAL_AGENT_OLLAMA_WEB_SEARCH_TOOL=True,
            GENERAL_AGENT_OLLAMA_WEB_FETCH_TOOL=True,
            GENERAL_AGENT_READ_FILE_CONTENT_TOOL=True,
        )
        tools = get_enabled_tools(settings)
        assert len(tools) == 6

    def test_disable_one_tool(self):
        settings = SimpleNamespace(
            GENERAL_AGENT_DATE_TIME_TOOL=True,
            GENERAL_AGENT_BRAVE_SEARCH_TOOL=True,
            GENERAL_AGENT_PYTHON_REPL_TOOL=False,
            GENERAL_AGENT_OLLAMA_WEB_SEARCH_TOOL=True,
            GENERAL_AGENT_OLLAMA_WEB_FETCH_TOOL=True,
        )
        tools = get_enabled_tools(settings)
        assert len(tools) == 4
        tool_entries = dict(GENERAL_AGENT_TOOLS)
        from AI.tools.python_repl import python_repl_tool

        assert python_repl_tool not in tools

    def test_all_disabled(self):
        settings = SimpleNamespace(
            GENERAL_AGENT_DATE_TIME_TOOL=False,
            GENERAL_AGENT_BRAVE_SEARCH_TOOL=False,
            GENERAL_AGENT_PYTHON_REPL_TOOL=False,
            GENERAL_AGENT_OLLAMA_WEB_SEARCH_TOOL=False,
            GENERAL_AGENT_OLLAMA_WEB_FETCH_TOOL=False,
        )
        tools = get_enabled_tools(settings)
        assert len(tools) == 0

    def test_missing_setting_defaults_to_disabled(self):
        settings = SimpleNamespace()
        tools = get_enabled_tools(settings)
        assert len(tools) == 0


class TestGetCurrentDateAndTime:
    @patch("AI.tools.get_current_date_and_time.get_stream_writer")
    def test_returns_formatted_datetime(self, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        from AI.tools.get_current_date_and_time import get_current_date_and_time

        result = get_current_date_and_time.invoke({})
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)


class TestBraveSearchTool:
    @patch("AI.tools.brave_search.get_stream_writer")
    @patch("AI.tools.brave_search._get_brave")
    def test_passthrough(self, mock_get_brave, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_brave_instance = MagicMock()
        mock_brave_instance.invoke.return_value = "search results"
        mock_get_brave.return_value = mock_brave_instance
        from AI.tools.brave_search import brave_search_tool

        result = brave_search_tool.invoke({"query": "test"})
        assert result == "search results"
        mock_get_brave.assert_called_once_with(3)
        mock_brave_instance.invoke.assert_called_once_with("test")


class TestPythonReplTool:
    @patch("AI.tools.python_repl.get_stream_writer")
    @patch("AI.tools.python_repl._repl")
    def test_passthrough(self, mock_repl, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_repl.run.return_value = "42"
        from AI.tools.python_repl import python_repl_tool

        result = python_repl_tool.invoke({"code": "print(42)"})
        assert result == "42"
        mock_repl.run.assert_called_once_with("print(42)")


class TestOllamaWebSearchTool:
    @patch("AI.tools.ollama_web.get_stream_writer")
    @patch("AI.tools.ollama_web._get_client")
    def test_returns_search_results(self, mock_get_client, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_client = MagicMock()
        mock_client.web_search.return_value = {"results": ["r1"]}
        mock_get_client.return_value = mock_client
        from AI.tools.ollama_web import ollama_web_search_tool

        result = ollama_web_search_tool.invoke({"query": "test query"})
        assert result == "{'results': ['r1']}"
        mock_client.web_search.assert_called_once_with("test query")

    @patch("AI.tools.ollama_web.get_stream_writer")
    @patch("AI.tools.ollama_web._get_client")
    def test_raises_on_error(self, mock_get_client, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_client = MagicMock()
        mock_client.web_search.side_effect = RuntimeError("fail")
        mock_get_client.return_value = mock_client
        from AI.tools.ollama_web import ollama_web_search_tool

        import pytest

        with pytest.raises(RuntimeError, match="fail"):
            ollama_web_search_tool.invoke({"query": "bad"})


class TestOllamaWebFetchTool:
    @patch("AI.tools.ollama_web.get_stream_writer")
    @patch("AI.tools.ollama_web._get_client")
    def test_returns_fetched_content(self, mock_get_client, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_client = MagicMock()
        mock_client.web_fetch.return_value = {"content": "page html"}
        mock_get_client.return_value = mock_client
        from AI.tools.ollama_web import ollama_web_fetch_tool

        result = ollama_web_fetch_tool.invoke({"url": "https://example.com"})
        assert result == "{'content': 'page html'}"
        mock_client.web_fetch.assert_called_once_with("https://example.com")

    @patch("AI.tools.ollama_web.get_stream_writer")
    @patch("AI.tools.ollama_web._get_client")
    def test_raises_on_error(self, mock_get_client, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_client = MagicMock()
        mock_client.web_fetch.side_effect = ConnectionError("timeout")
        mock_get_client.return_value = mock_client
        from AI.tools.ollama_web import ollama_web_fetch_tool

        import pytest

        with pytest.raises(ConnectionError, match="timeout"):
            ollama_web_fetch_tool.invoke({"url": "https://bad.com"})


class TestReadFileContentTool:
    @patch("AI.tools.read_file_content.get_stream_writer")
    @patch("AI.tools.read_file_content.run_async_from_sync")
    def test_returns_file_content(self, mock_run, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_run.return_value = "file text here"
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": "abc-123"})
        assert result == "file text here"

    @patch("AI.tools.read_file_content.get_stream_writer")
    @patch("AI.tools.read_file_content.run_async_from_sync")
    def test_file_not_found_returns_error_message(self, mock_run, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_run.side_effect = FileNotFoundError("No file found with id 'bad-id'")
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": "bad-id"})
        assert "Error" in result
        assert "No file found" in result

    @patch("AI.tools.read_file_content.get_stream_writer")
    @patch("AI.tools.read_file_content.run_async_from_sync")
    def test_unsupported_file_returns_error_message(self, mock_run, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_run.side_effect = ValueError("appears to be binary")
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": "bin-id"})
        assert "Error" in result
        assert "binary" in result

    @patch("AI.tools.read_file_content.get_stream_writer")
    @patch("AI.tools.read_file_content.run_async_from_sync")
    def test_truncates_large_content(self, mock_run, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        large = "x" * 600_000
        mock_run.return_value = large
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": "big-id"})
        assert len(result) < len(large)
        assert "truncated" in result.lower()
