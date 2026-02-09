"""FastAPI chat server exposing the chat Agent via HTTP endpoints."""

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from AI.agents import init_agent
from AI.prompts.general_agent_prompt import GENERAL_AGENT_PROMPT
from AI.tools import get_enabled_tools
from BE.archive_store import PostgresArchiveStore, create_store as _create_archive_store
from BE.async_utils import init_loop, shutdown_tasks
from BE.auth import UserInfo, create_access_token, get_current_user, verify_google_token
from BE.user_store import upsert_user
from BE.config import _parse_comma_separated, init_config, settings
from BE.logger import redact_url, setup_logger

init_config()
logger = setup_logger(__name__)

__all__ = ["app"]

MAX_TOTAL_FILE_SIZE = 20 * 1024 * 1024  # 20MB
SESSION_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"


class FileSizeLimitExceeded(Exception):
    """Raised when total uploaded file size exceeds the limit."""


class FileAttachment(BaseModel):
    name: str
    type: str
    content: str
    size: int


class ChatRequest(BaseModel):
    """Request model for chat endpoints."""

    message: str = Field(max_length=100_000)
    session_id: str = Field(max_length=128, pattern=SESSION_ID_PATTERN)
    files: list[FileAttachment] | None = None


def get_archive_store() -> PostgresArchiveStore:
    """Dependency that returns the archive store or raises 503."""
    store = _create_archive_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Archive store unavailable")
    return store


def build_prompt_with_files(
    message: str, files: list[FileAttachment]
) -> tuple[str, list[dict], list[dict]]:
    """Process file attachments and return (augmented_prompt, images_list, file_meta).

    Only image files are processed (kept as multimodal data URLs).
    Non-image files (text, PDF, etc.) are silently skipped.
    ``file_meta`` contains lightweight metadata (name, type) for each image
    so it can be persisted on the message and restored after a page reload.
    """
    text_parts: list[str] = []
    images: list[dict] = []
    file_meta: list[dict] = []

    for f in files:
        mime = f.type or ""

        if mime.startswith("image/"):
            images.append({"url": f.content})
            text_parts.append(f"[Attached image: {f.name}]")
            file_meta.append({"name": f.name, "type": f.type})

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


def process_files(
    message: str, files: list[FileAttachment] | None
) -> tuple[str, list[dict], list[dict]]:
    """Validate file sizes and build augmented prompt.

    Returns (prompt, images, file_attachments).
    Raises FileSizeLimitExceeded if total size exceeds MAX_TOTAL_FILE_SIZE.
    """
    if not files:
        return message, [], []
    total_size = sum(f.size for f in files)
    if total_size > MAX_TOTAL_FILE_SIZE:
        raise FileSizeLimitExceeded()
    prompt, images, file_attachments = build_prompt_with_files(message, files)
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
        logger.warning(
            "GOOGLE_CLIENT_ID is empty — Google OAuth login will not work."
        )

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

    app.state.general_agent = init_agent(
        system_prompt=GENERAL_AGENT_PROMPT,
        tools=tools,
        maintain_history=True,
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
    logger.info("=" * 60)

    yield

    logger.info("Application shutdown")
    await shutdown_tasks()
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
async def chat(body: ChatRequest, request: Request, user: UserInfo = Depends(get_current_user)):
    """Send a message and get a complete response."""
    logger.info(
        "POST /chat (session_id=%s, message_preview=%.50s)",
        body.session_id,
        body.message,
    )

    try:
        prompt, images, file_attachments = process_files(body.message, body.files)
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
async def chat_stream(body: ChatRequest, request: Request, user: UserInfo = Depends(get_current_user)):
    """Send a message and get a streaming SSE response."""
    logger.info(
        "POST /chat/stream (session_id=%s, message_preview=%.50s)",
        body.session_id,
        body.message,
    )

    logger.info("Files received: %d", len(body.files) if body.files else 0)

    try:
        prompt, images, file_attachments = process_files(body.message, body.files)
    except FileSizeLimitExceeded:
        return JSONResponse(
            status_code=413,
            content={"detail": "Total file size exceeds 20MB limit"},
        )

    agent = request.app.state.general_agent
    await agent.warm_session(body.session_id, user_id=user.id)

    async def generate():
        async for event in agent.stream(
            prompt,
            session_id=body.session_id,
            images=images or None,
            file_attachments=file_attachments or None,
            user_id=user.id,
        ):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"
        logger.info("POST /chat/stream complete (session_id=%s)", body.session_id)

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
