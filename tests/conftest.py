"""Shared test fixtures."""

from unittest.mock import AsyncMock, MagicMock

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


@pytest.fixture
def mock_agent():
    agent = MagicMock(spec=Agent)
    agent.invoke = AsyncMock(return_value="mock response")
    agent.stream = MagicMock()  # async generator, handled per-test
    agent.get_history = AsyncMock(return_value=[])
    agent.clear_history = AsyncMock()
    agent.warm_session = AsyncMock()
    return agent


@pytest.fixture
def mock_document_agent():
    agent = MagicMock(spec=Agent)
    agent.invoke = AsyncMock(return_value="mock doc response")
    agent.stream = MagicMock()
    agent.get_history = AsyncMock(return_value=[])
    agent.clear_history = AsyncMock()
    agent.warm_session = AsyncMock()
    return agent


@pytest.fixture
def client(mock_agent, mock_document_agent):
    from fastapi.testclient import TestClient
    from BE.app import app

    app.state.general_agent = mock_agent
    app.state.document_agent = mock_document_agent
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
