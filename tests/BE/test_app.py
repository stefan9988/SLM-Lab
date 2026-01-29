"""Tests for BE.app FastAPI endpoints."""

import json


class TestChatEndpoint:
    def test_post_chat_200(self, client, mock_agent):
        resp = client.post("/chat", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 200
        assert resp.json() == {"response": "mock response"}
        mock_agent.invoke.assert_called_once_with("hi", session_id="s1")

    def test_post_chat_422_missing_fields(self, client):
        resp = client.post("/chat", json={})
        assert resp.status_code == 422


class TestChatStreamEndpoint:
    def test_returns_sse_with_done(self, client, mock_agent):
        mock_agent.stream.return_value = iter([
            {"type": "token", "content": "hi"},
        ])
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

    def test_get_history_422_missing_session_id(self, client):
        resp = client.get("/history")
        assert resp.status_code == 422

    def test_delete_history_200(self, client, mock_agent):
        resp = client.delete("/history", params={"session_id": "s1"})
        assert resp.status_code == 200
        assert resp.json() == {"status": "cleared"}
        mock_agent.clear_history.assert_called_once_with(session_id="s1")


class TestExceptionHandler:
    def test_invoke_raises_returns_500(self, client, mock_agent):
        mock_agent.invoke.side_effect = RuntimeError("boom")
        resp = client.post("/chat", json={"message": "hi", "session_id": "s1"})
        assert resp.status_code == 500
        assert "Internal server error" in resp.json()["detail"]
