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
