"""Shared test fixtures."""

from unittest.mock import MagicMock

import pytest

from AI.agents.base import Agent


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
    yield TestClient(app, raise_server_exceptions=False)
