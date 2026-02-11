"""Qdrant vector store for document embeddings with per-user multi-tenancy."""

from datetime import datetime, timezone
from uuid import UUID, uuid5

from BE.config import settings
from BE.logger import setup_logger

logger = setup_logger(__name__)

__all__ = [
    "get_client",
    "init_collection",
    "store_embeddings",
    "delete_file_embeddings",
    "close_client",
]

# Fixed namespace for deterministic point IDs
_POINT_ID_NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

_UPSERT_BATCH_SIZE = 100

_client = None


def _make_point_id(file_id: str, chunk_index: int) -> str:
    """Generate a deterministic UUID5 point ID from file_id and chunk_index.

    Re-embedding the same file overwrites existing points automatically.
    """
    return str(uuid5(_POINT_ID_NAMESPACE, f"{file_id}:{chunk_index}"))


def get_client():
    """Return the singleton AsyncQdrantClient, or None if Qdrant is disabled.

    Uses gRPC (port from QDRANT_GRPC_PORT) for faster batch upserts.
    """
    global _client
    if not settings.QDRANT_ENABLED:
        return None
    if _client is not None:
        return _client

    from qdrant_client import AsyncQdrantClient

    _client = AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        prefer_grpc=True,
        grpc_port=settings.QDRANT_GRPC_PORT,
    )
    logger.info("Qdrant client created (url=%s)", settings.QDRANT_URL)
    return _client


async def init_collection() -> bool:
    """Create the embeddings collection if it does not exist.

    Configures HNSW for multi-tenancy: no global index (m=0),
    per-tenant indexes via payload_m=16. Adds payload indexes on
    user_id (tenant key) and file_id (for file-level deletion).

    Returns True if collection is ready, False on error.
    """
    client = get_client()
    if client is None:
        return False

    from qdrant_client.models import (
        Distance,
        HnswConfigDiff,
        PayloadSchemaType,
        VectorParams,
    )

    collection_name = settings.QDRANT_COLLECTION_NAME

    try:
        exists = await client.collection_exists(collection_name)
        if exists:
            logger.info("Qdrant collection '%s' already exists", collection_name)
            return True

        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSIONS,
                distance=Distance.COSINE,
            ),
            hnsw_config=HnswConfigDiff(payload_m=16, m=0),
        )
        logger.info("Created Qdrant collection '%s'", collection_name)

        # Payload indexes for multi-tenancy and file-level operations
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="user_id",
            field_schema=PayloadSchemaType.KEYWORD,
            is_tenant=True,
        )
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="file_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Payload indexes created on user_id (tenant) and file_id")
        return True

    except Exception as exc:
        logger.error("Failed to initialize Qdrant collection: %s", exc)
        return False


async def store_embeddings(
    file_id: str,
    user_id: str,
    session_id: str,
    original_name: str,
    mime_type: str,
    embedding_result,
) -> int:
    """Upsert chunk embeddings into Qdrant.

    Args:
        file_id: PostgreSQL FileUpload UUID.
        user_id: Owner's user ID (tenant key).
        session_id: Chat session ID (may be empty string).
        original_name: Original filename.
        mime_type: MIME type of the uploaded file.
        embedding_result: EmbeddingResult from AI.embeddings.

    Returns:
        Number of points stored.
    """
    client = get_client()
    if client is None:
        return 0

    from qdrant_client.models import PointStruct

    total_chunks = len(embedding_result.chunks)
    now = datetime.now(timezone.utc).isoformat()

    points = []
    for chunk in embedding_result.chunks:
        point_id = _make_point_id(file_id, chunk.index)
        points.append(
            PointStruct(
                id=point_id,
                vector=chunk.embedding,
                payload={
                    "file_id": file_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "original_name": original_name,
                    "mime_type": mime_type,
                    "chunk_index": chunk.index,
                    "total_chunks": total_chunks,
                    "chunk_text": chunk.text,
                    "embedding_model": embedding_result.model,
                    "created_at": now,
                },
            )
        )

    # Upsert in batches
    collection_name = settings.QDRANT_COLLECTION_NAME
    stored = 0
    for i in range(0, len(points), _UPSERT_BATCH_SIZE):
        batch = points[i : i + _UPSERT_BATCH_SIZE]
        await client.upsert(collection_name=collection_name, points=batch)
        stored += len(batch)

    logger.info(
        "Stored %d embedding points for file %s (user=%s)",
        stored,
        file_id,
        user_id,
    )
    return stored


async def delete_file_embeddings(file_id: str, user_id: str) -> bool:
    """Delete all embedding points for a file, scoped to the owning user.

    Args:
        file_id: PostgreSQL FileUpload UUID.
        user_id: Owner's user ID (ownership safety).

    Returns:
        True if deletion succeeded, False on error.
    """
    client = get_client()
    if client is None:
        return False

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    try:
        await client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="file_id", match=MatchValue(value=file_id)),
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                ]
            ),
        )
        logger.info(
            "Deleted embeddings for file %s (user=%s)", file_id, user_id
        )
        return True
    except Exception as exc:
        logger.error(
            "Failed to delete embeddings for file %s: %s", file_id, exc
        )
        return False


async def close_client() -> None:
    """Close the Qdrant client and reset the singleton."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("Qdrant client closed")
