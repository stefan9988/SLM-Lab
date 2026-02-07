"""Tests for session store implementations."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from BE.session_store import (
    InMemoryStore,
    RedisStore,
    create_store,
    warm_session_from_archive,
    _msg_to_dict,
    _dict_to_message,
    _history_entry_from_dict,
)

# --- Helper fixtures ---


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def run(event_loop):
    return event_loop.run_until_complete


@pytest.fixture
def in_memory_store():
    return InMemoryStore()


@pytest.fixture
def sample_messages():
    return [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!", additional_kwargs={"thinking": "Let me think"}),
    ]


# --- _msg_to_dict / _dict_to_message round-trip ---


class TestMessageSerialization:
    def test_human_message_round_trip(self):
        msg = HumanMessage(content="test")
        d = _msg_to_dict(msg, model="llama3.1:8b", provider="ollama")
        assert d["type"] == "human"
        assert d["content"] == "test"
        assert d["model"] == "llama3.1:8b"
        assert d["provider"] == "ollama"
        assert d["timestamp"]  # non-empty
        restored = _dict_to_message(d)
        assert isinstance(restored, HumanMessage)
        assert restored.content == "test"

    def test_ai_message_with_thinking(self):
        msg = AIMessage(content="answer", additional_kwargs={"thinking": "reason"})
        d = _msg_to_dict(msg)
        assert d["thinking"] == "reason"
        assert "thinking" not in d["additional_kwargs"]
        restored = _dict_to_message(d)
        assert isinstance(restored, AIMessage)
        assert restored.additional_kwargs["thinking"] == "reason"

    def test_unknown_type_returns_none(self):
        d = {"type": "tool", "content": "x", "thinking": None, "additional_kwargs": {}}
        assert _dict_to_message(d) is None


class TestHistoryEntryFromDict:
    def test_human_entry(self):
        d = {"type": "human", "content": "hi", "thinking": None}
        entry = _history_entry_from_dict(d)
        assert entry == {"role": "human", "content": "hi"}

    def test_ai_entry_with_thinking(self):
        d = {"type": "ai", "content": "reply", "thinking": "thought"}
        entry = _history_entry_from_dict(d)
        assert entry == {"role": "ai", "content": "reply", "thinking": "thought"}

    def test_multimodal_content_flattened(self):
        d = {
            "type": "human",
            "content": [
                {"type": "text", "text": "describe"},
                {"type": "image_url", "image_url": {"url": "data:..."}},
            ],
            "thinking": None,
        }
        entry = _history_entry_from_dict(d)
        assert entry["content"] == "describe"

    def test_tool_type_skipped(self):
        d = {"type": "tool", "content": "result", "thinking": None}
        assert _history_entry_from_dict(d) is None


# --- InMemoryStore ---


class TestInMemoryStore:
    def test_empty_session(self, run, in_memory_store):
        assert run(in_memory_store.get_messages("none", user_id="u1")) == []
        assert run(in_memory_store.get_history_dicts("none", user_id="u1")) == []

    def test_save_and_retrieve(self, run, in_memory_store, sample_messages):
        run(in_memory_store.save_messages("s1", sample_messages, "model", "provider", user_id="u1"))
        msgs = run(in_memory_store.get_messages("s1", user_id="u1"))
        assert len(msgs) == 2
        assert isinstance(msgs[0], HumanMessage)
        assert isinstance(msgs[1], AIMessage)

    def test_save_triggers_archive_to_postgres(self, run, in_memory_store, sample_messages):
        """save_messages calls _archive_to_postgres for PostgreSQL persistence."""
        with patch("BE.session_store._archive_to_postgres") as mock_archive:
            run(in_memory_store.save_messages("s1", sample_messages, "model", "prov", user_id="u1"))
            mock_archive.assert_called_once()
            args = mock_archive.call_args
            assert args[0][0] == "s1"  # session_id
            assert len(args[0][1]) == 2  # dicts
            assert args[0][2] == "model"
            assert args[0][3] == "prov"
            assert args[0][4] == "u1"  # user_id

    def test_get_history_dicts(self, run, in_memory_store, sample_messages):
        run(in_memory_store.save_messages("s1", sample_messages, user_id="u1"))
        history = run(in_memory_store.get_history_dicts("s1", user_id="u1"))
        assert len(history) == 2
        assert history[0]["role"] == "human"
        assert history[1]["thinking"] == "Let me think"

    def test_clear(self, run, in_memory_store, sample_messages):
        run(in_memory_store.save_messages("s1", sample_messages, user_id="u1"))
        run(in_memory_store.clear("s1", user_id="u1"))
        assert run(in_memory_store.get_messages("s1", user_id="u1")) == []

    def test_clear_nonexistent_no_error(self, run, in_memory_store):
        run(in_memory_store.clear("nope", user_id="u1"))  # should not raise

    def test_user_isolation(self, run, in_memory_store, sample_messages):
        """Same session_id, different user_ids can't see each other's data."""
        run(in_memory_store.save_messages("s1", sample_messages, user_id="user-a"))
        assert run(in_memory_store.get_messages("s1", user_id="user-a")) != []
        assert run(in_memory_store.get_messages("s1", user_id="user-b")) == []
        assert run(in_memory_store.get_history_dicts("s1", user_id="user-b")) == []

    def test_save_skip_archive_does_not_call_postgres(self, run, in_memory_store, sample_messages):
        """save_messages with _skip_archive=True does not call _archive_to_postgres."""
        with patch("BE.session_store._archive_to_postgres") as mock_archive:
            run(in_memory_store.save_messages(
                "s1", sample_messages, "model", "prov", user_id="u1", _skip_archive=True,
            ))
            mock_archive.assert_not_called()
        # Messages should still be stored in memory
        assert len(run(in_memory_store.get_messages("s1", user_id="u1"))) == 2


# --- RedisStore (mocked) ---


class TestRedisStore:
    @pytest.fixture
    def mock_redis(self):
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        with patch("BE.session_store.aioredis.from_url", return_value=mock_client):
            store = RedisStore.__new__(RedisStore)
            store._redis = mock_client
            store._ttl_seconds = 30 * 86400
            yield store, mock_client

    def test_get_messages_empty(self, run, mock_redis):
        store, client = mock_redis
        client.lrange.return_value = []
        assert run(store.get_messages("s1", user_id="u1")) == []
        client.lrange.assert_called_once_with("session:u1:s1:messages", 0, -1)

    def test_get_messages_deserializes(self, run, mock_redis):
        store, client = mock_redis
        client.lrange.return_value = [
            json.dumps(
                {
                    "type": "human",
                    "content": "hi",
                    "thinking": None,
                    "additional_kwargs": {},
                }
            ),
            json.dumps(
                {
                    "type": "ai",
                    "content": "hello",
                    "thinking": None,
                    "additional_kwargs": {},
                }
            ),
        ]
        msgs = run(store.get_messages("s1", user_id="u1"))
        assert len(msgs) == 2
        assert isinstance(msgs[0], HumanMessage)
        assert isinstance(msgs[1], AIMessage)

    def test_save_messages_uses_pipeline(self, run, mock_redis, sample_messages):
        store, client = mock_redis
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock()
        client.pipeline = MagicMock(return_value=mock_pipe)

        run(store.save_messages("s1", sample_messages, "model", "ollama", user_id="u1"))

        client.pipeline.assert_called_once_with(transaction=True)
        mock_pipe.delete.assert_called_once_with("session:u1:s1:messages")
        assert mock_pipe.rpush.call_count == 2
        mock_pipe.hsetnx.assert_called_once()
        mock_pipe.hset.assert_called_once()
        assert mock_pipe.expire.call_count == 2
        mock_pipe.execute.assert_called_once()

    def test_clear_deletes_both_keys(self, run, mock_redis):
        store, client = mock_redis
        run(store.clear("s1", user_id="u1"))
        client.delete.assert_called_once_with(
            "session:u1:s1:meta", "session:u1:s1:messages"
        )

    def test_get_history_dicts(self, run, mock_redis):
        store, client = mock_redis
        client.lrange.return_value = [
            json.dumps({"type": "human", "content": "q", "thinking": None}),
            json.dumps({"type": "ai", "content": "a", "thinking": "t"}),
        ]
        history = run(store.get_history_dicts("s1", user_id="u1"))
        assert len(history) == 2
        assert history[0] == {"role": "human", "content": "q"}
        assert history[1] == {"role": "ai", "content": "a", "thinking": "t"}

    def test_redis_key_includes_user_id(self, mock_redis):
        store, client = mock_redis
        assert store._meta_key("sess1", "uid1") == "session:uid1:sess1:meta"
        assert store._messages_key("sess1", "uid1") == "session:uid1:sess1:messages"


# --- create_store factory ---


class TestCreateStore:
    @patch("BE.config.settings")
    def test_disabled_returns_in_memory(self, mock_settings):
        mock_settings.REDIS_ENABLED = False
        store = create_store()
        assert isinstance(store, InMemoryStore)

    @patch("BE.session_store.RedisStore")
    @patch("BE.config.settings")
    def test_enabled_returns_redis(self, mock_settings, mock_redis_cls):
        mock_settings.REDIS_ENABLED = True
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_SESSION_TTL_DAYS = 30
        mock_redis_cls.return_value = MagicMock(spec=RedisStore)
        store = create_store()
        mock_redis_cls.assert_called_once_with(
            redis_url="redis://localhost:6379/0", ttl_days=30
        )

    @patch("BE.session_store.RedisStore", side_effect=ConnectionError("refused"))
    @patch("BE.config.settings")
    def test_fallback_on_connection_error(self, mock_settings, mock_redis_cls):
        mock_settings.REDIS_ENABLED = True
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.REDIS_SESSION_TTL_DAYS = 30
        store = create_store()
        assert isinstance(store, InMemoryStore)


# --- warm_session_from_archive ---


class TestWarmSessionFromArchive:
    def test_skips_when_store_already_has_messages(self, run):
        store = InMemoryStore()
        run(store.save_messages("s1", [HumanMessage(content="hi")], user_id="u1"))

        mock_archive = AsyncMock()
        with patch("BE.archive_store.create_store", return_value=mock_archive):
            run(warm_session_from_archive(store, "s1", user_id="u1"))
        mock_archive.get_messages.assert_not_called()

    def test_skips_when_archive_store_unavailable(self, run):
        store = InMemoryStore()
        with patch("BE.archive_store.create_store", return_value=None):
            run(warm_session_from_archive(store, "s1", user_id="u1"))
        assert run(store.get_messages("s1", user_id="u1")) == []

    def test_skips_when_archive_has_no_messages(self, run):
        store = InMemoryStore()
        mock_archive = AsyncMock()
        mock_archive.get_messages.return_value = []
        with patch("BE.archive_store.create_store", return_value=mock_archive):
            run(warm_session_from_archive(store, "s1", user_id="u1"))
        assert run(store.get_messages("s1", user_id="u1")) == []

    def test_loads_and_converts_archive_messages(self, run):
        store = InMemoryStore()
        mock_archive = AsyncMock()
        mock_archive.get_messages.return_value = [
            {
                "type": "human",
                "content": "Hello",
                "thinking": None,
                "model": None,
                "provider": None,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "additional_kwargs": None,
            },
            {
                "type": "ai",
                "content": "Hi there!",
                "thinking": "Let me think...",
                "model": "gpt-4",
                "provider": "openai",
                "timestamp": "2025-01-01T00:00:01+00:00",
                "additional_kwargs": {},
            },
        ]
        with patch("BE.archive_store.create_store", return_value=mock_archive):
            run(warm_session_from_archive(store, "s1", user_id="u1"))

        messages = run(store.get_messages("s1", user_id="u1"))
        assert len(messages) == 2
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "Hello"
        assert isinstance(messages[1], AIMessage)
        assert messages[1].content == "Hi there!"
        assert messages[1].additional_kwargs.get("thinking") == "Let me think..."

    def test_warm_up_does_not_re_archive(self, run):
        """warm_session_from_archive must not re-archive data back to PostgreSQL."""
        store = InMemoryStore()
        mock_archive = AsyncMock()
        mock_archive.get_messages.return_value = [
            {
                "type": "human",
                "content": "Hello",
                "thinking": None,
                "model": "gpt-4",
                "provider": "openai",
                "timestamp": "2025-01-01T00:00:00+00:00",
                "additional_kwargs": {},
            },
        ]
        with patch("BE.archive_store.create_store", return_value=mock_archive), \
             patch("BE.session_store._archive_to_postgres") as mock_pg:
            run(warm_session_from_archive(store, "s1", user_id="u1"))
            mock_pg.assert_not_called()

        # Messages should still be loaded into memory
        assert len(run(store.get_messages("s1", user_id="u1"))) == 1

    def test_preserves_user_isolation(self, run):
        store = InMemoryStore()
        mock_archive = AsyncMock()
        mock_archive.get_messages.return_value = [
            {
                "type": "human",
                "content": "user1 message",
                "thinking": None,
                "model": None,
                "provider": None,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "additional_kwargs": None,
            },
        ]
        with patch("BE.archive_store.create_store", return_value=mock_archive):
            run(warm_session_from_archive(store, "s1", user_id="u1"))

        assert len(run(store.get_messages("s1", user_id="u1"))) == 1
        assert len(run(store.get_messages("s1", user_id="u2"))) == 0
