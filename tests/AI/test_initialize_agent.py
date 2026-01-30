"""Tests for AI.agents.initialize_agent module."""

from unittest.mock import MagicMock, patch

import pytest

from AI.agents.initialize_agent import _build_llm, init_agent


class TestBuildLlm:
    @patch("AI.agents.initialize_agent.settings")
    def test_ollama_provider(self, mock_settings):
        mock_settings.LLM_PROVIDER = "ollama"
        mock_settings.MODEL_NAME = "llama3.1:8b"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_THINKING = True
        with patch("langchain_ollama.ChatOllama") as MockOllama:
            _build_llm()
            MockOllama.assert_called_once_with(
                model="llama3.1:8b", base_url="http://localhost:11434", reasoning=True
            )

    @patch("AI.agents.initialize_agent.settings")
    def test_ollama_provider_no_thinking(self, mock_settings):
        mock_settings.LLM_PROVIDER = "ollama"
        mock_settings.MODEL_NAME = "llama3.1:8b"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_THINKING = False
        with patch("langchain_ollama.ChatOllama") as MockOllama:
            _build_llm()
            MockOllama.assert_called_once_with(
                model="llama3.1:8b", base_url="http://localhost:11434"
            )

    @patch("AI.agents.initialize_agent.settings")
    def test_openrouter_provider(self, mock_settings):
        mock_settings.LLM_PROVIDER = "openrouter"
        mock_settings.MODEL_NAME = "gpt-4"
        mock_settings.OPEN_ROUTER_API_KEY = "key123"
        mock_settings.OPEN_ROUTER_BASE_URL = "https://openrouter.ai/api/v1"
        with patch("langchain_openai.ChatOpenAI") as MockOpenAI:
            llm = _build_llm()
            MockOpenAI.assert_called_once_with(
                model="gpt-4",
                openai_api_key="key123",
                openai_api_base="https://openrouter.ai/api/v1",
                extra_body={"require": ["tools"]},
            )

    @patch("AI.agents.initialize_agent.settings")
    def test_invalid_provider_raises(self, mock_settings):
        mock_settings.LLM_PROVIDER = "invalid"
        with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
            _build_llm()


class TestInitAgent:
    @patch("AI.agents.initialize_agent._build_llm")
    @patch("AI.agents.base.create_agent")
    def test_returns_agent(self, mock_create, mock_build_llm):
        mock_build_llm.return_value = MagicMock()
        mock_create.return_value = MagicMock()
        agent = init_agent(system_prompt="test", tools=[], maintain_history=False)
        from AI.agents.base import Agent

        assert isinstance(agent, Agent)

    @patch("AI.agents.initialize_agent._build_llm")
    def test_propagates_exceptions(self, mock_build_llm):
        mock_build_llm.side_effect = ValueError("bad")
        with pytest.raises(ValueError):
            init_agent(system_prompt="test")
