"""FastAPI chat server exposing the chat Agent via HTTP endpoints."""

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from AI.agents import init_agent
from AI.prompts.general_agent_prompt import GENERAL_AGENT_PROMPT
from AI.tools import get_enabled_tools
from BE.archive_store import PostgresArchiveStore, create_store as _create_archive_store
from BE.auth import UserInfo, create_access_token, get_current_user, verify_google_token
from BE.user_store import upsert_user
from BE.config import _parse_comma_separated, settings
from BE.logger import redact_url, setup_logger

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
) -> tuple[str, list[dict], list[str]]:
    """Process file attachments and return (augmented_prompt, images_list, warnings).

    Only image files are processed (kept as multimodal data URLs).
    Non-image files (text, PDF, etc.) are silently skipped.
    """
    text_parts: list[str] = []
    images: list[dict] = []

    for f in files:
        mime = f.type or ""

        if mime.startswith("image/"):
            images.append({"url": f.content})
            text_parts.append(f"[Attached image: {f.name}]")

    augmented = message
    if not message.strip() and text_parts:
        augmented = (
            "\n\n".join(text_parts)
            + "\n\nThe user uploaded the above file(s) without a message."
            " Please review and summarize the content."
        )
    elif text_parts:
        augmented = "\n\n".join(text_parts) + "\n\n" + message

    return augmented, images, []


def process_files(
    message: str, files: list[FileAttachment] | None
) -> tuple[str, list[dict], list[str]]:
    """Validate file sizes and build augmented prompt.

    Returns (prompt, images, warnings).
    Raises FileSizeLimitExceeded if total size exceeds MAX_TOTAL_FILE_SIZE.
    """
    if not files:
        return message, [], []
    total_size = sum(f.size for f in files)
    if total_size > MAX_TOTAL_FILE_SIZE:
        raise FileSizeLimitExceeded()
    prompt, images, warnings = build_prompt_with_files(message, files)
    logger.info("Augmented prompt length: %d chars", len(prompt))
    return prompt, images, warnings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
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
        logger.info("  Redis:      %s", settings.REDIS_URL)
    if settings.POSTGRES_ENABLED:
        logger.info("  PostgreSQL: %s", redact_url(settings.POSTGRES_URL))
    logger.info("=" * 60)

    yield
    logger.info("Application shutdown")


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
        prompt, images, file_warnings = process_files(body.message, body.files)
    except FileSizeLimitExceeded:
        return JSONResponse(
            status_code=413,
            content={"detail": "Total file size exceeds 20MB limit"},
        )

    agent = request.app.state.general_agent
    response = agent.invoke(prompt, session_id=body.session_id, images=images or None, user_id=user.id)
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
        prompt, images, file_warnings = process_files(body.message, body.files)
    except FileSizeLimitExceeded:
        return JSONResponse(
            status_code=413,
            content={"detail": "Total file size exceeds 20MB limit"},
        )

    agent = request.app.state.general_agent

    def generate():
        for warn in file_warnings:
            yield f"data: {json.dumps({'type': 'status', 'content': warn})}\n\n"
        for event in agent.stream(
            prompt, session_id=body.session_id, images=images or None, user_id=user.id
        ):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"
        logger.info("POST /chat/stream complete (session_id=%s)", body.session_id)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/history")
async def get_history(
    request: Request,
    session_id: str = Query(min_length=1, max_length=128, pattern=SESSION_ID_PATTERN),
    user: UserInfo = Depends(get_current_user),
):
    """Retrieve conversation history for a session."""
    logger.info("GET /history (session_id=%s)", session_id)
    agent = request.app.state.general_agent
    history = agent.get_history(session_id=session_id, user_id=user.id)
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
    agent.clear_history(session_id=session_id, user_id=user.id)
    return {"status": "cleared"}


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
    session_id: str,
    store: PostgresArchiveStore = Depends(get_archive_store),
    user: UserInfo = Depends(get_current_user),
):
    """Get archived messages for a session."""
    messages = await store.get_messages(session_id, user_id=user.id)
    return {"session_id": session_id, "messages": messages}


@app.delete("/archive/sessions/{session_id}")
async def delete_archived_session(
    session_id: str,
    store: PostgresArchiveStore = Depends(get_archive_store),
    user: UserInfo = Depends(get_current_user),
):
    """Delete an archived session."""
    deleted = await store.delete_session(session_id, user_id=user.id)
    if not deleted:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})
    return {"status": "deleted"}
