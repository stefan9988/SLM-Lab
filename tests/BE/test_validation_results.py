"""Tests for POST /validate-stream and GET /validate-results/{session_id}."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from AI.agents.base import Agent
from BE.auth import UserInfo, get_current_user

MOCK_USER = UserInfo(
    id="test-user-id",
    email="test@example.com",
    name="Test User",
    picture="",
    google_sub="google-sub-123",
)

MOCK_USER_2 = UserInfo(
    id="test-user-id-2",
    email="other@example.com",
    name="Other User",
    picture="",
    google_sub="google-sub-456",
)

SAMPLE_RESULTS = [
    {
        "claim": "company_name: Acme Corp",
        "status": "correct",
        "validated_value": "Acme Corporation",
        "sources": ["https://acme.example.com/about"],
    },
    {
        "claim": "founded_year: 1990",
        "status": "incorrect",
        "validated_value": "1985",
        "sources": ["https://acme.example.com/history"],
    },
]

AGENT_RESPONSE_JSON = json.dumps({"results": SAMPLE_RESULTS})


def _parse_sse_lines(text: str) -> list[str]:
    """Return data-prefixed SSE lines, excluding the [DONE] sentinel."""
    return [
        line.strip()
        for line in text.split("\n")
        if line.strip().startswith("data:") and line.strip() != "data: [DONE]"
    ]


async def _async_gen(items):
    for item in items:
        yield item


@pytest.fixture
def mock_validation_agent():
    agent = MagicMock(spec=Agent)
    agent.stream = MagicMock()
    return agent


def _make_minimal_agent():
    agent = MagicMock(spec=Agent)
    agent.invoke = AsyncMock(return_value="mock")
    agent.stream = MagicMock()
    agent.get_history = AsyncMock(return_value=[])
    agent.clear_history = AsyncMock()
    agent.warm_session = AsyncMock()
    agent.append_to_history = AsyncMock()
    return agent


@pytest.fixture
def client_with_validation(mock_validation_agent):
    from fastapi.testclient import TestClient
    from BE.app import app

    app.state.general_agent = _make_minimal_agent()
    app.state.document_agent = _make_minimal_agent()
    app.state.validation_agent = mock_validation_agent
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def client_user2(mock_validation_agent):
    from fastapi.testclient import TestClient
    from BE.app import app

    app.state.general_agent = _make_minimal_agent()
    app.state.document_agent = _make_minimal_agent()
    app.state.validation_agent = mock_validation_agent
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER_2
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _make_db_session_mock(row=None):
    """Return a context-manager-compatible async DB session mock."""

    async def _fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = row
        return result

    async_session = AsyncMock()
    async_session.__aenter__ = AsyncMock(return_value=async_session)
    async_session.__aexit__ = AsyncMock(return_value=False)
    async_session.execute = _fake_execute
    return async_session


class TestGetValidationResultsNotFound:
    @patch("BE.app.settings")
    def test_returns_null_when_postgres_disabled(
        self, mock_settings, client_with_validation
    ):
        mock_settings.POSTGRES_ENABLED = False
        resp = client_with_validation.get("/validate-results/session-abc")
        assert resp.status_code == 200
        assert resp.json() == {"results": None}

    @patch("BE.app.settings")
    def test_returns_null_for_unknown_session(
        self, mock_settings, client_with_validation
    ):
        mock_settings.POSTGRES_ENABLED = True
        async_session = _make_db_session_mock(row=None)
        factory = MagicMock(return_value=async_session)

        with patch("BE.database.get_session_factory", return_value=factory):
            resp = client_with_validation.get("/validate-results/unknown-session")

        assert resp.status_code == 200
        assert resp.json() == {"results": None}


class TestValidateStream:
    def _make_stream_events(self):
        return [
            {"type": "status", "content": "Calling tool: web_page_content"},
            {"type": "token", "content": AGENT_RESPONSE_JSON},
        ]

    @patch("BE.app.settings")
    def test_streams_validation_complete_event(
        self,
        mock_settings,
        client_with_validation,
        mock_validation_agent,
    ):
        from BE.app import app

        mock_settings.POSTGRES_ENABLED = False
        mock_validation_agent.stream.return_value = _async_gen(
            self._make_stream_events()
        )

        resp = client_with_validation.post(
            "/validate-stream",
            json={
                "session_id": "sess-abc",
                "validation_urls": ["https://acme.example.com"],
                "extracted_data": [
                    {"key": "company_name", "value": "Acme Corp"},
                    {"key": "founded_year", "value": "1990"},
                ],
            },
        )

        assert resp.status_code == 200
        lines = _parse_sse_lines(resp.text)
        assert resp.text.rstrip().endswith("data: [DONE]")

        vc_events = [
            json.loads(l.removeprefix("data: "))
            for l in lines
            if json.loads(l.removeprefix("data: ")).get("type") == "validation_complete"
        ]

        assert len(vc_events) == 1
        results = vc_events[0]["content"]
        assert len(results) == 2
        assert results[0]["claim"] == "company_name: Acme Corp"
        assert results[0]["status"] == "correct"

        mock_general_agent = app.state.general_agent
        mock_general_agent.append_to_history.assert_awaited_once()
        call_args = mock_general_agent.append_to_history.call_args
        assert (
            call_args.kwargs.get("user_id") == "test-user-id"
            or call_args.args[2] == "test-user-id"
        )

    @patch("BE.app.settings")
    def test_appends_validation_summary_to_agent_history(
        self,
        mock_settings,
        client_with_validation,
        mock_validation_agent,
    ):
        from langchain_core.messages import AIMessage, HumanMessage
        from BE.app import app

        mock_settings.POSTGRES_ENABLED = False
        mock_validation_agent.stream.return_value = _async_gen(
            self._make_stream_events()
        )

        client_with_validation.post(
            "/validate-stream",
            json={
                "session_id": "sess-history",
                "validation_urls": ["https://acme.example.com"],
                "extracted_data": [
                    {"key": "company_name", "value": "Acme Corp"},
                ],
            },
        )

        mock_general_agent = app.state.general_agent
        mock_general_agent.append_to_history.assert_awaited_once()
        call_args = mock_general_agent.append_to_history.call_args

        session_id_arg = (
            call_args.args[0] if call_args.args else call_args.kwargs.get("session_id")
        )
        messages_arg = (
            call_args.args[1]
            if len(call_args.args) > 1
            else call_args.kwargs.get("messages")
        )

        assert session_id_arg == "sess-history"
        assert len(messages_arg) == 2
        assert isinstance(messages_arg[0], HumanMessage)
        assert isinstance(messages_arg[1], AIMessage)
        import json as json_module
        parsed = json_module.loads(messages_arg[1].content)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert "claim" in parsed[0]
        assert "status" in parsed[0]

    @patch("BE.app.settings")
    def test_persists_result_when_postgres_enabled(
        self,
        mock_settings,
        client_with_validation,
        mock_validation_agent,
    ):
        mock_settings.POSTGRES_ENABLED = True
        mock_validation_agent.stream.return_value = _async_gen(
            self._make_stream_events()
        )

        saved_results = []

        async def fake_save(session_id, user_id, results):
            saved_results.append((session_id, user_id, results))

        with patch("BE.app._save_validation_result", new=fake_save):
            resp = client_with_validation.post(
                "/validate-stream",
                json={
                    "session_id": "sess-persist",
                    "validation_urls": ["https://acme.example.com"],
                    "extracted_data": [{"key": "company_name", "value": "Acme Corp"}],
                },
            )

        assert resp.status_code == 200
        assert len(saved_results) == 1
        assert saved_results[0][0] == "sess-persist"
        assert saved_results[0][1] == "test-user-id"

    @patch("BE.app.settings")
    def test_returns_error_event_on_invalid_response(
        self,
        mock_settings,
        client_with_validation,
        mock_validation_agent,
    ):
        mock_settings.POSTGRES_ENABLED = False
        mock_validation_agent.stream.return_value = _async_gen(
            [{"type": "token", "content": "not valid json at all"}]
        )

        resp = client_with_validation.post(
            "/validate-stream",
            json={
                "session_id": "sess-error",
                "validation_urls": ["https://example.com"],
                "extracted_data": [{"key": "x", "value": "y"}],
            },
        )

        assert resp.status_code == 200
        lines = _parse_sse_lines(resp.text)
        error_events = [
            json.loads(l.removeprefix("data: "))
            for l in lines
            if json.loads(l.removeprefix("data: ")).get("type") == "error"
        ]
        assert len(error_events) >= 1


class TestGetValidationResultsWithData:
    @patch("BE.app.settings")
    def test_returns_results_for_own_session(
        self, mock_settings, client_with_validation
    ):
        mock_settings.POSTGRES_ENABLED = True

        mock_row = MagicMock()
        mock_row.results = SAMPLE_RESULTS
        async_session = _make_db_session_mock(row=mock_row)
        factory = MagicMock(return_value=async_session)

        with patch("BE.database.get_session_factory", return_value=factory):
            resp = client_with_validation.get("/validate-results/sess-abc")

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] is not None
        assert len(data["results"]) == 2
        assert data["results"][0]["claim"] == "company_name: Acme Corp"


class TestValidationResultSecurity:
    @patch("BE.app.settings")
    def test_other_user_gets_null(self, mock_settings, client_user2):
        """User B should not be able to see user A's validation results."""
        mock_settings.POSTGRES_ENABLED = True
        async_session = _make_db_session_mock(row=None)
        factory = MagicMock(return_value=async_session)

        with patch("BE.database.get_session_factory", return_value=factory):
            resp = client_user2.get("/validate-results/sess-belongs-to-user1")

        assert resp.status_code == 200
        assert resp.json() == {"results": None}


class TestParseValidationJson:
    def test_parses_object_with_results_key(self):
        from BE.app import _parse_validation_json

        text = json.dumps({"results": SAMPLE_RESULTS})
        result = _parse_validation_json(text)
        assert len(result) == 2
        assert result[0]["claim"] == "company_name: Acme Corp"

    def test_parses_bare_array_fallback(self):
        from BE.app import _parse_validation_json

        text = json.dumps(SAMPLE_RESULTS)
        result = _parse_validation_json(text)
        assert len(result) == 2

    def test_strips_markdown_fences(self):
        from BE.app import _parse_validation_json

        text = f"```json\n{json.dumps({'results': SAMPLE_RESULTS})}\n```"
        result = _parse_validation_json(text)
        assert len(result) == 2

    def test_raises_on_invalid_text(self):
        from BE.app import _parse_validation_json

        with pytest.raises(ValueError, match="No validation results found"):
            _parse_validation_json("no json here at all")
