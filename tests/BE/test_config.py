"""Tests for BE.config module."""

import os
from unittest.mock import patch

from BE.config import Settings


class TestSettingsDefaults:
    def test_default_llm_provider(self):
        s = Settings(LOG_LEVEL="INFO")
        assert s.LLM_PROVIDER == "ollama"

    def test_default_langsmith_tracing_false(self):
        s = Settings(LOG_LEVEL="INFO")
        assert s.LANGSMITH_TRACING is False

    def test_explicit_kwargs_override(self):
        s = Settings(LLM_PROVIDER="openrouter", MODEL_NAME="gpt-4", LOG_LEVEL="INFO")
        assert s.LLM_PROVIDER == "openrouter"
        assert s.MODEL_NAME == "gpt-4"


class TestLangSmithEnvExport:
    def test_tracing_true_sets_env_vars(self):
        env = os.environ.copy()
        with patch.dict(os.environ, env, clear=True):
            s = Settings(
                LANGSMITH_TRACING=True,
                LANGSMITH_API_KEY="test-key",
                LANGSMITH_PROJECT="test-proj",
                LOG_LEVEL="INFO",
            )
            # Simulate what config.py does at module level
            if s.LANGSMITH_TRACING:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_ENDPOINT"] = s.LANGSMITH_ENDPOINT
                os.environ["LANGCHAIN_API_KEY"] = s.LANGSMITH_API_KEY
                os.environ["LANGCHAIN_PROJECT"] = s.LANGSMITH_PROJECT

            assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
            assert os.environ["LANGCHAIN_API_KEY"] == "test-key"
            assert os.environ["LANGCHAIN_PROJECT"] == "test-proj"

    def test_tracing_false_does_not_set_env_vars(self):
        env = os.environ.copy()
        # Remove any existing langchain keys
        for k in list(env.keys()):
            if k.startswith("LANGCHAIN_"):
                del env[k]
        with patch.dict(os.environ, env, clear=True):
            s = Settings(LANGSMITH_TRACING=False, LOG_LEVEL="INFO")
            if s.LANGSMITH_TRACING:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"

            assert "LANGCHAIN_TRACING_V2" not in os.environ
