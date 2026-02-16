"""Tests for AI.agents.initialize_agent module."""

from unittest.mock import MagicMock, patch

import pytest

from AI.agents.initialize_agent import _build_llm, init_agent


class TestBuildLlm:
    @patch("AI.agents.initialize_agent.settings")
    def test_ollama_provider(self, mock_settings):
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_THINKING = True
        with patch("langchain_ollama.ChatOllama") as MockOllama:
            _build_llm("ollama", "llama3.1:8b")
            MockOllama.assert_called_once_with(
                model="llama3.1:8b", base_url="http://localhost:11434", reasoning=True
            )

    @patch("AI.agents.initialize_agent.settings")
    def test_ollama_provider_no_thinking(self, mock_settings):
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_THINKING = False
        with patch("langchain_ollama.ChatOllama") as MockOllama:
            _build_llm("ollama", "llama3.1:8b")
            MockOllama.assert_called_once_with(
                model="llama3.1:8b", base_url="http://localhost:11434"
            )

    @patch("AI.agents.initialize_agent.settings")
    def test_openrouter_provider(self, mock_settings):
        mock_settings.OPEN_ROUTER_API_KEY = "key123"
        mock_settings.OPEN_ROUTER_BASE_URL = "https://openrouter.ai/api/v1"
        with patch("langchain_openai.ChatOpenAI") as MockOpenAI:
            _build_llm("openrouter", "gpt-4")
            MockOpenAI.assert_called_once_with(
                model="gpt-4",
                openai_api_key="key123",
                openai_api_base="https://openrouter.ai/api/v1",
                extra_body={"require": ["tools"]},
            )

    @patch("AI.agents.initialize_agent.settings")
    def test_anthropic_provider(self, mock_settings):
        mock_settings.ANTHROPIC_API_KEY = "sk-ant-test"
        with patch("langchain_anthropic.ChatAnthropic") as MockAnthropic:
            _build_llm("anthropic", "claude-sonnet-4-5-20250929")
            MockAnthropic.assert_called_once_with(
                model="claude-sonnet-4-5-20250929",
                api_key="sk-ant-test",
            )

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
            _build_llm("invalid", "some-model")

    def test_invalid_provider_error_message_lists_all_providers(self):
        with pytest.raises(ValueError, match="'anthropic'"):
            _build_llm("invalid", "some-model")


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

    @patch("AI.agents.initialize_agent._build_llm")
    @patch("AI.agents.base.create_agent")
    @patch("AI.agents.initialize_agent.settings")
    def test_per_agent_provider_override(
        self, mock_settings, mock_create, mock_build_llm
    ):
        mock_settings.LLM_PROVIDER = "ollama"
        mock_settings.MODEL_NAME = "llama3.1:8b"
        mock_build_llm.return_value = MagicMock()
        mock_create.return_value = MagicMock()

        init_agent(
            system_prompt="test",
            tools=[],
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
        )
        mock_build_llm.assert_called_once_with(
            "anthropic", "claude-sonnet-4-5-20250929"
        )

    @patch("AI.agents.initialize_agent._build_llm")
    @patch("AI.agents.base.create_agent")
    @patch("AI.agents.initialize_agent.settings")
    def test_falls_back_to_global_when_no_override(
        self, mock_settings, mock_create, mock_build_llm
    ):
        mock_settings.LLM_PROVIDER = "openrouter"
        mock_settings.MODEL_NAME = "gpt-4"
        mock_build_llm.return_value = MagicMock()
        mock_create.return_value = MagicMock()

        init_agent(system_prompt="test", tools=[])
        mock_build_llm.assert_called_once_with("openrouter", "gpt-4")

    @patch("AI.agents.initialize_agent._build_llm")
    @patch("AI.agents.base.create_agent")
    @patch("AI.agents.initialize_agent.settings")
    def test_partial_override_provider_only(
        self, mock_settings, mock_create, mock_build_llm
    ):
        mock_settings.LLM_PROVIDER = "ollama"
        mock_settings.MODEL_NAME = "llama3.1:8b"
        mock_build_llm.return_value = MagicMock()
        mock_create.return_value = MagicMock()

        init_agent(system_prompt="test", tools=[], provider="anthropic")
        mock_build_llm.assert_called_once_with("anthropic", "llama3.1:8b")

    @patch("AI.agents.initialize_agent._build_llm")
    @patch("AI.agents.base.create_agent")
    @patch("AI.agents.initialize_agent.settings")
    def test_partial_override_model_only(
        self, mock_settings, mock_create, mock_build_llm
    ):
        mock_settings.LLM_PROVIDER = "ollama"
        mock_settings.MODEL_NAME = "llama3.1:8b"
        mock_build_llm.return_value = MagicMock()
        mock_create.return_value = MagicMock()

        init_agent(system_prompt="test", tools=[], model_name="custom-model")
        mock_build_llm.assert_called_once_with("ollama", "custom-model")
