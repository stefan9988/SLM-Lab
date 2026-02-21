"""Tests for BE.app FastAPI endpoints."""

import asyncio
import base64
import json
from unittest.mock import AsyncMock, patch

import pytest

from BE.app import (
    FileAttachment,
    build_prompt_with_files,
    process_files,
    get_archive_store,
)
from BE.auth import get_current_user


async def _async_gen(items):
    """Helper to create an async generator from a list."""
    for item in items:
        yield item


async def _async_gen_raising(items, exc):
    """Helper to create an async generator that raises after yielding items."""
    for item in items:
        yield item
    raise exc


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def run(event_loop):
    """Helper to run coroutines in the test event loop."""
    return event_loop.run_until_complete


# ── build_prompt_with_files unit tests ──────────────────────────────────────


class TestBuildPromptWithFiles:
    @patch("BE.app.save_file", new_callable=AsyncMock, return_value=None)
    def test_image_file_added_to_images(self, _mock_save, run):
        data_url = "data:image/png;base64,iVBOR"
        f = FileAttachment(name="pic.png", type="image/png", content=data_url, size=10)
        prompt, images, file_meta = run(
            build_prompt_with_files("describe", [f], user_id="u1")
        )
        assert len(images) == 1
        assert images[0]["url"] == data_url
        assert prompt.endswith("describe")
        assert file_meta == [{"name": "pic.png", "type": "image/png"}]

    @patch("BE.app.save_file", new_callable=AsyncMock, return_value=None)
    def test_no_files_returns_original_message(self, _mock_save, run):
        prompt, images, file_meta = run(
            build_prompt_with_files("hello", [], user_id="u1")
        )
        assert prompt == "hello"
        assert images == []
        assert file_meta == []

    @patch("BE.app.save_file", new_callable=AsyncMock, return_value="uuid-123")
    def test_non_image_file_is_saved_and_referenced(self, mock_save, run):
        """Non-image files should be saved to DB and referenced by file_id."""
        text_file = FileAttachment(
            name="data.csv",
            type="text/csv",
            content="data:text/csv;base64,YSxiLGMKMSwyLDM=",
            size=20,
        )
        pdf_file = FileAttachment(
            name="doc.pdf",
            type="application/pdf",
            content="data:application/pdf;base64,ZmFrZQ==",
            size=50,
        )
        prompt, images, file_meta = run(
            build_prompt_with_files(
                "summarize", [text_file, pdf_file], user_id="u1", session_id="s1"
            )
        )
        assert images == []
        assert "file_id: uuid-123" in prompt
        assert "[Attached file: data.csv" in prompt
        assert "[Attached file: doc.pdf" in prompt
        assert len(file_meta) == 2
        assert file_meta[0] == {
            "name": "data.csv",
            "type": "text/csv",
            "file_id": "uuid-123",
        }
        assert file_meta[1] == {
            "name": "doc.pdf",
            "type": "application/pdf",
            "file_id": "uuid-123",
        }
        assert mock_save.call_count == 2

    @patch("BE.app.save_file", new_callable=AsyncMock, return_value=None)
    def test_non_image_file_degradation(self, _mock_save, run):
        """When save_file returns None, file is referenced as 'content not stored'."""
        text_file = FileAttachment(
            name="data.csv",
            type="text/csv",
            content="data:text/csv;base64,YSxiLGMKMSwyLDM=",
            size=20,
        )
        prompt, images, file_meta = run(
            build_prompt_with_files("summarize", [text_file], user_id="u1")
        )
        assert "(content not stored)" in prompt
        assert file_meta == [{"name": "data.csv", "type": "text/csv"}]

    @patch("BE.app.save_file", new_callable=AsyncMock, return_value=None)
    def test_multiple_images_returns_metadata(self, _mock_save, run):
        f1 = FileAttachment(
            name="a.png", type="image/png", content="data:image/png;base64,x", size=10
        )
        f2 = FileAttachment(
            name="b.jpg", type="image/jpeg", content="data:image/jpeg;base64,y", size=20
        )
        prompt, images, file_meta = run(
            build_prompt_with_files("describe", [f1, f2], user_id="u1")
        )
        assert len(images) == 2
        assert len(file_meta) == 2
        assert file_meta[0] == {"name": "a.png", "type": "image/png"}
        assert file_meta[1] == {"name": "b.jpg", "type": "image/jpeg"}

    @patch("BE.app.save_file", new_callable=AsyncMock, return_value="uuid-abc")
    def test_mixed_image_and_text_files(self, mock_save, run):
        """Images go to multimodal, text files get saved to DB."""
        img = FileAttachment(
            name="pic.png", type="image/png", content="data:image/png;base64,x", size=10
        )
        txt = FileAttachment(
            name="notes.txt",
            type="text/plain",
            content="data:text/plain;base64,aGVsbG8=",
            size=5,
        )
        prompt, images, file_meta = run(
            build_prompt_with_files("review", [img, txt], user_id="u1", session_id="s1")
        )
        assert len(images) == 1
        assert images[0]["url"] == "data:image/png;base64,x"
        assert "[Attached image: pic.png]" in prompt
        assert "[Attached file: notes.txt (file_id: uuid-abc)]" in prompt
        assert file_meta[0] == {"name": "pic.png", "type": "image/png"}
        assert file_meta[1] == {
            "name": "notes.txt",
            "type": "text/plain",
            "file_id": "uuid-abc",
        }
        mock_save.assert_called_once()


class TestProcessFiles:
    def test_no_files_returns_empty_metadata(self, run):
        prompt, images, file_meta = run(process_files("hello", None, user_id="u1"))
        assert prompt == "hello"
        assert images == []
        assert file_meta == []

    @patch("BE.app.save_file", new_callable=AsyncMock, return_value=None)
    def test_image_files_return_metadata(self, _mock_save, run):
        f = FileAttachment(
            name="pic.png", type="image/png", content="data:image/png;base64,x", size=10
        )
        prompt, images, file_meta = run(process_files("describe", [f], user_id="u1"))
        assert len(images) == 1
        assert file_meta == [{"name": "pic.png", "type": "image/png"}]

    @patch("BE.app.save_file", new_callable=AsyncMock, return_value="uuid-456")
    def test_text_file_saved_and_referenced(self, mock_save, run):
        raw = b"a,b,c\n1,2,3"
        data_url = f"data:text/csv;base64,{base64.b64encode(raw).decode()}"
        f = FileAttachment(
            name="data.csv", type="text/csv", content=data_url, size=len(raw)
        )
        prompt, images, file_meta = run(
            process_files("analyze", [f], user_id="u1", session_id="s1")
        )
        assert images == []
        assert "file_id: uuid-456" in prompt
        assert file_meta == [
            {"name": "data.csv", "type": "text/csv", "file_id": "uuid-456"}
        ]
        mock_save.assert_called_once_with(
            original_name="data.csv",
            mime_type="text/csv",
            data_url_content=data_url,
            size_bytes=len(raw),
            user_id="u1",
            session_id="s1",
        )


# ── Endpoint tests with file attachments ────────────────────────────────────


class TestChatWithFiles:
    def test_file_size_limit_returns_413(self, client):
        # Use multiple files whose declared sizes sum to > 20MB total
        resp = client.post(
            "/chat",
            json={
                "message": "hi",
                "session_id": "s1",
                "files": [
                    {
                        "name": "big1.bin",
                        "type": "application/octet-stream",
                        "content": "data:application/octet-stream;base64,eA==",
                        "size": 15_000_000,
                    },
                    {
                        "name": "big2.bin",
                        "type": "application/octet-stream",
                        "content": "data:application/octet-stream;base64,eA==",
                        "size": 10_000_001,
                    },
                ],
            },
        )
        assert resp.status_code == 413

    def test_file_size_field_validation_returns_422(self, client):
        """Field-level size constraint (le=20_000_000) rejects oversized declarations."""
        resp = client.post(
            "/chat",
            json={
                "message": "hi",
                "session_id": "s1",
                "files": [
                    {
                        "name": "huge.bin",
                        "type": "application/octet-stream",
                        "content": "data:application/octet-stream;base64,eA==",
                        "size": 25_000_000,
                    }
                ],
            },
        )
        assert resp.status_code == 422


class TestChatEndpoint:
    def test_post_chat_200(self, client, mock_agent):
        resp = client.post("/chat", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 200
        assert resp.json() == {"response": "mock response"}
        mock_agent.invoke.assert_called_once_with(
            "hi",
            session_id="s1",
            images=None,
            file_attachments=None,
            user_id="test-user-id",
        )

    def test_post_chat_422_missing_fields(self, client):
        resp = client.post("/chat", json={})
        assert resp.status_code == 422


class TestChatStreamEndpoint:
    def test_returns_sse_with_done(self, client, mock_agent):
        mock_agent.stream.return_value = _async_gen(
            [
                {"type": "token", "content": "hi"},
            ]
        )
        resp = client.post("/chat/stream", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 200
        lines = [l for l in resp.text.strip().split("\n\n") if l.startswith("data:")]
        assert len(lines) == 2  # one token event + [DONE]
        assert lines[-1] == "data: [DONE]"
        payload = json.loads(lines[0].removeprefix("data: "))
        assert payload == {"type": "token", "content": "hi"}

    def test_stream_agent_error_yields_error_event_then_done(self, client, mock_agent):
        mock_agent.stream.return_value = _async_gen_raising(
            [{"type": "token", "content": "partial"}],
            RuntimeError("model 'llama3.1:8b' not found"),
        )
        resp = client.post("/chat/stream", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 200
        lines = [l for l in resp.text.strip().split("\n\n") if l.startswith("data:")]
        assert lines[-1] == "data: [DONE]"
        error_lines = [l for l in lines if '"error"' in l]
        assert len(error_lines) == 1
        payload = json.loads(error_lines[0].removeprefix("data: "))
        assert payload["type"] == "error"
        assert payload["content"].startswith("LLM error:")
        assert "llama3.1:8b" in payload["content"]

    def test_stream_agent_immediate_error_yields_error_then_done(
        self, client, mock_agent
    ):
        mock_agent.stream.return_value = _async_gen_raising(
            [], RuntimeError("connection refused")
        )
        resp = client.post("/chat/stream", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 200
        lines = [l for l in resp.text.strip().split("\n\n") if l.startswith("data:")]
        assert lines[-1] == "data: [DONE]"
        assert len(lines) == 2  # error + DONE
        payload = json.loads(lines[0].removeprefix("data: "))
        assert payload["type"] == "error"


class TestHistoryEndpoints:
    def test_get_history_200(self, client, mock_agent):
        mock_agent.get_history.return_value = [{"role": "human", "content": "hi"}]
        resp = client.get("/history", params={"session_id": "s1"})
        assert resp.status_code == 200
        assert resp.json() == {"history": [{"role": "human", "content": "hi"}]}
        mock_agent.get_history.assert_called_once_with(
            session_id="s1", user_id="test-user-id"
        )

    def test_get_history_422_missing_session_id(self, client):
        resp = client.get("/history")
        assert resp.status_code == 422

    def test_delete_history_200(self, client, mock_agent):
        resp = client.delete("/history", params={"session_id": "s1"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "cleared"}
        mock_agent.clear_history.assert_called_once_with(
            session_id="s1", user_id="test-user-id"
        )


class TestExceptionHandler:
    def test_invoke_raises_returns_500(self, client, mock_agent):
        mock_agent.invoke.side_effect = RuntimeError("boom")
        resp = client.post("/chat", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 500
        assert "Internal server error" in resp.json()["detail"]


# ── Google Auth endpoint tests ──────────────────────────────────────────────


class TestGoogleAuthEndpoint:
    @patch("BE.app.upsert_user")
    @patch("BE.app.verify_google_token")
    def test_valid_google_token_returns_200(self, mock_verify, mock_upsert, client):
        from BE.auth import UserInfo

        mock_verify.return_value = UserInfo(
            email="user@test.com",
            name="User",
            picture="pic.jpg",
            google_sub="gsub-1",
        )
        mock_upsert.return_value = "uid-abc"
        resp = client.post("/auth/google", json={"token": "valid-google-token"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "user@test.com"
        assert data["user"]["id"] == "uid-abc"
        assert data["user"]["google_sub"] == "gsub-1"
        mock_upsert.assert_called_once_with(
            email="user@test.com",
            name="User",
            picture="pic.jpg",
            google_sub="gsub-1",
        )

    @patch("BE.app.verify_google_token")
    def test_invalid_google_token_returns_401(self, mock_verify, client):
        from fastapi import HTTPException

        mock_verify.side_effect = HTTPException(
            status_code=401, detail="Invalid Google token"
        )
        resp = client.post("/auth/google", json={"token": "bad-token"})
        assert resp.status_code == 401

    def test_missing_token_field_returns_422(self, client):
        resp = client.post("/auth/google", json={})
        assert resp.status_code == 422

    def test_protected_route_without_auth_returns_422(self, mock_agent):
        """Without the dependency override, protected routes require auth."""
        from fastapi.testclient import TestClient
        from BE.app import app

        app.state.general_agent = mock_agent
        # Clear overrides so auth is actually enforced
        app.dependency_overrides.pop(get_current_user, None)
        unauthed_client = TestClient(app, raise_server_exceptions=False)
        resp = unauthed_client.post("/chat", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 422  # missing Authorization header


# ── GET /general-agent/model endpoint tests ──────────────────────────────────


class TestGetGeneralAgentModel:
    def test_returns_provider_and_model_name(self, client, mock_agent):
        mock_agent._provider = "ollama"
        mock_agent._model_name = "llama3.1:8b"
        resp = client.get("/general-agent/model")
        assert resp.status_code == 200
        assert resp.json() == {"provider": "ollama", "model_name": "llama3.1:8b"}

    def test_returns_anthropic_model(self, client, mock_agent):
        mock_agent._provider = "anthropic"
        mock_agent._model_name = "claude-sonnet-4-6"
        resp = client.get("/general-agent/model")
        assert resp.status_code == 200
        assert resp.json() == {
            "provider": "anthropic",
            "model_name": "claude-sonnet-4-6",
        }


# ── PUT /general-agent/model endpoint tests ──────────────────────────────────


class TestUpdateGeneralAgentModel:
    @patch("BE.app.init_agent")
    def test_updates_agent_and_returns_new_model(
        self, mock_init_agent, client, mock_agent
    ):
        from unittest.mock import MagicMock
        from AI.agents.base import Agent

        new_mock_agent = MagicMock(spec=Agent)
        new_mock_agent._provider = "anthropic"
        new_mock_agent._model_name = "claude-sonnet-4-6"
        mock_init_agent.return_value = new_mock_agent

        mock_agent._provider = "ollama"
        mock_agent._model_name = "llama3.1:8b"
        # Must set _store before reading it (spec=Agent doesn't auto-create instance attrs)
        mock_agent._store = MagicMock()
        old_store = mock_agent._store

        resp = client.put(
            "/general-agent/model",
            json={"provider": "anthropic", "model_name": "claude-sonnet-4-6"},
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "provider": "anthropic",
            "model_name": "claude-sonnet-4-6",
        }

        mock_init_agent.assert_called_once()
        call_kwargs = mock_init_agent.call_args.kwargs
        assert call_kwargs["provider"] == "anthropic"
        assert call_kwargs["model_name"] == "claude-sonnet-4-6"
        assert call_kwargs["maintain_history"] is True

        # Verify old store was transferred to the new agent
        assert new_mock_agent._store is old_store

    @patch("BE.app.init_agent")
    def test_preserves_session_store(self, mock_init_agent, client, mock_agent):
        from unittest.mock import MagicMock, sentinel
        from AI.agents.base import Agent

        new_mock_agent = MagicMock(spec=Agent)
        new_mock_agent._provider = "openrouter"
        new_mock_agent._model_name = "openai/gpt-4o"
        mock_init_agent.return_value = new_mock_agent

        # Set a specific sentinel store to track transfer
        mock_agent._store = sentinel.old_store

        client.put(
            "/general-agent/model",
            json={"provider": "openrouter", "model_name": "openai/gpt-4o"},
        )

        assert new_mock_agent._store is sentinel.old_store


# ── GET /document-agent/model endpoint tests ──────────────────────────────────


class TestGetDocumentAgentModel:
    def test_returns_provider_and_model_name(self, client, mock_document_agent):
        mock_document_agent._provider = "ollama"
        mock_document_agent._model_name = "llama3.1:8b"
        resp = client.get("/document-agent/model")
        assert resp.status_code == 200
        assert resp.json() == {"provider": "ollama", "model_name": "llama3.1:8b"}

    def test_returns_anthropic_model(self, client, mock_document_agent):
        mock_document_agent._provider = "anthropic"
        mock_document_agent._model_name = "claude-sonnet-4-6"
        resp = client.get("/document-agent/model")
        assert resp.status_code == 200
        assert resp.json() == {
            "provider": "anthropic",
            "model_name": "claude-sonnet-4-6",
        }


# ── PUT /document-agent/model endpoint tests ──────────────────────────────────


class TestUpdateDocumentAgentModel:
    @patch("BE.app.init_agent")
    def test_updates_agent_and_returns_new_model(
        self, mock_init_agent, client, mock_document_agent
    ):
        from unittest.mock import MagicMock
        from AI.agents.base import Agent

        new_mock_agent = MagicMock(spec=Agent)
        new_mock_agent._provider = "anthropic"
        new_mock_agent._model_name = "claude-sonnet-4-6"
        new_mock_agent._store = MagicMock()
        mock_init_agent.return_value = new_mock_agent
        mock_document_agent._store = MagicMock()

        resp = client.put(
            "/document-agent/model",
            json={"provider": "anthropic", "model_name": "claude-sonnet-4-6"},
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "provider": "anthropic",
            "model_name": "claude-sonnet-4-6",
        }

    @patch("BE.app.init_agent")
    def test_preserves_session_store(
        self, mock_init_agent, client, mock_document_agent
    ):
        from unittest.mock import MagicMock, sentinel
        from AI.agents.base import Agent

        new_mock_agent = MagicMock(spec=Agent)
        new_mock_agent._provider = "openrouter"
        new_mock_agent._model_name = "openai/gpt-4o"
        new_mock_agent._store = MagicMock()
        mock_init_agent.return_value = new_mock_agent
        mock_document_agent._store = sentinel.old_store

        client.put(
            "/document-agent/model",
            json={"provider": "openrouter", "model_name": "openai/gpt-4o"},
        )
        assert new_mock_agent._store is sentinel.old_store


# ── GET /sessions endpoint tests ─────────────────────────────────────────


class TestSessionsEndpoint:
    @pytest.fixture
    def client_with_archive(self, mock_agent):
        from fastapi.testclient import TestClient
        from BE.app import app

        mock_archive = AsyncMock()
        app.state.general_agent = mock_agent
        from tests.conftest import MOCK_USER

        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_archive_store] = lambda: mock_archive
        yield TestClient(app, raise_server_exceptions=False), mock_archive
        app.dependency_overrides.clear()

    def test_get_sessions_returns_list(self, client_with_archive):
        client, mock_archive = client_with_archive
        mock_archive.get_all_sessions_with_titles.return_value = [
            {"id": "s1", "title": "Hello world", "updated_at": "2025-01-01T00:00:00"},
            {"id": "s2", "title": "Another chat", "updated_at": "2025-01-02T00:00:00"},
        ]
        resp = client.get("/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sessions"]) == 2
        assert data["sessions"][0]["id"] == "s1"
        assert data["sessions"][0]["title"] == "Hello world"

    def test_get_sessions_empty(self, client_with_archive):
        client, mock_archive = client_with_archive
        mock_archive.get_all_sessions_with_titles.return_value = []
        resp = client.get("/sessions")
        assert resp.status_code == 200
        assert resp.json() == {"sessions": []}
