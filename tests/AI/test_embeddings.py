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
    generate_embeddings,
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
