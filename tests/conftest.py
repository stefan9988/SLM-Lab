"""Shared test fixtures."""

from unittest.mock import MagicMock

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
    agent.invoke.return_value = "mock response"
    agent.stream.return_value = iter([{"type": "token", "content": "hello"}])
    agent.get_history.return_value = []
    agent.clear_history.return_value = None
    return agent


@pytest.fixture
def client(mock_agent):
    from fastapi.testclient import TestClient
    from BE.app import app

    app.state.general_agent = mock_agent
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
