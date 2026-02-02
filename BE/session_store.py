"""Session store abstraction for conversation history persistence."""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, List, Optional

from BE.logger import setup_logger

logger = setup_logger(__name__)


class SessionStore(ABC):
    """Abstract base class for session storage backends."""

    @abstractmethod
    def get_messages(self, session_id: str) -> List:
        """Retrieve LangChain message objects for a session."""

    @abstractmethod
    def save_messages(
        self,
        session_id: str,
        messages: List,
        model: str = "",
        provider: str = "",
    ) -> None:
        """Persist the full message list for a session."""

    @abstractmethod
    def clear(self, session_id: str) -> None:
        """Delete all data for a session."""

    @abstractmethod
    def get_history_dicts(self, session_id: str) -> List[dict]:
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
        "content": msg.content,
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
    additional_kwargs = d.get("additional_kwargs", {})
    if d.get("thinking"):
        additional_kwargs["thinking"] = d["thinking"]

    if d["type"] == "human":
        return HumanMessage(content=content)
    elif d["type"] == "ai":
        return AIMessage(content=content, additional_kwargs=additional_kwargs)
    return None


def _history_entry_from_dict(d: dict) -> Optional[dict]:
    """Convert a stored dict to a history entry for the API."""
    if d["type"] not in ("human", "ai"):
        return None
    content = d["content"]
    if isinstance(content, list):
        content = " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    entry: dict = {"role": d["type"], "content": content}
    if d.get("thinking"):
        entry["thinking"] = d["thinking"]
    return entry


class InMemoryStore(SessionStore):
    """In-memory session store (no persistence across restarts)."""

    def __init__(self) -> None:
        self._sessions: dict[str, List[dict]] = {}

    def get_messages(self, session_id: str) -> List:
        dicts = self._sessions.get(session_id, [])
        msgs = []
        for d in dicts:
            m = _dict_to_message(d)
            if m is not None:
                msgs.append(m)
        return msgs

    def save_messages(
        self,
        session_id: str,
        messages: List,
        model: str = "",
        provider: str = "",
    ) -> None:
        self._sessions[session_id] = [
            _msg_to_dict(m, model, provider) for m in messages
        ]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def get_history_dicts(self, session_id: str) -> List[dict]:
        dicts = self._sessions.get(session_id, [])
        history = []
        for d in dicts:
            entry = _history_entry_from_dict(d)
            if entry:
                history.append(entry)
        return history


class RedisStore(SessionStore):
    """Redis-backed session store with per-message metadata."""

    def __init__(self, redis_url: str, ttl_days: int = 30) -> None:
        import redis as redis_lib

        self._redis = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_days * 86400
        # Verify connectivity
        self._redis.ping()
        logger.info("RedisStore connected to %s", redis_url)

    def _meta_key(self, session_id: str) -> str:
        return f"session:{session_id}:meta"

    def _messages_key(self, session_id: str) -> str:
        return f"session:{session_id}:messages"

    def _touch_ttl(self, pipe, session_id: str) -> None:
        pipe.expire(self._meta_key(session_id), self._ttl_seconds)
        pipe.expire(self._messages_key(session_id), self._ttl_seconds)

    def get_messages(self, session_id: str) -> List:
        raw = self._redis.lrange(self._messages_key(session_id), 0, -1)
        msgs = []
        for item in raw:
            d = json.loads(item)
            m = _dict_to_message(d)
            if m is not None:
                msgs.append(m)
        return msgs

    def save_messages(
        self,
        session_id: str,
        messages: List,
        model: str = "",
        provider: str = "",
    ) -> None:
        meta_key = self._meta_key(session_id)
        msg_key = self._messages_key(session_id)
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
        self._touch_ttl(pipe, session_id)
        pipe.execute()

    def clear(self, session_id: str) -> None:
        self._redis.delete(
            self._meta_key(session_id),
            self._messages_key(session_id),
        )

    def get_history_dicts(self, session_id: str) -> List[dict]:
        raw = self._redis.lrange(self._messages_key(session_id), 0, -1)
        history = []
        for item in raw:
            d = json.loads(item)
            entry = _history_entry_from_dict(d)
            if entry:
                history.append(entry)
        return history


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
    except Exception as exc:
        logger.warning(
            "Failed to connect to Redis (%s), falling back to InMemoryStore",
            exc,
        )
        return InMemoryStore()
