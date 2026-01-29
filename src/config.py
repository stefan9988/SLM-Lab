import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Model settings
    MODEL_NAME: str = "llama2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # API settings
    API_TITLE: str = "SLM-Lab Chat API"
    API_DESCRIPTION: str = "Chat API with streaming support using OllamaAgent"
    API_VERSION: str = "0.1.0"

    # External service API keys
    BRAVE_SEARCH_API_KEY: str = "YOUR_BRAVE_SEARCH_API_KEY_HERE"

    # LangSmith settings
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "SLM Lab"


settings = Settings()

# Export LangSmith settings to environment so LangChain picks them up
if settings.LANGSMITH_TRACING:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
