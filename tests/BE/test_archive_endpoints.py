"""Tests for archive API endpoints in BE.app."""

from unittest.mock import AsyncMock, patch


class TestArchiveEndpoints:
    @patch("BE.app._create_archive_store", return_value=None)
    def test_list_sessions_unavailable(self, mock_cs, client):
        resp = client.get("/archive/sessions")
        assert resp.status_code == 503

    @patch("BE.app._create_archive_store")
    def test_list_sessions(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.get_all_sessions.return_value = [
            {"id": "s1", "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00", "model_name": "m", "provider": "p"}
        ]
        mock_cs.return_value = mock_store
        resp = client.get("/archive/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == "s1"

    @patch("BE.app._create_archive_store", return_value=None)
    def test_get_session_unavailable(self, mock_cs, client):
        resp = client.get("/archive/sessions/s1")
        assert resp.status_code == 503

    @patch("BE.app._create_archive_store")
    def test_get_session_messages(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.get_messages.return_value = [
            {"role": "human", "content": "hi", "thinking": None}
        ]
        mock_cs.return_value = mock_store
        resp = client.get("/archive/sessions/s1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "s1"
        assert len(data["messages"]) == 1

    @patch("BE.app._create_archive_store", return_value=None)
    def test_delete_session_unavailable(self, mock_cs, client):
        resp = client.delete("/archive/sessions/s1")
        assert resp.status_code == 503

    @patch("BE.app._create_archive_store")
    def test_delete_session_success(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.delete_session.return_value = True
        mock_cs.return_value = mock_store
        resp = client.delete("/archive/sessions/s1")
        assert resp.status_code == 200
        assert resp.json() == {"status": "deleted"}

    @patch("BE.app._create_archive_store")
    def test_delete_session_not_found(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.delete_session.return_value = False
        mock_cs.return_value = mock_store
        resp = client.delete("/archive/sessions/s1")
        assert resp.status_code == 404
