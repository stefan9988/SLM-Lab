"""FastAPI chat server exposing the chat Agent via HTTP endpoints."""

import json
import re
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from AI.agents import init_agent
from AI.prompts import build_general_agent_prompt, DOCUMENT_AGENT_PROMPT
from AI.agents.metadata import get_delegatable_agents
from AI.prompts.extraction_prompt import build_extraction_prompt
from AI.prompts.validation_agent_prompt import VALIDATION_AGENT_PROMPT
from AI.tools import (
    get_enabled_tools,
    get_document_agent_enabled_tools,
    get_validation_agent_enabled_tools,
)
from BE.archive_store import (
    PostgresArchiveStore,
    create_store as _create_archive_store,
    ensure_session_exists,
)
from BE.schema_store import SchemaStore, create_store as _create_schema_store
from BE.async_utils import init_loop, schedule_background_task, shutdown_tasks
from BE.auth import UserInfo, create_access_token, get_current_user, verify_google_token
from BE.user_store import upsert_user
from BE.config import _parse_comma_separated, init_config, settings
from BE.file_store import get_file_content, get_file_pages, sanitize_filename, save_file
from BE.logger import redact_url, setup_logger

init_config()
logger = setup_logger(__name__)

__all__ = ["app"]

MAX_TOTAL_FILE_SIZE = 20 * 1024 * 1024  # 20MB
SESSION_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"


class FileSizeLimitExceeded(Exception):
    """Raised when total uploaded file size exceeds the limit."""


def _make_embed_task(
    file_id: str,
    user_id: str,
    session_id: str = "",
    original_name: str = "",
    mime_type: str = "",
):
    """Return an async callable that embeds a file's text content."""

    async def _embed():
        from AI.embeddings import generate_embeddings, generate_embeddings_with_pages

        # Try page-aware extraction for PDFs first
        try:
            pages = await get_file_pages(file_id, user_id)
        except (ValueError, FileNotFoundError) as exc:
            logger.debug("Skipping embedding for file %s: %s", file_id, exc)
            return
        except Exception as exc:
            logger.warning("Failed to read file %s for embedding: %s", file_id, exc)
            return

        try:
            if pages is not None:
                result = await generate_embeddings_with_pages(pages)
            else:
                text_content = await get_file_content(file_id, user_id)
                result = await generate_embeddings(text_content)
            dims = len(result.chunks[0].embedding) if result.chunks else 0
            logger.info(
                "Embeddings generated for file %s: %d chunks, %d dimensions, model=%s",
                file_id,
                len(result.chunks),
                dims,
                result.model,
            )
        except ValueError as exc:
            logger.debug("Skipping embedding for file %s: %s", file_id, exc)
            return
        except Exception as exc:
            logger.warning("Embedding failed for file %s: %s", file_id, exc)
            return

        # Store embeddings in Qdrant if enabled
        if settings.QDRANT_ENABLED:
            try:
                from BE.vector_store import store_embeddings

                count = await store_embeddings(
                    file_id=file_id,
                    user_id=user_id,
                    session_id=session_id or "",
                    original_name=original_name,
                    mime_type=mime_type,
                    embedding_result=result,
                )
                logger.info("Stored %d vectors in Qdrant for file %s", count, file_id)
            except Exception as exc:
                logger.warning("Qdrant storage failed for file %s: %s", file_id, exc)

    return _embed


class FileAttachment(BaseModel):
    name: str = Field(max_length=255)
    type: str = Field(max_length=255)
    content: str
    size: int = Field(ge=0, le=20_000_000)


class ChatRequest(BaseModel):
    """Request model for chat endpoints."""

    message: str = Field(max_length=100_000)
    session_id: str = Field(max_length=128, pattern=SESSION_ID_PATTERN)
    files: list[FileAttachment] | None = None


class AnalyzeRequest(BaseModel):
    """Request model for document analysis endpoint."""

    file: FileAttachment
    schema_id: str = Field(max_length=128)
    session_id: str | None = Field(
        default=None, max_length=128, pattern=SESSION_ID_PATTERN
    )


def get_archive_store() -> PostgresArchiveStore:
    """Dependency that returns the archive store or raises 503."""
    store = _create_archive_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Archive store unavailable")
    return store


def get_schema_store() -> SchemaStore:
    """Dependency that returns the schema store or raises 503."""
    store = _create_schema_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Schema store unavailable")
    return store


class SchemaFieldPayload(BaseModel):
    id: str
    key: str
    description: str = ""


class CreateSchemaRequest(BaseModel):
    name: str = Field(max_length=255)
    fields: list[SchemaFieldPayload] = []


class UpdateSchemaRequest(BaseModel):
    name: str = Field(max_length=255)
    fields: list[SchemaFieldPayload] = []


async def build_prompt_with_files(
    message: str,
    files: list[FileAttachment],
    user_id: str,
    session_id: str | None = None,
) -> tuple[str, list[dict], list[dict]]:
    """Process file attachments and return (augmented_prompt, images_list, file_meta).

    Image files are kept as multimodal data URLs.
    Non-image files are saved to PostgreSQL and referenced by UUID.
    ``file_meta`` contains lightweight metadata (name, type, and optionally
    file_id) so it can be persisted on the message and restored after reload.
    """
    text_parts: list[str] = []
    images: list[dict] = []
    file_meta: list[dict] = []

    for f in files:
        mime = f.type or ""
        safe_name = sanitize_filename(f.name)

        if mime.startswith("image/"):
            images.append({"url": f.content})
            text_parts.append(f"[Attached image: {safe_name}]")
            file_meta.append({"name": safe_name, "type": f.type})
        else:
            file_id = await save_file(
                original_name=safe_name,
                mime_type=mime,
                data_url_content=f.content,
                size_bytes=f.size,
                user_id=user_id,
                session_id=session_id,
            )
            if file_id:
                text_parts.append(f"[Attached file: {safe_name} (file_id: {file_id})]")
                file_meta.append(
                    {"name": safe_name, "type": f.type, "file_id": file_id}
                )
                if settings.EMBEDDING_ENABLED:
                    schedule_background_task(
                        _make_embed_task(
                            file_id,
                            user_id,
                            session_id=session_id or "",
                            original_name=safe_name,
                            mime_type=mime,
                        ),
                        max_retries=1,
                        timeout=60.0,
                        task_name=f"embed_file_{file_id}",
                    )
            else:
                text_parts.append(f"[Attached file: {safe_name} (content not stored)]")
                file_meta.append({"name": safe_name, "type": f.type})

    augmented = message
    if not message.strip() and text_parts:
        augmented = (
            "\n\n".join(text_parts)
            + "\n\nThe user uploaded the above file(s) without a message."
            " Please review and summarize the content."
        )
    elif text_parts:
        augmented = "\n\n".join(text_parts) + "\n\n" + message

    return augmented, images, file_meta


async def process_files(
    message: str,
    files: list[FileAttachment] | None,
    user_id: str,
    session_id: str | None = None,
) -> tuple[str, list[dict], list[dict]]:
    """Validate file sizes and build augmented prompt.

    Returns (prompt, images, file_attachments).
    Raises FileSizeLimitExceeded if total size exceeds MAX_TOTAL_FILE_SIZE.
    """
    if not files:
        return message, [], []
    if len(files) > 20:
        raise FileSizeLimitExceeded()
    total_size = sum(f.size for f in files)
    if total_size > MAX_TOTAL_FILE_SIZE:
        raise FileSizeLimitExceeded()
    prompt, images, file_attachments = await build_prompt_with_files(
        message, files, user_id=user_id, session_id=session_id
    )
    logger.info("Augmented prompt length: %d chars", len(prompt))
    return prompt, images, file_attachments


_INSECURE_JWT_DEFAULTS = {"change-me-in-production", "change-me-to-a-random-secret"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")

    if settings.JWT_SECRET_KEY in _INSECURE_JWT_DEFAULTS:
        raise RuntimeError(
            "JWT_SECRET_KEY is set to an insecure default. "
            "Set a strong random secret via the JWT_SECRET_KEY environment variable."
        )
    if not settings.GOOGLE_CLIENT_ID:
        logger.warning("GOOGLE_CLIENT_ID is empty — Google OAuth login will not work.")

    init_loop()
    tools = get_enabled_tools(settings)
    tool_names = [t.name if hasattr(t, "name") else t.__name__ for t in tools]
    logger.info("General agent tools enabled: %s", tool_names)

    # Initialize PostgreSQL tables if enabled
    if settings.POSTGRES_ENABLED:
        try:
            from BE.database import init_db

            await init_db()
        except Exception as exc:
            logger.warning("PostgreSQL init failed (archive disabled): %s", exc)

    # Initialize Qdrant collection if enabled
    if settings.QDRANT_ENABLED:
        try:
            from BE.vector_store import init_collection

            await init_collection()
        except Exception as exc:
            logger.warning("Qdrant init failed (vector store disabled): %s", exc)

    app.state.general_agent = init_agent(
        system_prompt=build_general_agent_prompt(get_delegatable_agents()),
        tools=tools,
        maintain_history=True,
        provider=settings.GENERAL_AGENT_LLM_PROVIDER or None,
        model_name=settings.GENERAL_AGENT_MODEL_NAME or None,
        agent_name="general_agent",
    )

    doc_tools = get_document_agent_enabled_tools(settings)
    doc_tool_names = [t.name if hasattr(t, "name") else t.__name__ for t in doc_tools]
    logger.info("Document agent tools enabled: %s", doc_tool_names)

    app.state.document_agent = init_agent(
        system_prompt=DOCUMENT_AGENT_PROMPT,
        tools=doc_tools,
        maintain_history=True,
        provider=settings.DOCUMENT_AGENT_LLM_PROVIDER or None,
        model_name=settings.DOCUMENT_AGENT_MODEL_NAME or None,
        agent_name="document_agent",
    )

    val_tools = get_validation_agent_enabled_tools(settings)
    val_tool_names = [t.name if hasattr(t, "name") else t.__name__ for t in val_tools]
    logger.info("Validation agent tools enabled: %s", val_tool_names)

    app.state.validation_agent = init_agent(
        system_prompt=VALIDATION_AGENT_PROMPT,
        tools=val_tools,
        maintain_history=False,
        provider=settings.VALIDATION_AGENT_LLM_PROVIDER or None,
        model_name=settings.VALIDATION_AGENT_MODEL_NAME or None,
        agent_name="validation_agent",
    )

    # Register agents for cross-agent delegation
    from AI.agents import registry

    registry.register("general_agent", app.state.general_agent)
    registry.register(
        "document_agent",
        app.state.document_agent,
        allowed_callers={"general_agent"},
    )
    registry.register(
        "validation_agent",
        app.state.validation_agent,
        allowed_callers={"general_agent"},
    )

    # Log service URLs for easy reference
    logger.info("=" * 60)
    logger.info("SLM-Lab services running:")
    logger.info("  Frontend:   http://localhost:%s", settings.VITE_PORT)
    logger.info("  Backend:    %s", settings.VITE_API_URL)
    logger.info("  Ollama:     %s", settings.OLLAMA_BASE_URL)
    logger.info("  CORS origins: %s", settings.CORS_ALLOW_ORIGINS)
    if settings.REDIS_ENABLED:
        logger.info("  Redis:      %s", redact_url(settings.REDIS_URL))
    if settings.POSTGRES_ENABLED:
        logger.info("  PostgreSQL: %s", redact_url(settings.POSTGRES_URL))
    if settings.QDRANT_ENABLED:
        logger.info("  Qdrant:     %s", settings.QDRANT_URL)
    logger.info("=" * 60)

    yield

    logger.info("Application shutdown")
    await shutdown_tasks()
    if settings.QDRANT_ENABLED:
        from BE.vector_store import close_client

        await close_client()
    if settings.POSTGRES_ENABLED:
        from BE.database import dispose_engine

        await dispose_engine()


app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_comma_separated(settings.CORS_ALLOW_ORIGINS),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=_parse_comma_separated(settings.CORS_ALLOW_METHODS),
    allow_headers=_parse_comma_separated(settings.CORS_ALLOW_HEADERS),
    expose_headers=_parse_comma_separated(settings.CORS_EXPOSE_HEADERS),
    max_age=settings.CORS_MAX_AGE,
)


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    logger.warning("Validation error: %s", exc)
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled error on %s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


class GoogleAuthRequest(BaseModel):
    """Request model for Google OAuth login."""

    token: str


@app.post("/auth/google")
async def google_auth(body: GoogleAuthRequest):
    """Exchange a Google ID token for an app JWT."""
    user = verify_google_token(body.token)
    user_id = await upsert_user(
        email=user.email,
        name=user.name,
        picture=user.picture,
        google_sub=user.google_sub,
    )
    user.id = user_id
    access_token = create_access_token(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.model_dump(),
    }


@app.post("/chat")
async def chat(
    body: ChatRequest, request: Request, user: UserInfo = Depends(get_current_user)
):
    """Send a message and get a complete response."""
    logger.info(
        "POST /chat (session_id=%s, message_preview=%.50s)",
        body.session_id,
        body.message,
    )

    if body.files:
        await ensure_session_exists(body.session_id, user.id)

    try:
        prompt, images, file_attachments = await process_files(
            body.message, body.files, user_id=user.id, session_id=body.session_id
        )
    except FileSizeLimitExceeded:
        return JSONResponse(
            status_code=413,
            content={"detail": "Total file size exceeds 20MB limit"},
        )

    agent = request.app.state.general_agent
    await agent.warm_session(body.session_id, user_id=user.id)
    response = await agent.invoke(
        prompt,
        session_id=body.session_id,
        images=images or None,
        file_attachments=file_attachments or None,
        user_id=user.id,
    )
    logger.info(
        "POST /chat response (session_id=%s, length=%d)",
        body.session_id,
        len(response),
    )
    return {"response": response}


@app.post("/chat/stream")
async def chat_stream(
    body: ChatRequest, request: Request, user: UserInfo = Depends(get_current_user)
):
    """Send a message and get a streaming SSE response."""
    logger.info(
        "POST /chat/stream (session_id=%s, message_preview=%.50s)",
        body.session_id,
        body.message,
    )

    logger.info("Files received: %d", len(body.files) if body.files else 0)

    if body.files:
        await ensure_session_exists(body.session_id, user.id)

    try:
        prompt, images, file_attachments = await process_files(
            body.message, body.files, user_id=user.id, session_id=body.session_id
        )
    except FileSizeLimitExceeded:
        return JSONResponse(
            status_code=413,
            content={"detail": "Total file size exceeds 20MB limit"},
        )

    agent = request.app.state.general_agent
    await agent.warm_session(body.session_id, user_id=user.id)

    async def generate():
        try:
            async for event in agent.stream(
                prompt,
                session_id=body.session_id,
                images=images or None,
                file_attachments=file_attachments or None,
                user_id=user.id,
            ):
                yield f"data: {json.dumps(event)}\n\n"
            logger.info("POST /chat/stream complete (session_id=%s)", body.session_id)
        except Exception as exc:
            logger.error("Chat stream failed: %s", exc, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'LLM error: {exc}'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/history")
async def get_history(
    request: Request,
    session_id: str = Query(min_length=1, max_length=128, pattern=SESSION_ID_PATTERN),
    user: UserInfo = Depends(get_current_user),
):
    """Retrieve conversation history for a session."""
    logger.info("GET /history (session_id=%s)", session_id)
    agent = request.app.state.general_agent
    await agent.warm_session(session_id, user_id=user.id)
    history = await agent.get_history(session_id=session_id, user_id=user.id)
    logger.info("GET /history (session_id=%s, messages=%d)", session_id, len(history))
    return {"history": history}


@app.delete("/history")
async def clear_history(
    request: Request,
    session_id: str = Query(min_length=1, max_length=128, pattern=SESSION_ID_PATTERN),
    user: UserInfo = Depends(get_current_user),
):
    """Clear conversation history for a session."""
    logger.info("DELETE /history (session_id=%s)", session_id)
    agent = request.app.state.general_agent
    await agent.clear_history(session_id=session_id, user_id=user.id)
    return {"status": "cleared"}


class AgentModelRequest(BaseModel):
    provider: str
    model_name: str


@app.get("/general-agent/model")
async def get_general_agent_model(
    request: Request, user: UserInfo = Depends(get_current_user)
):
    """Return the current general agent's provider and model name."""
    agent = request.app.state.general_agent
    return {"provider": agent._provider, "model_name": agent._model_name}


@app.put("/general-agent/model")
async def update_general_agent_model(
    body: AgentModelRequest,
    request: Request,
    user: UserInfo = Depends(get_current_user),
):
    """Re-initialize the general agent with a new LLM, preserving session history."""
    old_agent = request.app.state.general_agent
    old_store = old_agent._store
    new_agent = init_agent(
        system_prompt=build_general_agent_prompt(get_delegatable_agents()),
        tools=get_enabled_tools(settings),
        maintain_history=True,
        provider=body.provider,
        model_name=body.model_name,
    )
    new_agent._store = old_store
    request.app.state.general_agent = new_agent
    from AI.agents import registry

    registry.register("general_agent", new_agent)
    return {"provider": new_agent._provider, "model_name": new_agent._model_name}


@app.get("/document-agent/model")
async def get_document_agent_model(
    request: Request, user: UserInfo = Depends(get_current_user)
):
    """Return the current document agent's provider and model name."""
    agent = request.app.state.document_agent
    return {"provider": agent._provider, "model_name": agent._model_name}


@app.put("/document-agent/model")
async def update_document_agent_model(
    body: AgentModelRequest,
    request: Request,
    user: UserInfo = Depends(get_current_user),
):
    """Re-initialize the document agent with a new LLM, preserving session history."""
    old_agent = request.app.state.document_agent
    old_store = old_agent._store
    new_agent = init_agent(
        system_prompt=DOCUMENT_AGENT_PROMPT,
        tools=get_document_agent_enabled_tools(settings),
        maintain_history=True,
        provider=body.provider,
        model_name=body.model_name,
    )
    new_agent._store = old_store
    request.app.state.document_agent = new_agent
    from AI.agents import registry

    registry.register(
        "document_agent",
        new_agent,
        allowed_callers={"general_agent"},
    )
    return {"provider": new_agent._provider, "model_name": new_agent._model_name}


@app.get("/sessions")
async def list_sessions(
    store: PostgresArchiveStore = Depends(get_archive_store),
    user: UserInfo = Depends(get_current_user),
):
    """List all sessions with titles for the sidebar."""
    sessions = await store.get_all_sessions_with_titles(user_id=user.id)
    return {"sessions": sessions}


# --- Archive endpoints (PostgreSQL) ---


@app.get("/archive/sessions")
async def list_archived_sessions(
    store: PostgresArchiveStore = Depends(get_archive_store),
    user: UserInfo = Depends(get_current_user),
):
    """List all archived sessions."""
    sessions = await store.get_all_sessions(user_id=user.id)
    return {"sessions": sessions}


@app.get("/archive/sessions/{session_id}")
async def get_archived_session(
    session_id: str = Path(max_length=128, pattern=SESSION_ID_PATTERN),
    store: PostgresArchiveStore = Depends(get_archive_store),
    user: UserInfo = Depends(get_current_user),
):
    """Get archived messages for a session."""
    messages = await store.get_messages(session_id, user_id=user.id)
    return {"session_id": session_id, "messages": messages}


@app.delete("/archive/sessions/{session_id}")
async def delete_archived_session(
    session_id: str = Path(max_length=128, pattern=SESSION_ID_PATTERN),
    store: PostgresArchiveStore = Depends(get_archive_store),
    user: UserInfo = Depends(get_current_user),
):
    """Delete an archived session."""
    deleted = await store.delete_session(session_id, user_id=user.id)
    if not deleted:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})
    return {"status": "deleted"}


# --- Extraction schema endpoints (PostgreSQL) ---


@app.get("/schemas")
async def list_schemas(
    store: SchemaStore = Depends(get_schema_store),
    user: UserInfo = Depends(get_current_user),
):
    """List all extraction schemas for the current user."""
    schemas = await store.get_schemas(user_id=user.id)
    return {"schemas": schemas}


@app.post("/schemas")
async def create_schema(
    body: CreateSchemaRequest,
    store: SchemaStore = Depends(get_schema_store),
    user: UserInfo = Depends(get_current_user),
):
    """Create a new extraction schema."""
    schema = await store.create_schema(
        user_id=user.id,
        name=body.name,
        fields=[f.model_dump() for f in body.fields],
    )
    return schema


@app.put("/schemas/{schema_id}")
async def update_schema(
    schema_id: str,
    body: UpdateSchemaRequest,
    store: SchemaStore = Depends(get_schema_store),
    user: UserInfo = Depends(get_current_user),
):
    """Update an extraction schema."""
    updated = await store.update_schema(
        schema_id,
        user_id=user.id,
        name=body.name,
        fields=[f.model_dump() for f in body.fields],
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Schema not found")
    return updated


@app.delete("/schemas/{schema_id}")
async def delete_schema(
    schema_id: str,
    store: SchemaStore = Depends(get_schema_store),
    user: UserInfo = Depends(get_current_user),
):
    """Delete an extraction schema."""
    deleted = await store.delete_schema(schema_id, user_id=user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schema not found")
    return {"status": "deleted"}


# --- Document analysis endpoint ---


def validate_extraction_keys(
    results: list[dict], schema_fields: list[dict]
) -> list[dict]:
    """Ensure all schema keys appear in results, adding nulls for missing ones.

    Numbered variants like ``phone_number_1`` are accepted as matching
    ``phone_number``.  Extra numbered variants the agent returned are kept.
    """
    schema_keys = {f["key"] for f in schema_fields}

    # Build a set of schema keys that are already covered
    covered: set[str] = set()
    for item in results:
        key = item.get("key", "")
        if key in schema_keys:
            covered.add(key)
        else:
            # Check numbered variant: key_<digits>
            match = re.match(r"^(.+)_(\d+)$", key)
            if match and match.group(1) in schema_keys:
                covered.add(match.group(1))

    # Normalise each result item
    validated: list[dict] = []
    for item in results:
        validated.append(
            {
                "key": item.get("key", ""),
                "extraction": item.get("extraction") or None,
                "location": item.get("location") or None,
            }
        )

    # Add missing schema keys with null values
    for key in schema_keys:
        if key not in covered:
            validated.append({"key": key, "extraction": None, "location": None})

    return validated


def _parse_extraction_json(text: str) -> list[dict]:
    """Extract a JSON array from the agent's response text.

    The agent is instructed to return *only* a JSON array, but may wrap it in
    markdown fences.  This helper strips fences and parses the first ``[...]``
    block found.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.replace("```", "")

    # Find the first JSON array
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in agent response")

    return json.loads(cleaned[start : end + 1])


@app.post("/analyze")
async def analyze_document(
    body: AnalyzeRequest,
    request: Request,
    schema_store: SchemaStore = Depends(get_schema_store),
    user: UserInfo = Depends(get_current_user),
):
    """Analyze a document against a schema. Streams SSE events."""
    logger.info(
        "POST /analyze (schema_id=%s, file=%s)",
        body.schema_id,
        body.file.name,
    )

    # 1. Fetch schema
    schemas = await schema_store.get_schemas(user_id=user.id)
    schema = next((s for s in schemas if s["id"] == body.schema_id), None)
    if schema is None:
        raise HTTPException(status_code=404, detail="Schema not found")

    schema_fields: list[dict] = schema["fields"]
    if not schema_fields:
        raise HTTPException(status_code=400, detail="Schema has no fields")

    # 2. Save file
    safe_name = sanitize_filename(body.file.name)
    mime = body.file.type or ""
    file_id = await save_file(
        original_name=safe_name,
        mime_type=mime,
        data_url_content=body.file.content,
        size_bytes=body.file.size,
        user_id=user.id,
    )
    if not file_id:
        raise HTTPException(status_code=500, detail="Failed to save file")

    # 3. Create embeddings synchronously if enabled
    if settings.EMBEDDING_ENABLED:
        embed_fn = _make_embed_task(
            file_id,
            user_id=user.id,
            original_name=safe_name,
            mime_type=mime,
        )
        await embed_fn()

    # 4. Build extraction prompt
    prompt = build_extraction_prompt(schema_fields, file_id)

    # 5. Stream agent response and parse results
    document_agent = request.app.state.document_agent
    session_id = body.session_id or str(uuid4())
    file_attachments = [{"name": safe_name, "type": mime, "file_id": file_id}]

    async def generate():
        full_text = ""
        try:
            async for event in document_agent.stream(
                prompt,
                session_id=session_id,
                file_attachments=file_attachments,
                user_id=user.id,
            ):
                event_type = event.get("type", "")
                if event_type == "token":
                    full_text += event.get("content", "")
                elif event_type in ("status", "tool_use"):
                    yield f"data: {json.dumps({'type': 'status', 'content': event.get('content', '')})}\n\n"

            # Parse and validate results
            results = _parse_extraction_json(full_text)
            validated = validate_extraction_keys(results, schema_fields)

            for item in validated:
                yield f"data: {json.dumps({'type': 'extraction', 'content': item})}\n\n"

        except Exception as exc:
            logger.error("Analysis failed: %s", exc, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

        yield "data: [DONE]\n\n"
        logger.info("POST /analyze complete (schema_id=%s)", body.schema_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
