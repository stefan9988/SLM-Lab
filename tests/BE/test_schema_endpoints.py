"""Tests for extraction schema API endpoints in BE.app."""

from unittest.mock import AsyncMock, patch


class TestSchemaEndpoints:
    @patch("BE.app._create_schema_store", return_value=None)
    def test_list_schemas_unavailable(self, mock_cs, client):
        resp = client.get("/schemas")
        assert resp.status_code == 503

    @patch("BE.app._create_schema_store")
    def test_list_schemas(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.get_schemas.return_value = [
            {
                "id": "s1",
                "name": "Invoice",
                "fields": [],
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
            }
        ]
        mock_cs.return_value = mock_store
        resp = client.get("/schemas")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["schemas"]) == 1
        assert data["schemas"][0]["name"] == "Invoice"
        mock_store.get_schemas.assert_called_once_with(user_id="test-user-id")

    @patch("BE.app._create_schema_store", return_value=None)
    def test_create_schema_unavailable(self, mock_cs, client):
        resp = client.post("/schemas", json={"name": "Test", "fields": []})
        assert resp.status_code == 503

    @patch("BE.app._create_schema_store")
    def test_create_schema(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.create_schema.return_value = {
            "id": "new-id",
            "name": "Test",
            "fields": [],
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        mock_cs.return_value = mock_store
        resp = client.post("/schemas", json={"name": "Test", "fields": []})
        assert resp.status_code == 200
        assert resp.json()["id"] == "new-id"
        mock_store.create_schema.assert_called_once_with(
            user_id="test-user-id", name="Test", fields=[]
        )

    @patch("BE.app._create_schema_store")
    def test_create_schema_with_fields(self, mock_cs, client):
        mock_store = AsyncMock()
        fields = [{"id": "f1", "key": "title", "description": "The title"}]
        mock_store.create_schema.return_value = {
            "id": "new-id",
            "name": "Doc",
            "fields": fields,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        mock_cs.return_value = mock_store
        resp = client.post("/schemas", json={"name": "Doc", "fields": fields})
        assert resp.status_code == 200
        mock_store.create_schema.assert_called_once_with(
            user_id="test-user-id", name="Doc", fields=fields
        )

    @patch("BE.app._create_schema_store", return_value=None)
    def test_update_schema_unavailable(self, mock_cs, client):
        resp = client.put("/schemas/s1", json={"name": "X", "fields": []})
        assert resp.status_code == 503

    @patch("BE.app._create_schema_store")
    def test_update_schema(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.update_schema.return_value = {
            "id": "s1",
            "name": "Updated",
            "fields": [],
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-02T00:00:00",
        }
        mock_cs.return_value = mock_store
        resp = client.put("/schemas/s1", json={"name": "Updated", "fields": []})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        mock_store.update_schema.assert_called_once_with(
            "s1", user_id="test-user-id", name="Updated", fields=[]
        )

    @patch("BE.app._create_schema_store")
    def test_update_schema_not_found(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.update_schema.return_value = None
        mock_cs.return_value = mock_store
        resp = client.put("/schemas/s1", json={"name": "X", "fields": []})
        assert resp.status_code == 404

    @patch("BE.app._create_schema_store", return_value=None)
    def test_delete_schema_unavailable(self, mock_cs, client):
        resp = client.delete("/schemas/s1")
        assert resp.status_code == 503

    @patch("BE.app._create_schema_store")
    def test_delete_schema_success(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.delete_schema.return_value = True
        mock_cs.return_value = mock_store
        resp = client.delete("/schemas/s1")
        assert resp.status_code == 200
        assert resp.json() == {"status": "deleted"}
        mock_store.delete_schema.assert_called_once_with("s1", user_id="test-user-id")

    @patch("BE.app._create_schema_store")
    def test_delete_schema_not_found(self, mock_cs, client):
        mock_store = AsyncMock()
        mock_store.delete_schema.return_value = False
        mock_cs.return_value = mock_store
        resp = client.delete("/schemas/s1")
        assert resp.status_code == 404
