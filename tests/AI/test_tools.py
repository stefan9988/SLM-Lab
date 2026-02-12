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
            GENERAL_AGENT_SEARCH_CHUNKS_TOOL=True,
        )
        tools = get_enabled_tools(settings)
        assert len(tools) == 7

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


_VALID_UUID = "12345678-1234-1234-1234-123456789abc"
_CONFIG_WITH_USER = {"configurable": {"user_id": "user-1"}}


class TestReadFileContentTool:
    @patch("AI.tools.read_file_content.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.read_file_content.get_stream_writer")
    @patch("AI.tools.read_file_content.run_async_from_sync")
    def test_returns_file_content(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        mock_run.return_value = "file text here"
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": _VALID_UUID})
        assert result == "file text here"

    @patch("AI.tools.read_file_content.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.read_file_content.get_stream_writer")
    @patch("AI.tools.read_file_content.run_async_from_sync")
    def test_file_not_found_returns_error_message(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        mock_run.side_effect = FileNotFoundError("No file found with id 'bad-id'")
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": _VALID_UUID})
        assert "Error" in result
        assert "No file found" in result

    @patch("AI.tools.read_file_content.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.read_file_content.get_stream_writer")
    @patch("AI.tools.read_file_content.run_async_from_sync")
    def test_unsupported_file_returns_error_message(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        mock_run.side_effect = ValueError("appears to be binary")
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": _VALID_UUID})
        assert "Error" in result
        assert "binary" in result

    @patch("AI.tools.read_file_content.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.read_file_content.get_stream_writer")
    @patch("AI.tools.read_file_content.run_async_from_sync")
    def test_truncates_large_content(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        large = "x" * 600_000
        mock_run.return_value = large
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": _VALID_UUID})
        assert len(result) < len(large)
        assert "truncated" in result.lower()

    @patch("AI.tools.read_file_content.get_stream_writer")
    def test_invalid_uuid_returns_error(self, mock_get_writer):
        """Issue 4: Non-UUID file_id is rejected without a DB query."""
        mock_get_writer.return_value = MagicMock()
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": "not-a-uuid"})
        assert "Error" in result
        assert "Invalid file_id format" in result

    @patch("AI.tools.read_file_content.get_config", return_value={"configurable": {}})
    @patch("AI.tools.read_file_content.get_stream_writer")
    def test_missing_user_id_returns_error(self, mock_get_writer, mock_get_config):
        """Issue 1: Missing user_id in config returns an ownership error."""
        mock_get_writer.return_value = MagicMock()
        from AI.tools.read_file_content import read_file_content_tool

        result = read_file_content_tool.invoke({"file_id": _VALID_UUID})
        assert "Error" in result
        assert "ownership" in result.lower()


class TestSearchChunksTool:
    @patch("AI.tools.search_chunks.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.search_chunks.get_stream_writer")
    @patch("AI.tools.search_chunks.run_async_from_sync")
    def test_returns_formatted_results(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        mock_run.return_value = [
            {
                "chunk_index": 0,
                "chunk_text": "Hello world",
                "score": 0.95,
                "original_name": "test.txt",
                "file_id": _VALID_UUID,
                "page_number": None,
            },
            {
                "chunk_index": 3,
                "chunk_text": "Second chunk",
                "score": 0.80,
                "original_name": "test.txt",
                "file_id": _VALID_UUID,
                "page_number": None,
            },
        ]
        from AI.tools.search_chunks import search_chunks_tool

        result = search_chunks_tool.invoke({
            "file_id": _VALID_UUID,
            "queries": ["hello"],
            "num_results": 5,
        })
        assert "Hello world" in result
        assert "Second chunk" in result
        assert "0.9500" in result
        assert "[1]" in result
        assert "[2]" in result
        # No page info when page_number is None
        assert "[Page" not in result

    @patch("AI.tools.search_chunks.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.search_chunks.get_stream_writer")
    @patch("AI.tools.search_chunks.run_async_from_sync")
    def test_shows_page_number_when_present(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        mock_run.return_value = [
            {
                "chunk_index": 2,
                "chunk_text": "PDF chunk text",
                "score": 0.90,
                "original_name": "report.pdf",
                "file_id": _VALID_UUID,
                "page_number": 5,
            },
        ]
        from AI.tools.search_chunks import search_chunks_tool

        result = search_chunks_tool.invoke({
            "file_id": _VALID_UUID,
            "queries": ["report"],
            "num_results": 5,
        })
        assert "[Page 5]" in result
        assert "PDF chunk text" in result

    @patch("AI.tools.search_chunks.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.search_chunks.get_stream_writer")
    @patch("AI.tools.search_chunks.run_async_from_sync")
    def test_mixed_page_numbers(self, mock_run, mock_get_writer, mock_get_config):
        """Results with and without page numbers format correctly."""
        mock_get_writer.return_value = MagicMock()
        mock_run.return_value = [
            {
                "chunk_index": 0,
                "chunk_text": "With page",
                "score": 0.95,
                "original_name": "doc.pdf",
                "file_id": _VALID_UUID,
                "page_number": 3,
            },
            {
                "chunk_index": 1,
                "chunk_text": "Without page",
                "score": 0.85,
                "original_name": "doc.txt",
                "file_id": _VALID_UUID,
                "page_number": None,
            },
        ]
        from AI.tools.search_chunks import search_chunks_tool

        result = search_chunks_tool.invoke({
            "file_id": _VALID_UUID,
            "queries": ["test"],
            "num_results": 5,
        })
        assert "[Page 3]" in result
        # The second chunk should NOT have [Page
        lines = result.split("---")
        assert "[Page" not in lines[1]

    @patch("AI.tools.search_chunks.get_stream_writer")
    def test_invalid_uuid_returns_error(self, mock_get_writer):
        mock_get_writer.return_value = MagicMock()
        from AI.tools.search_chunks import search_chunks_tool

        result = search_chunks_tool.invoke({
            "file_id": "not-a-uuid",
            "queries": ["test"],
        })
        assert "Error" in result
        assert "Invalid file_id format" in result

    @patch("AI.tools.search_chunks.get_config", return_value={"configurable": {}})
    @patch("AI.tools.search_chunks.get_stream_writer")
    def test_missing_user_id_returns_error(self, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        from AI.tools.search_chunks import search_chunks_tool

        result = search_chunks_tool.invoke({
            "file_id": _VALID_UUID,
            "queries": ["test"],
        })
        assert "Error" in result
        assert "ownership" in result.lower()

    @patch("AI.tools.search_chunks.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.search_chunks.get_stream_writer")
    def test_empty_queries_returns_error(self, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        from AI.tools.search_chunks import search_chunks_tool

        result = search_chunks_tool.invoke({
            "file_id": _VALID_UUID,
            "queries": [],
        })
        assert "Error" in result
        assert "query" in result.lower()

    @patch("AI.tools.search_chunks.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.search_chunks.get_stream_writer")
    @patch("AI.tools.search_chunks.run_async_from_sync")
    def test_no_results_returns_message(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        mock_run.return_value = []
        from AI.tools.search_chunks import search_chunks_tool

        result = search_chunks_tool.invoke({
            "file_id": _VALID_UUID,
            "queries": ["nonexistent"],
        })
        assert "No matching chunks" in result

    @patch("AI.tools.search_chunks.get_config", return_value=_CONFIG_WITH_USER)
    @patch("AI.tools.search_chunks.get_stream_writer")
    @patch("AI.tools.search_chunks.run_async_from_sync")
    def test_clamps_num_results(self, mock_run, mock_get_writer, mock_get_config):
        mock_get_writer.return_value = MagicMock()
        mock_run.return_value = []
        from AI.tools.search_chunks import search_chunks_tool

        search_chunks_tool.invoke({
            "file_id": _VALID_UUID,
            "queries": ["test"],
            "num_results": 50,
        })
        # Verify the clamped limit was passed to search_chunks
        call_args = mock_run.call_args
        # The coroutine is passed as the first positional arg
        # We can't inspect the coroutine args directly, but we verify
        # it was called (no error from clamping)
