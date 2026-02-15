"""Text chunking and Ollama embedding generation service."""

from __future__ import annotations

from dataclasses import dataclass, field

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
    page_number: int | None = field(default=None)


@dataclass
class EmbeddingResult:
    """Result of embedding a full text document."""

    chunks: list[ChunkEmbedding]
    model: str


def _get_async_client() -> AsyncClient:
    """Create an async Ollama client with configured base URL and auth."""
    return AsyncClient(
        host=settings.OLLAMA_BASE_URL,
        headers=(
            {"authorization": f"Bearer {settings.OLLAMA_API_KEY}"}
            if settings.OLLAMA_API_KEY
            else {}
        ),
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
    overlap = (
        chunk_overlap if chunk_overlap is not None else settings.EMBEDDING_CHUNK_OVERLAP
    )

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


def chunk_text_with_pages(
    pages: list,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[tuple[str, int | None]]:
    """Split page-segmented text into overlapping chunks, preserving page numbers.

    Args:
        pages: List of PageText objects (page_number, text).
        chunk_size: Max characters per chunk. Defaults to settings.EMBEDDING_CHUNK_SIZE.
        chunk_overlap: Overlap between chunks. Defaults to settings.EMBEDDING_CHUNK_OVERLAP.

    Returns:
        List of (chunk_text, page_number) tuples. page_number is from the
        source page's metadata, preserved through LangChain splitting.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    size = chunk_size if chunk_size is not None else settings.EMBEDDING_CHUNK_SIZE
    overlap = (
        chunk_overlap if chunk_overlap is not None else settings.EMBEDDING_CHUNK_OVERLAP
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
    )

    texts = [p.text for p in pages]
    metadatas = [{"page_number": p.page_number} for p in pages]

    docs = splitter.create_documents(texts, metadatas=metadatas)
    return [(doc.page_content, doc.metadata.get("page_number")) for doc in docs]


async def generate_embeddings_with_pages(
    pages: list,
    model: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> EmbeddingResult:
    """Chunk page-segmented text and generate embeddings via Ollama.

    Like generate_embeddings() but preserves page_number metadata from PDF pages.

    Args:
        pages: List of PageText objects (page_number, text).
        model: Ollama embedding model name. Defaults to settings.EMBEDDING_MODEL.
        chunk_size: Optional chunk size override.
        chunk_overlap: Optional chunk overlap override.

    Returns:
        EmbeddingResult with chunk embeddings including page_number.

    Raises:
        ValueError: If pages is empty or all pages are blank.
    """
    if not pages:
        raise ValueError("Cannot generate embeddings for empty pages")

    chunks_with_pages = chunk_text_with_pages(
        pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    if not chunks_with_pages:
        raise ValueError("Cannot generate embeddings for empty text")

    model_name = model or settings.EMBEDDING_MODEL
    chunk_texts = [text for text, _ in chunks_with_pages]

    client = _get_async_client()
    response = await client.embed(model=model_name, input=chunk_texts)

    chunk_embeddings = [
        ChunkEmbedding(
            index=i,
            text=text,
            embedding=embedding,
            page_number=page_num,
        )
        for i, ((text, page_num), embedding) in enumerate(
            zip(chunks_with_pages, response.embeddings)
        )
    ]

    return EmbeddingResult(chunks=chunk_embeddings, model=model_name)
