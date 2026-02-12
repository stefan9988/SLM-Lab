"""Tests for BE.vector_store module."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from BE.vector_store import (
    _embed_queries,
    _make_point_id,
    _POINT_ID_NAMESPACE,
    _UPSERT_BATCH_SIZE,
    close_client,
    delete_file_embeddings,
    get_client,
    init_collection,
    search_chunks,
    store_embeddings,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def run(event_loop):
    """Helper to run coroutines in the test event loop."""
    return event_loop.run_until_complete


# ---------------------------------------------------------------------------
# Helpers – lightweight fakes for EmbeddingResult / ChunkEmbedding
# ---------------------------------------------------------------------------

class FakeChunk:
    def __init__(self, index: int, text: str, embedding: list[float], page_number=None):
        self.index = index
        self.text = text
        self.embedding = embedding
        self.page_number = page_number


class FakeEmbeddingResult:
    def __init__(self, chunks: list[FakeChunk], model: str = "nomic-embed-text"):
        self.chunks = chunks
        self.model = model


def _make_fake_result(n_chunks: int = 3, dims: int = 4) -> FakeEmbeddingResult:
    """Create a FakeEmbeddingResult with *n_chunks* chunks of *dims* dimensions."""
    chunks = [
        FakeChunk(index=i, text=f"chunk {i}", embedding=[0.1 * i] * dims)
        for i in range(n_chunks)
    ]
    return FakeEmbeddingResult(chunks=chunks)


# ===========================================================================
# TestMakePointId
# ===========================================================================


class TestMakePointId:
    def test_returns_valid_uuid(self):
        result = _make_point_id("file-123", 0)
        UUID(result)

    def test_deterministic(self):
        a = _make_point_id("file-abc", 5)
        b = _make_point_id("file-abc", 5)
        assert a == b

    def test_different_file_ids(self):
        a = _make_point_id("file-1", 0)
        b = _make_point_id("file-2", 0)
        assert a != b

    def test_different_chunk_indexes(self):
        a = _make_point_id("file-1", 0)
        b = _make_point_id("file-1", 1)
        assert a != b


# ===========================================================================
# TestGetClient
# ===========================================================================


class TestGetClient:
    def setup_method(self):
        import BE.vector_store as vs
        vs._client = None

    def test_returns_none_when_disabled(self):
        with patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_ENABLED = False
            assert get_client() is None

    def test_creates_client_when_enabled(self):
        with patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_ENABLED = True
            mock_settings.QDRANT_URL = "http://localhost:6333"
            mock_settings.QDRANT_API_KEY = "test-key"
            mock_settings.QDRANT_GRPC_PORT = 6334

            mock_instance = MagicMock()
            with patch("qdrant_client.AsyncQdrantClient", return_value=mock_instance):
                client = get_client()

            assert client is mock_instance

    def test_singleton_returns_same_client(self):
        import BE.vector_store as vs
        fake_client = MagicMock()
        vs._client = fake_client

        with patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_ENABLED = True
            result = get_client()

        assert result is fake_client

    def teardown_method(self):
        import BE.vector_store as vs
        vs._client = None


# ===========================================================================
# TestInitCollection
# ===========================================================================


class TestInitCollection:
    def setup_method(self):
        import BE.vector_store as vs
        vs._client = None

    def test_returns_false_when_disabled(self, run):
        with patch("BE.vector_store.get_client", return_value=None):
            assert run(init_collection()) is False

    def test_skips_create_when_collection_exists(self, run):
        mock_client = AsyncMock()
        mock_client.collection_exists = AsyncMock(return_value=True)
        mock_client.create_payload_index = AsyncMock()

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"
            mock_settings.EMBEDDING_DIMENSIONS = 768

            result = run(init_collection())

        assert result is True
        mock_client.create_collection.assert_not_called()
        # Indexes are still ensured even for existing collections
        assert mock_client.create_payload_index.call_count == 3

    def test_creates_collection_and_indexes(self, run):
        mock_client = AsyncMock()
        mock_client.collection_exists = AsyncMock(return_value=False)
        mock_client.create_collection = AsyncMock()
        mock_client.create_payload_index = AsyncMock()

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"
            mock_settings.EMBEDDING_DIMENSIONS = 768

            result = run(init_collection())

        assert result is True
        mock_client.create_collection.assert_called_once()
        assert mock_client.create_payload_index.call_count == 3

        # Verify user_id index has is_tenant=True
        calls = mock_client.create_payload_index.call_args_list
        user_id_call = [c for c in calls if c.kwargs.get("field_name") == "user_id"]
        assert len(user_id_call) == 1
        assert user_id_call[0].kwargs["is_tenant"] is True

        # Verify chunk_text full-text index
        text_call = [c for c in calls if c.kwargs.get("field_name") == "chunk_text"]
        assert len(text_call) == 1

    def test_handles_error_gracefully(self, run):
        mock_client = AsyncMock()
        mock_client.collection_exists = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"
            mock_settings.EMBEDDING_DIMENSIONS = 768

            result = run(init_collection())

        assert result is False

    def teardown_method(self):
        import BE.vector_store as vs
        vs._client = None


# ===========================================================================
# TestStoreEmbeddings
# ===========================================================================


class TestStoreEmbeddings:
    def test_returns_zero_when_disabled(self, run):
        with patch("BE.vector_store.get_client", return_value=None):
            result = run(store_embeddings(
                file_id="f1", user_id="u1", session_id="s1",
                original_name="test.txt", mime_type="text/plain",
                embedding_result=_make_fake_result(),
            ))
        assert result == 0

    def test_stores_all_chunks(self, run):
        mock_client = AsyncMock()
        mock_client.upsert = AsyncMock()

        fake_result = _make_fake_result(n_chunks=3)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            count = run(store_embeddings(
                file_id="file-abc",
                user_id="user-123",
                session_id="sess-1",
                original_name="readme.md",
                mime_type="text/markdown",
                embedding_result=fake_result,
            ))

        assert count == 3
        mock_client.upsert.assert_called_once()
        points = mock_client.upsert.call_args.kwargs["points"]
        assert len(points) == 3

    def test_correct_payload_fields(self, run):
        mock_client = AsyncMock()
        mock_client.upsert = AsyncMock()

        fake_result = _make_fake_result(n_chunks=1)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            run(store_embeddings(
                file_id="f1",
                user_id="u1",
                session_id="s1",
                original_name="data.csv",
                mime_type="text/csv",
                embedding_result=fake_result,
            ))

        points = mock_client.upsert.call_args.kwargs["points"]
        payload = points[0].payload
        assert payload["file_id"] == "f1"
        assert payload["user_id"] == "u1"
        assert payload["session_id"] == "s1"
        assert payload["original_name"] == "data.csv"
        assert payload["mime_type"] == "text/csv"
        assert payload["chunk_index"] == 0
        assert payload["total_chunks"] == 1
        assert payload["chunk_text"] == "chunk 0"
        assert payload["embedding_model"] == "nomic-embed-text"
        assert payload["page_number"] is None  # FakeChunk defaults to None
        assert "created_at" in payload
        # Verify created_at is valid ISO 8601
        datetime.fromisoformat(payload["created_at"])

    def test_deterministic_point_ids(self, run):
        mock_client = AsyncMock()
        mock_client.upsert = AsyncMock()

        fake_result = _make_fake_result(n_chunks=2)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            run(store_embeddings(
                file_id="f1", user_id="u1", session_id="s1",
                original_name="test.txt", mime_type="text/plain",
                embedding_result=fake_result,
            ))

        points = mock_client.upsert.call_args.kwargs["points"]
        assert points[0].id == _make_point_id("f1", 0)
        assert points[1].id == _make_point_id("f1", 1)

    def test_batches_large_chunk_count(self, run):
        mock_client = AsyncMock()
        mock_client.upsert = AsyncMock()

        n = _UPSERT_BATCH_SIZE + 50
        fake_result = _make_fake_result(n_chunks=n)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            count = run(store_embeddings(
                file_id="f1", user_id="u1", session_id="s1",
                original_name="big.txt", mime_type="text/plain",
                embedding_result=fake_result,
            ))

        assert count == n
        assert mock_client.upsert.call_count == 2
        first_batch = mock_client.upsert.call_args_list[0].kwargs["points"]
        second_batch = mock_client.upsert.call_args_list[1].kwargs["points"]
        assert len(first_batch) == _UPSERT_BATCH_SIZE
        assert len(second_batch) == 50

    def test_empty_session_id(self, run):
        mock_client = AsyncMock()
        mock_client.upsert = AsyncMock()

        fake_result = _make_fake_result(n_chunks=1)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            run(store_embeddings(
                file_id="f1", user_id="u1", session_id="",
                original_name="test.txt", mime_type="text/plain",
                embedding_result=fake_result,
            ))

        points = mock_client.upsert.call_args.kwargs["points"]
        assert points[0].payload["session_id"] == ""

    def test_includes_page_number_in_payload(self, run):
        mock_client = AsyncMock()
        mock_client.upsert = AsyncMock()

        chunks = [
            FakeChunk(index=0, text="chunk 0", embedding=[0.1], page_number=3),
            FakeChunk(index=1, text="chunk 1", embedding=[0.2], page_number=5),
        ]
        fake_result = FakeEmbeddingResult(chunks=chunks)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            run(store_embeddings(
                file_id="f1", user_id="u1", session_id="s1",
                original_name="doc.pdf", mime_type="application/pdf",
                embedding_result=fake_result,
            ))

        points = mock_client.upsert.call_args.kwargs["points"]
        assert points[0].payload["page_number"] == 3
        assert points[1].payload["page_number"] == 5


# ===========================================================================
# TestDeleteFileEmbeddings
# ===========================================================================


class TestDeleteFileEmbeddings:
    def test_returns_false_when_disabled(self, run):
        with patch("BE.vector_store.get_client", return_value=None):
            assert run(delete_file_embeddings("f1", "u1")) is False

    def test_deletes_with_correct_filter(self, run):
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock()

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            result = run(delete_file_embeddings("file-1", "user-1"))

        assert result is True
        mock_client.delete.assert_called_once()

        # Verify both file_id and user_id are in the filter
        call_kwargs = mock_client.delete.call_args.kwargs
        filter_obj = call_kwargs["points_selector"]
        conditions = filter_obj.must
        field_keys = [c.key for c in conditions]
        assert "file_id" in field_keys
        assert "user_id" in field_keys

    def test_handles_error_gracefully(self, run):
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(side_effect=Exception("Qdrant down"))

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            result = run(delete_file_embeddings("f1", "u1"))

        assert result is False


# ===========================================================================
# TestCloseClient
# ===========================================================================


class TestCloseClient:
    def setup_method(self):
        import BE.vector_store as vs
        vs._client = None

    def test_closes_and_resets(self, run):
        import BE.vector_store as vs

        mock_client = AsyncMock()
        vs._client = mock_client

        run(close_client())

        mock_client.close.assert_called_once()
        assert vs._client is None

    def test_noop_when_no_client(self, run):
        import BE.vector_store as vs
        vs._client = None

        run(close_client())
        assert vs._client is None

    def teardown_method(self):
        import BE.vector_store as vs
        vs._client = None


# ===========================================================================
# TestEmbedQueries
# ===========================================================================


class TestEmbedQueries:
    def test_calls_ollama_with_correct_args(self, run):
        fake_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        mock_response = MagicMock()
        mock_response.embeddings = fake_embeddings

        mock_embed = AsyncMock(return_value=mock_response)
        mock_instance = MagicMock()
        mock_instance.embed = mock_embed

        with patch("ollama.AsyncClient", return_value=mock_instance), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_API_KEY = ""
            mock_settings.EMBEDDING_MODEL = "nomic-embed-text"

            result = run(_embed_queries(["query 1", "query 2"]))

        assert result == fake_embeddings
        mock_embed.assert_called_once_with(
            model="nomic-embed-text", input=["query 1", "query 2"]
        )


# ===========================================================================
# TestSearchChunks
# ===========================================================================


class _FakePoint:
    """Minimal stand-in for a Qdrant ScoredPoint."""
    def __init__(self, payload: dict, score: float):
        self.payload = payload
        self.score = score


class TestSearchChunks:
    def setup_method(self):
        import BE.vector_store as vs
        vs._client = None

    def test_returns_empty_when_disabled(self, run):
        with patch("BE.vector_store.get_client", return_value=None):
            result = run(search_chunks(["q"], "f1", "u1"))
        assert result == []

    def test_search_returns_results(self, run):
        mock_client = AsyncMock()
        fake_point = _FakePoint(
            payload={
                "chunk_index": 0,
                "chunk_text": "hello world",
                "original_name": "test.txt",
                "file_id": "f1",
                "page_number": 7,
            },
            score=0.95,
        )
        mock_query_result = MagicMock()
        mock_query_result.points = [fake_point]
        mock_client.query_points = AsyncMock(return_value=mock_query_result)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store._embed_queries", new_callable=AsyncMock, return_value=[[0.1, 0.2]]), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            results = run(search_chunks(["hello"], "f1", "u1", limit=5))

        assert len(results) == 1
        assert results[0]["chunk_index"] == 0
        assert results[0]["chunk_text"] == "hello world"
        assert results[0]["score"] == 0.95
        assert results[0]["original_name"] == "test.txt"
        assert results[0]["file_id"] == "f1"
        assert results[0]["page_number"] == 7

    def test_search_returns_none_page_number_for_old_data(self, run):
        """Old Qdrant points without page_number return None (backward compat)."""
        mock_client = AsyncMock()
        fake_point = _FakePoint(
            payload={
                "chunk_index": 0,
                "chunk_text": "old chunk",
                "original_name": "legacy.txt",
                "file_id": "f1",
            },
            score=0.80,
        )
        mock_query_result = MagicMock()
        mock_query_result.points = [fake_point]
        mock_client.query_points = AsyncMock(return_value=mock_query_result)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store._embed_queries", new_callable=AsyncMock, return_value=[[0.1]]), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            results = run(search_chunks(["old"], "f1", "u1"))

        assert results[0]["page_number"] is None

    def test_builds_correct_prefetch_count(self, run):
        """1 query → 2 prefetches, 3 queries → 6 prefetches."""
        mock_client = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.points = []
        mock_client.query_points = AsyncMock(return_value=mock_query_result)

        for n_queries, expected_prefetches in [(1, 2), (3, 6)]:
            queries = [f"q{i}" for i in range(n_queries)]
            embeddings = [[0.1] * 4] * n_queries

            with patch("BE.vector_store.get_client", return_value=mock_client), \
                 patch("BE.vector_store._embed_queries", new_callable=AsyncMock, return_value=embeddings), \
                 patch("BE.vector_store.settings") as mock_settings:
                mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

                run(search_chunks(queries, "f1", "u1"))

            call_kwargs = mock_client.query_points.call_args.kwargs
            assert len(call_kwargs["prefetch"]) == expected_prefetches

    def test_applies_user_and_file_filter(self, run):
        mock_client = AsyncMock()
        mock_query_result = MagicMock()
        mock_query_result.points = []
        mock_client.query_points = AsyncMock(return_value=mock_query_result)

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store._embed_queries", new_callable=AsyncMock, return_value=[[0.1]]), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            run(search_chunks(["test"], "file-abc", "user-xyz"))

        prefetches = mock_client.query_points.call_args.kwargs["prefetch"]
        # Check the dense-only prefetch filter (first prefetch)
        conditions = prefetches[0].filter.must
        keys = [c.key for c in conditions]
        assert "user_id" in keys
        assert "file_id" in keys

    def test_handles_embed_error(self, run):
        mock_client = AsyncMock()

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store._embed_queries", new_callable=AsyncMock, side_effect=Exception("Ollama down")):
            result = run(search_chunks(["q"], "f1", "u1"))

        assert result == []

    def test_handles_query_error(self, run):
        mock_client = AsyncMock()
        mock_client.query_points = AsyncMock(side_effect=Exception("Qdrant down"))

        with patch("BE.vector_store.get_client", return_value=mock_client), \
             patch("BE.vector_store._embed_queries", new_callable=AsyncMock, return_value=[[0.1]]), \
             patch("BE.vector_store.settings") as mock_settings:
            mock_settings.QDRANT_COLLECTION_NAME = "slmlab"

            result = run(search_chunks(["q"], "f1", "u1"))

        assert result == []

    def teardown_method(self):
        import BE.vector_store as vs
        vs._client = None
