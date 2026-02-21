"""Session store abstraction for conversation history persistence."""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import redis.asyncio as aioredis
import redis.exceptions as redis_exceptions

from BE.async_utils import schedule_background_task
from BE.logger import redact_url, setup_logger

logger = setup_logger(__name__)

__all__ = ["SessionStore", "InMemoryStore", "RedisStore", "create_store"]


class SessionStore(ABC):
    """Abstract base class for session storage backends."""

    @abstractmethod
    async def get_messages(self, session_id: str, user_id: str = "") -> list:
        """Retrieve LangChain message objects for a session."""

    @abstractmethod
    async def save_messages(
        self,
        session_id: str,
        messages: list,
        model: str = "",
        provider: str = "",
        user_id: str = "",
        _skip_archive: bool = False,
    ) -> None:
        """Persist the full message list for a session."""

    @abstractmethod
    async def clear(self, session_id: str, user_id: str = "") -> None:
        """Delete all data for a session."""

    @abstractmethod
    async def get_history_dicts(self, session_id: str, user_id: str = "") -> list[dict]:
        """Return conversation history as serializable dicts."""


def _msg_to_dict(msg, model: str = "", provider: str = "") -> dict:
    """Convert a LangChain message to a serializable dict."""
    thinking = (
        msg.additional_kwargs.get("thinking")
        if hasattr(msg, "additional_kwargs")
        else None
    )
    additional = {}
    if hasattr(msg, "additional_kwargs"):
        additional = {k: v for k, v in msg.additional_kwargs.items() if k != "thinking"}
    return {
        "type": msg.type,
        "content": (
            json.dumps(msg.content) if isinstance(msg.content, list) else msg.content
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "provider": provider,
        "thinking": thinking,
        "additional_kwargs": additional,
    }


def _dict_to_message(d: dict):
    """Convert a stored dict back to a LangChain message."""
    from langchain_core.messages import AIMessage, HumanMessage

    content = d["content"]
    if isinstance(content, str) and content.startswith("["):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and all(
                isinstance(block, dict) and block.get("type") in ("text", "image_url")
                for block in parsed
            ):
                content = parsed
        except (json.JSONDecodeError, ValueError):
            pass
    additional_kwargs = d.get("additional_kwargs") or {}
    if d.get("thinking"):
        additional_kwargs["thinking"] = d["thinking"]

    if d["type"] == "human":
        return HumanMessage(content=content, additional_kwargs=additional_kwargs)
    elif d["type"] == "ai":
        return AIMessage(content=content, additional_kwargs=additional_kwargs)
    return None


_ATTACHED_FILE_RE = None


def _get_attached_file_re():
    global _ATTACHED_FILE_RE
    if _ATTACHED_FILE_RE is None:
        import re

        _ATTACHED_FILE_RE = re.compile(r"\[Attached (?:image|file): [^\]]+\]\n*")
    return _ATTACHED_FILE_RE


def _history_entry_from_dict(d: dict) -> dict | None:
    """Convert a stored dict to a history entry for the API."""
    if d["type"] not in ("human", "ai"):
        return None
    content = d["content"]
    if isinstance(content, str) and content.startswith("["):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and all(
                isinstance(block, dict) and block.get("type") in ("text", "image_url")
                for block in parsed
            ):
                content = " ".join(
                    block.get("text", "")
                    for block in parsed
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            # else: non-content-block arrays (e.g. extraction results) stay as string
        except (json.JSONDecodeError, ValueError):
            pass
    if isinstance(content, list):
        content = " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    additional = d.get("additional_kwargs") or {}
    file_attachments = additional.get("file_attachments")

    if file_attachments and isinstance(content, str):
        content = _get_attached_file_re().sub("", content).strip()

    entry: dict = {"role": d["type"], "content": content}
    if file_attachments:
        entry["files"] = [
            {k: v for k, v in f.items() if k in ("name", "type", "file_id")}
            for f in file_attachments
        ]
    if d.get("thinking"):
        entry["thinking"] = d["thinking"]
    tools_used = additional.get("tools_used")
    if tools_used:
        entry["tools_used"] = tools_used
    return entry


def _get_archive_settings() -> tuple[int, float, float]:
    """Get archive retry settings from config."""
    from BE.config import settings

    return (
        settings.ARCHIVE_MAX_RETRIES,
        settings.ARCHIVE_RETRY_DELAY,
        settings.ARCHIVE_TIMEOUT,
    )


def _archive_to_postgres(
    session_id: str,
    dicts: list[dict],
    model: str,
    provider: str,
    user_id: str = "",
) -> None:
    """Best-effort async archive to PostgreSQL."""
    from BE.archive_store import create_store

    store = create_store()
    if store is None:
        return

    max_retries, retry_delay, timeout = _get_archive_settings()

    async def _do_archive():
        await store.save_messages(
            session_id,
            dicts,
            {"model": model, "provider": provider},
            user_id=user_id,
        )

    schedule_background_task(
        _do_archive,
        max_retries=max_retries,
        retry_delay=retry_delay,
        timeout=timeout,
        task_name=f"archive_save:{session_id}",
    )


def _clear_archive(session_id: str, user_id: str = "") -> None:
    """Best-effort async archive deletion from PostgreSQL."""
    from BE.archive_store import create_store

    store = create_store()
    if store is None:
        return

    max_retries, retry_delay, timeout = _get_archive_settings()

    async def _do_delete():
        await store.delete_session(session_id, user_id=user_id)
        logger.debug("Cleared archive for session %s", session_id)

    schedule_background_task(
        _do_delete,
        max_retries=max_retries,
        retry_delay=retry_delay,
        timeout=timeout,
        task_name=f"archive_clear:{session_id}",
    )


class InMemoryStore(SessionStore):
    """In-memory session store (no persistence across restarts)."""

    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str], list[dict]] = {}

    async def get_messages(self, session_id: str, user_id: str = "") -> list:
        dicts = self._sessions.get((user_id, session_id), [])
        msgs = []
        for d in dicts:
            m = _dict_to_message(d)
            if m is not None:
                msgs.append(m)
        return msgs

    async def save_messages(
        self,
        session_id: str,
        messages: list,
        model: str = "",
        provider: str = "",
        user_id: str = "",
        _skip_archive: bool = False,
    ) -> None:
        dicts = [_msg_to_dict(m, model, provider) for m in messages]
        self._sessions[(user_id, session_id)] = dicts
        if not _skip_archive:
            _archive_to_postgres(session_id, dicts, model, provider, user_id)

    async def clear(self, session_id: str, user_id: str = "") -> None:
        self._sessions.pop((user_id, session_id), None)
        _clear_archive(session_id, user_id=user_id)

    async def get_history_dicts(self, session_id: str, user_id: str = "") -> list[dict]:
        dicts = self._sessions.get((user_id, session_id), [])
        history = []
        for d in dicts:
            entry = _history_entry_from_dict(d)
            if entry:
                history.append(entry)
        return history


class RedisStore(SessionStore):
    """Redis-backed session store with per-message metadata."""

    def __init__(self, redis_url: str, ttl_days: int = 30) -> None:
        self._redis = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5.0,
            socket_timeout=5.0,
        )
        self._ttl_seconds = ttl_days * 86400
        logger.info("RedisStore connected to %s", redact_url(redis_url))

    def _meta_key(self, session_id: str, user_id: str = "") -> str:
        return f"session:{user_id}:{session_id}:meta"

    def _messages_key(self, session_id: str, user_id: str = "") -> str:
        return f"session:{user_id}:{session_id}:messages"

    async def _touch_ttl(self, pipe, session_id: str, user_id: str = "") -> None:
        pipe.expire(self._meta_key(session_id, user_id), self._ttl_seconds)
        pipe.expire(self._messages_key(session_id, user_id), self._ttl_seconds)

    async def get_messages(self, session_id: str, user_id: str = "") -> list:
        raw = await self._redis.lrange(self._messages_key(session_id, user_id), 0, -1)
        msgs = []
        for item in raw:
            d = json.loads(item)
            m = _dict_to_message(d)
            if m is not None:
                msgs.append(m)
        return msgs

    async def save_messages(
        self,
        session_id: str,
        messages: list,
        model: str = "",
        provider: str = "",
        user_id: str = "",
        _skip_archive: bool = False,
    ) -> None:
        meta_key = self._meta_key(session_id, user_id)
        msg_key = self._messages_key(session_id, user_id)
        now = datetime.now(timezone.utc).isoformat()

        dicts = [_msg_to_dict(m, model, provider) for m in messages]

        pipe = self._redis.pipeline(transaction=True)
        pipe.delete(msg_key)
        for d in dicts:
            pipe.rpush(msg_key, json.dumps(d))
        pipe.hsetnx(meta_key, "created_at", now)
        pipe.hset(
            meta_key,
            mapping={
                "updated_at": now,
                "model_name": model,
                "provider": provider,
            },
        )
        await self._touch_ttl(pipe, session_id, user_id)
        await pipe.execute()

        if not _skip_archive:
            _archive_to_postgres(session_id, dicts, model, provider, user_id)

    async def clear(self, session_id: str, user_id: str = "") -> None:
        await self._redis.delete(
            self._meta_key(session_id, user_id),
            self._messages_key(session_id, user_id),
        )
        _clear_archive(session_id, user_id=user_id)

    async def get_history_dicts(self, session_id: str, user_id: str = "") -> list[dict]:
        raw = await self._redis.lrange(self._messages_key(session_id, user_id), 0, -1)
        history = []
        for item in raw:
            d = json.loads(item)
            entry = _history_entry_from_dict(d)
            if entry:
                history.append(entry)
        return history


async def warm_session_from_archive(
    store: SessionStore,
    session_id: str,
    user_id: str = "",
) -> None:
    """If session store is empty for this session, load from PostgreSQL archive."""
    if await store.get_messages(session_id, user_id):
        return

    from BE.archive_store import create_store as create_archive_store

    archive = create_archive_store()
    if archive is None:
        return

    archive_dicts = await archive.get_messages(session_id, user_id=user_id)
    if not archive_dicts:
        return

    messages = []
    for d in archive_dicts:
        msg = _dict_to_message(d)
        if msg is not None:
            messages.append(msg)

    if messages:
        await store.save_messages(
            session_id, messages, user_id=user_id, _skip_archive=True
        )
        logger.info(
            "Warmed session %s from archive (%d messages)", session_id, len(messages)
        )


def create_store() -> SessionStore:
    """Create the appropriate session store based on configuration."""
    from BE.config import settings

    if not settings.REDIS_ENABLED:
        logger.info("Redis disabled, using InMemoryStore")
        return InMemoryStore()

    try:
        store = RedisStore(
            redis_url=settings.REDIS_URL,
            ttl_days=settings.REDIS_SESSION_TTL_DAYS,
        )
        return store
    except (
        redis_exceptions.ConnectionError,
        redis_exceptions.TimeoutError,
        OSError,
    ) as exc:
        logger.warning(
            "Failed to connect to Redis (%s), falling back to InMemoryStore",
            exc,
        )
        return InMemoryStore()
