"""Tests for BE.app FastAPI endpoints."""

import base64
import json
from unittest.mock import MagicMock, patch

from BE.app import FileAttachment, build_prompt_with_files
from BE.auth import get_current_user


def _make_text_data_url(text: str, mime: str = "text/plain") -> str:
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _make_file(
    name: str, content_text: str, mime: str = "text/plain"
) -> FileAttachment:
    data_url = _make_text_data_url(content_text, mime)
    return FileAttachment(
        name=name, type=mime, content=data_url, size=len(content_text)
    )


# ── build_prompt_with_files unit tests ──────────────────────────────────────


class TestBuildPromptWithFiles:
    def test_text_file_content_in_prompt(self):
        f = _make_file("data.csv", "a,b,c\n1,2,3", "text/csv")
        prompt, images, warnings = build_prompt_with_files("summarize", [f])
        assert "a,b,c" in prompt
        assert "1,2,3" in prompt
        assert "--- Content of data.csv ---" in prompt
        assert prompt.endswith("summarize")
        assert images == []
        assert warnings == []

    def test_multiple_text_files(self):
        f1 = _make_file("a.txt", "hello", "text/plain")
        f2 = _make_file("b.md", "# title", "text/markdown")
        prompt, images, warnings = build_prompt_with_files("go", [f1, f2])
        assert "hello" in prompt
        assert "# title" in prompt
        assert prompt.endswith("go")

    def test_pdf_text_extraction(self):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "pdf content here"
        mock_doc = MagicMock()
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.close = MagicMock()

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch("BE.app.fitz", mock_fitz):
            f = FileAttachment(
                name="doc.pdf",
                type="application/pdf",
                content=_make_text_data_url("fakepdfbytes", "application/pdf"),
                size=100,
            )
            prompt, images, warnings = build_prompt_with_files("analyze", [f])
            assert "pdf content here" in prompt
            assert prompt.endswith("analyze")
            assert warnings == []

    def test_pdf_empty_text_warns(self):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "   "
        mock_doc = MagicMock()
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.close = MagicMock()

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch("BE.app.fitz", mock_fitz):
            f = FileAttachment(
                name="scan.pdf",
                type="application/pdf",
                content=_make_text_data_url("bytes", "application/pdf"),
                size=50,
            )
            prompt, images, warnings = build_prompt_with_files("read", [f])
            assert len(warnings) == 1
            assert "scan.pdf" in warnings[0]

    def test_pdf_extraction_failure_warns(self):
        mock_fitz = MagicMock()
        mock_fitz.open.side_effect = RuntimeError("corrupt")

        with patch("BE.app.fitz", mock_fitz):
            f = FileAttachment(
                name="bad.pdf",
                type="application/pdf",
                content=_make_text_data_url("bytes", "application/pdf"),
                size=50,
            )
            prompt, images, warnings = build_prompt_with_files("read", [f])
            assert len(warnings) == 1
            assert "bad.pdf" in warnings[0]
            assert "could not extract text" in prompt.lower()

    def test_image_file_added_to_images(self):
        data_url = "data:image/png;base64,iVBOR"
        f = FileAttachment(name="pic.png", type="image/png", content=data_url, size=10)
        prompt, images, warnings = build_prompt_with_files("describe", [f])
        assert len(images) == 1
        assert images[0]["url"] == data_url
        assert prompt.endswith("describe")
        assert warnings == []

    def test_empty_message_with_files_uses_default_prompt(self):
        f = _make_file("notes.txt", "some notes here")
        prompt, images, warnings = build_prompt_with_files("", [f])
        assert "some notes here" in prompt
        assert "Please review and summarize the content" in prompt
        assert warnings == []

    def test_whitespace_message_with_files_uses_default_prompt(self):
        f = _make_file("notes.txt", "content")
        prompt, images, warnings = build_prompt_with_files("   ", [f])
        assert "content" in prompt
        assert "Please review and summarize the content" in prompt

    def test_no_files_returns_original_message(self):
        prompt, images, warnings = build_prompt_with_files("hello", [])
        assert prompt == "hello"
        assert images == []
        assert warnings == []


# ── Endpoint tests with file attachments ────────────────────────────────────


class TestChatWithFiles:
    def test_post_chat_with_text_file(self, client, mock_agent):
        data_url = _make_text_data_url("col1,col2\n10,20")
        resp = client.post(
            "/chat",
            json={
                "message": "summarize",
                "session_id": "s1",
                "files": [
                    {
                        "name": "data.csv",
                        "type": "text/csv",
                        "content": data_url,
                        "size": 20,
                    }
                ],
            },
        )
        assert resp.status_code == 200
        call_args = mock_agent.invoke.call_args
        sent_prompt = call_args[0][0]
        assert "col1,col2" in sent_prompt
        assert "10,20" in sent_prompt
        assert sent_prompt.endswith("summarize")

    def test_post_chat_stream_with_text_file(self, client, mock_agent):
        mock_agent.stream.return_value = iter([{"type": "token", "content": "ok"}])
        data_url = _make_text_data_url("line1\nline2")
        resp = client.post(
            "/chat/stream",
            json={
                "message": "read",
                "session_id": "s1",
                "files": [
                    {
                        "name": "notes.txt",
                        "type": "text/plain",
                        "content": data_url,
                        "size": 10,
                    }
                ],
            },
        )
        assert resp.status_code == 200
        call_args = mock_agent.stream.call_args
        sent_prompt = call_args[0][0]
        assert "line1" in sent_prompt
        assert sent_prompt.endswith("read")

    def test_chat_stream_emits_status_for_warnings(self, client, mock_agent):
        mock_agent.stream.return_value = iter([{"type": "token", "content": "x"}])
        mock_fitz = MagicMock()
        mock_fitz.open.side_effect = RuntimeError("corrupt")

        with patch("BE.app.fitz", mock_fitz):
            data_url = _make_text_data_url("bytes", "application/pdf")
            resp = client.post(
                "/chat/stream",
                json={
                    "message": "read",
                    "session_id": "s1",
                    "files": [
                        {
                            "name": "bad.pdf",
                            "type": "application/pdf",
                            "content": data_url,
                            "size": 10,
                        }
                    ],
                },
            )
        assert resp.status_code == 200
        lines = [l for l in resp.text.strip().split("\n\n") if l.startswith("data:")]
        # First event should be a status warning, before token events
        first_payload = json.loads(lines[0].removeprefix("data: "))
        assert first_payload["type"] == "status"
        assert "bad.pdf" in first_payload["content"]

    def test_post_chat_stream_empty_message_with_file(self, client, mock_agent):
        mock_agent.stream.return_value = iter([{"type": "token", "content": "ok"}])
        data_url = _make_text_data_url("file content here")
        resp = client.post(
            "/chat/stream",
            json={
                "message": "",
                "session_id": "s1",
                "files": [
                    {
                        "name": "doc.txt",
                        "type": "text/plain",
                        "content": data_url,
                        "size": 17,
                    }
                ],
            },
        )
        assert resp.status_code == 200
        call_args = mock_agent.stream.call_args
        sent_prompt = call_args[0][0]
        assert "file content here" in sent_prompt
        assert "Please review and summarize the content" in sent_prompt

    def test_file_size_limit_returns_413(self, client):
        data_url = _make_text_data_url("x")
        resp = client.post(
            "/chat",
            json={
                "message": "hi",
                "session_id": "s1",
                "files": [
                    {
                        "name": "big.bin",
                        "type": "application/octet-stream",
                        "content": data_url,
                        "size": 25_000_000,
                    }
                ],
            },
        )
        assert resp.status_code == 413


class TestChatEndpoint:
    def test_post_chat_200(self, client, mock_agent):
        resp = client.post("/chat", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 200
        assert resp.json() == {"response": "mock response"}
        mock_agent.invoke.assert_called_once_with(
            "hi", session_id="s1", images=None, user_id="test-user-id"
        )

    def test_post_chat_422_missing_fields(self, client):
        resp = client.post("/chat", json={})
        assert resp.status_code == 422


class TestChatStreamEndpoint:
    def test_returns_sse_with_done(self, client, mock_agent):
        mock_agent.stream.return_value = iter(
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

    def test_protected_route_without_auth_returns_401(self, mock_agent):
        """Without the dependency override, protected routes require auth."""
        from fastapi.testclient import TestClient
        from BE.app import app

        app.state.general_agent = mock_agent
        # Clear overrides so auth is actually enforced
        app.dependency_overrides.pop(get_current_user, None)
        unauthed_client = TestClient(app, raise_server_exceptions=False)
        resp = unauthed_client.post(
            "/chat", json={"message": "hi", "session_id": "s1"}
        )
        assert resp.status_code == 422  # missing Authorization header
