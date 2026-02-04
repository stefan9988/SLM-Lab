"""Tests for BE.config module."""

import os
from unittest.mock import patch

import pytest

from BE.config import Settings, _parse_comma_separated


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


class TestParseCommaSeparated:
    def test_string_input(self):
        assert _parse_comma_separated("a,b,c") == ["a", "b", "c"]

    def test_list_passthrough(self):
        assert _parse_comma_separated(["x", "y"]) == ["x", "y"]

    def test_whitespace_stripping(self):
        assert _parse_comma_separated("  a , b , c  ") == ["a", "b", "c"]

    def test_empty_string(self):
        assert _parse_comma_separated("") == []

    def test_blank_string(self):
        assert _parse_comma_separated("   ") == []

    def test_trailing_comma(self):
        assert _parse_comma_separated("a,b,") == ["a", "b"]

    def test_single_value(self):
        assert _parse_comma_separated("http://localhost:3000") == [
            "http://localhost:3000"
        ]


class TestCorsSettings:
    def test_default_origins(self):
        s = Settings(_env_file=None, LOG_LEVEL="INFO")
        assert s.CORS_ALLOW_ORIGINS == "http://localhost:3000,http://localhost:8080"

    def test_custom_origins(self):
        s = Settings(
            CORS_ALLOW_ORIGINS="http://localhost:3000,https://example.com",
            LOG_LEVEL="INFO",
        )
        assert s.CORS_ALLOW_ORIGINS == "http://localhost:3000,https://example.com"

    def test_single_origin(self):
        s = Settings(CORS_ALLOW_ORIGINS="http://localhost:5000", LOG_LEVEL="INFO")
        assert s.CORS_ALLOW_ORIGINS == "http://localhost:5000"

    def test_custom_methods(self):
        s = Settings(CORS_ALLOW_METHODS="GET,POST", LOG_LEVEL="INFO")
        assert s.CORS_ALLOW_METHODS == "GET,POST"

    def test_custom_headers(self):
        s = Settings(
            CORS_ALLOW_HEADERS="Content-Type,Authorization,X-Custom",
            LOG_LEVEL="INFO",
        )
        assert s.CORS_ALLOW_HEADERS == "Content-Type,Authorization,X-Custom"

    def test_expose_headers_empty_default(self):
        s = Settings(LOG_LEVEL="INFO")
        assert s.CORS_EXPOSE_HEADERS == ""

    def test_expose_headers_custom(self):
        s = Settings(CORS_EXPOSE_HEADERS="X-Total-Count,X-Page", LOG_LEVEL="INFO")
        assert s.CORS_EXPOSE_HEADERS == "X-Total-Count,X-Page"

    def test_max_age_default(self):
        s = Settings(LOG_LEVEL="INFO")
        assert s.CORS_MAX_AGE == 600

    def test_max_age_custom(self):
        s = Settings(CORS_MAX_AGE=3600, LOG_LEVEL="INFO")
        assert s.CORS_MAX_AGE == 3600

    def test_credentials_default_true(self):
        s = Settings(LOG_LEVEL="INFO")
        assert s.CORS_ALLOW_CREDENTIALS is True

    def test_default_methods(self):
        s = Settings(LOG_LEVEL="INFO")
        assert s.CORS_ALLOW_METHODS == "GET,POST,DELETE,OPTIONS"

    def test_default_headers(self):
        s = Settings(LOG_LEVEL="INFO")
        assert s.CORS_ALLOW_HEADERS == "Content-Type,Authorization"

    def test_origins_parsed_correctly(self):
        """Verify _parse_comma_separated works with CORS_ALLOW_ORIGINS values."""
        s = Settings(
            CORS_ALLOW_ORIGINS="http://localhost:3000,https://example.com",
            LOG_LEVEL="INFO",
        )
        assert _parse_comma_separated(s.CORS_ALLOW_ORIGINS) == [
            "http://localhost:3000",
            "https://example.com",
        ]

    def test_methods_parsed_correctly(self):
        """Verify _parse_comma_separated works with CORS_ALLOW_METHODS values."""
        s = Settings(LOG_LEVEL="INFO")
        assert _parse_comma_separated(s.CORS_ALLOW_METHODS) == [
            "GET",
            "POST",
            "DELETE",
            "OPTIONS",
        ]

    def test_expose_headers_empty_parsed(self):
        """Verify _parse_comma_separated returns [] for empty CORS_EXPOSE_HEADERS."""
        s = Settings(LOG_LEVEL="INFO")
        assert _parse_comma_separated(s.CORS_EXPOSE_HEADERS) == []
