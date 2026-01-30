"""Tests for AI.tools module."""

import re
from unittest.mock import MagicMock, patch


class TestGetCurrentDateAndTime:
    @patch("AI.tools.get_current_date_and_time.get_stream_writer")
    def test_returns_formatted_datetime(self, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        from AI.tools.get_current_date_and_time import get_current_date_and_time

        result = get_current_date_and_time.invoke({})
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)


class TestBraveSearchTool:
    @patch("AI.tools.brave_search.get_stream_writer")
    @patch("AI.tools.brave_search._brave")
    def test_passthrough(self, mock_brave, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        mock_brave.invoke.return_value = "search results"
        from AI.tools.brave_search import brave_search_tool

        result = brave_search_tool.invoke({"query": "test"})
        assert result == "search results"
        mock_brave.invoke.assert_called_once_with("test")


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
