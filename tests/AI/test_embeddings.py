"""Tests for AI.embeddings module."""

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest

from AI.embeddings import (
    ChunkEmbedding,
    EmbeddingResult,
    _get_async_client,
    chunk_text,
    chunk_text_with_pages,
    generate_embeddings,
    generate_embeddings_with_pages,
)


@dataclass
class _MockEmbedResponse:
    embeddings: list[list[float]]


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def run(event_loop):
    """Helper to run coroutines in the test event loop."""
    return event_loop.run_until_complete


class TestChunkText:
    def test_uses_config_defaults(self):
        text = "word " * 500  # ~2500 chars
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            chunks = chunk_text(text)
        assert len(chunks) > 1

    def test_parameter_overrides(self):
        text = "word " * 200  # ~1000 chars
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            chunks_default = chunk_text(text)
            chunks_small = chunk_text(text, chunk_size=100, chunk_overlap=10)
        assert len(chunks_small) > len(chunks_default)

    def test_single_chunk_for_short_text(self):
        text = "Hello world"
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_empty_text_returns_empty_list(self):
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            chunks = chunk_text("")
        assert chunks == []

    def test_overlap_produces_shared_content(self):
        text = "A " * 600  # ~1200 chars, should produce 2+ chunks with overlap
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.EMBEDDING_CHUNK_SIZE = 500
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 100
            chunks = chunk_text(text)
        assert len(chunks) >= 2


class TestGenerateEmbeddings:
    def test_result_structure(self, run):
        mock_response = _MockEmbedResponse(
            embeddings=[[0.1, 0.2, 0.3]]
        )
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(return_value=mock_response)

        with (
            patch("AI.embeddings._get_async_client", return_value=mock_client),
            patch("AI.embeddings.settings") as mock_settings,
        ):
            mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            result = run(generate_embeddings("Hello world"))

        assert isinstance(result, EmbeddingResult)
        assert len(result.chunks) == 1
        assert isinstance(result.chunks[0], ChunkEmbedding)
        assert result.chunks[0].index == 0
        assert result.chunks[0].text == "Hello world"
        assert result.chunks[0].embedding == [0.1, 0.2, 0.3]
        assert result.model == "nomic-embed-text"

    def test_multi_chunk_batching(self, run):
        text = "word " * 500
        mock_response = _MockEmbedResponse(
            embeddings=[[0.1, 0.2]] * 3
        )
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(return_value=mock_response)

        with (
            patch("AI.embeddings._get_async_client", return_value=mock_client),
            patch("AI.embeddings.chunk_text", return_value=["chunk1", "chunk2", "chunk3"]),
            patch("AI.embeddings.settings") as mock_settings,
        ):
            mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
            result = run(generate_embeddings(text))

        assert len(result.chunks) == 3
        mock_client.embed.assert_called_once_with(
            model="nomic-embed-text", input=["chunk1", "chunk2", "chunk3"]
        )

    def test_empty_text_raises_value_error(self, run):
        with pytest.raises(ValueError, match="empty text"):
            run(generate_embeddings(""))

    def test_whitespace_only_raises_value_error(self, run):
        with pytest.raises(ValueError, match="empty text"):
            run(generate_embeddings("   \n\t  "))

    def test_model_override(self, run):
        mock_response = _MockEmbedResponse(embeddings=[[0.1]])
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(return_value=mock_response)

        with (
            patch("AI.embeddings._get_async_client", return_value=mock_client),
            patch("AI.embeddings.settings") as mock_settings,
        ):
            mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            result = run(generate_embeddings("Hello", model="custom-model"))

        assert result.model == "custom-model"
        mock_client.embed.assert_called_once_with(
            model="custom-model", input=["Hello"]
        )

    def test_connection_error_propagates(self, run):
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(side_effect=ConnectionError("Ollama unreachable"))

        with (
            patch("AI.embeddings._get_async_client", return_value=mock_client),
            patch("AI.embeddings.settings") as mock_settings,
        ):
            mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            with pytest.raises(ConnectionError, match="Ollama unreachable"):
                run(generate_embeddings("Hello world"))


class TestGetAsyncClient:
    def test_client_created_with_api_key(self):
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_API_KEY = "test-key"
            client = _get_async_client()
        assert client is not None

    def test_client_created_without_api_key(self):
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_API_KEY = ""
            client = _get_async_client()
        assert client is not None

    def test_client_with_api_key_has_auth_header(self):
        with (
            patch("AI.embeddings.settings") as mock_settings,
            patch("AI.embeddings.AsyncClient") as MockAsyncClient,
        ):
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_API_KEY = "test-key"
            _get_async_client()
        MockAsyncClient.assert_called_once_with(
            host="http://localhost:11434",
            headers={"authorization": "Bearer test-key"},
        )

    def test_client_without_api_key_has_no_auth_header(self):
        with (
            patch("AI.embeddings.settings") as mock_settings,
            patch("AI.embeddings.AsyncClient") as MockAsyncClient,
        ):
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_API_KEY = ""
            _get_async_client()
        MockAsyncClient.assert_called_once_with(
            host="http://localhost:11434",
            headers={},
        )


class TestChunkEmbeddingPageNumber:
    def test_defaults_to_none(self):
        chunk = ChunkEmbedding(index=0, text="hello", embedding=[0.1])
        assert chunk.page_number is None

    def test_accepts_page_number(self):
        chunk = ChunkEmbedding(index=0, text="hello", embedding=[0.1], page_number=3)
        assert chunk.page_number == 3


class _FakePageText:
    """Stand-in for BE.file_store.PageText to avoid cross-module import in tests."""

    def __init__(self, page_number: int, text: str):
        self.page_number = page_number
        self.text = text


class TestChunkTextWithPages:
    def test_preserves_page_numbers(self):
        pages = [
            _FakePageText(1, "Short text on page one."),
            _FakePageText(2, "Short text on page two."),
        ]
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            result = chunk_text_with_pages(pages)

        assert len(result) == 2
        assert result[0][1] == 1
        assert result[1][1] == 2

    def test_long_page_splits_with_same_page_number(self):
        pages = [_FakePageText(5, "word " * 500)]
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.EMBEDDING_CHUNK_SIZE = 200
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 20
            result = chunk_text_with_pages(pages)

        assert len(result) > 1
        # All chunks should have page_number 5
        assert all(pn == 5 for _, pn in result)

    def test_empty_pages_returns_empty(self):
        with patch("AI.embeddings.settings") as mock_settings:
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            result = chunk_text_with_pages([])

        assert result == []


class TestGenerateEmbeddingsWithPages:
    def test_produces_embeddings_with_page_numbers(self, run):
        pages = [
            _FakePageText(1, "Page one text."),
            _FakePageText(2, "Page two text."),
        ]
        mock_response = _MockEmbedResponse(
            embeddings=[[0.1, 0.2], [0.3, 0.4]]
        )
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(return_value=mock_response)

        with (
            patch("AI.embeddings._get_async_client", return_value=mock_client),
            patch("AI.embeddings.settings") as mock_settings,
        ):
            mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            result = run(generate_embeddings_with_pages(pages))

        assert isinstance(result, EmbeddingResult)
        assert len(result.chunks) == 2
        assert result.chunks[0].page_number == 1
        assert result.chunks[1].page_number == 2
        assert result.model == "nomic-embed-text"

    def test_empty_pages_raises_value_error(self, run):
        with pytest.raises(ValueError, match="empty pages"):
            run(generate_embeddings_with_pages([]))

    def test_model_override(self, run):
        pages = [_FakePageText(1, "Some text.")]
        mock_response = _MockEmbedResponse(embeddings=[[0.1]])
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(return_value=mock_response)

        with (
            patch("AI.embeddings._get_async_client", return_value=mock_client),
            patch("AI.embeddings.settings") as mock_settings,
        ):
            mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
            mock_settings.EMBEDDING_CHUNK_SIZE = 1000
            mock_settings.EMBEDDING_CHUNK_OVERLAP = 200
            result = run(generate_embeddings_with_pages(pages, model="custom-model"))

        assert result.model == "custom-model"
        mock_client.embed.assert_called_once_with(
            model="custom-model", input=["Some text."]
        )
