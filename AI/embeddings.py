"""Text chunking and Ollama embedding generation service."""

from dataclasses import dataclass

from ollama import AsyncClient

from BE.config import settings
from BE.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ChunkEmbedding:
    """A single chunk with its embedding vector."""

    index: int
    text: str
    embedding: list[float]


@dataclass
class EmbeddingResult:
    """Result of embedding a full text document."""

    chunks: list[ChunkEmbedding]
    model: str


def _get_async_client() -> AsyncClient:
    """Create an async Ollama client with configured base URL and auth."""
    return AsyncClient(
        host=settings.OLLAMA_BASE_URL,
        headers={"authorization": f"Bearer {settings.OLLAMA_API_KEY}"}
        if settings.OLLAMA_API_KEY
        else {},
    )


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """Split text into overlapping chunks using RecursiveCharacterTextSplitter.

    Args:
        text: The text to split.
        chunk_size: Max characters per chunk. Defaults to settings.EMBEDDING_CHUNK_SIZE.
        chunk_overlap: Overlap between chunks. Defaults to settings.EMBEDDING_CHUNK_OVERLAP.

    Returns:
        List of text chunks.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    size = chunk_size if chunk_size is not None else settings.EMBEDDING_CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else settings.EMBEDDING_CHUNK_OVERLAP

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
    )
    return splitter.split_text(text)


async def generate_embeddings(
    text: str,
    model: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> EmbeddingResult:
    """Chunk text and generate embeddings via Ollama.

    Args:
        text: The full text to embed.
        model: Ollama embedding model name. Defaults to settings.EMBEDDING_MODEL.
        chunk_size: Optional chunk size override.
        chunk_overlap: Optional chunk overlap override.

    Returns:
        EmbeddingResult with chunk embeddings.

    Raises:
        ValueError: If text is empty or whitespace-only.
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate embeddings for empty text")

    model_name = model or settings.EMBEDDING_MODEL
    chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    client = _get_async_client()
    response = await client.embed(model=model_name, input=chunks)

    chunk_embeddings = [
        ChunkEmbedding(index=i, text=chunk, embedding=embedding)
        for i, (chunk, embedding) in enumerate(zip(chunks, response.embeddings))
    ]

    return EmbeddingResult(chunks=chunk_embeddings, model=model_name)
