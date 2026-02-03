import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Logging
    LOG_LEVEL: str = "INFO"

    # LLM provider settings
    LLM_PROVIDER: str = "ollama"  # "ollama" | "openrouter"
    MODEL_NAME: str = "llama3.1:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_THINKING: bool = False
    OLLAMA_API_KEY: str = ""
    OPEN_ROUTER_API_KEY: str = ""
    OPEN_ROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # API settings
    API_TITLE: str = "SLM-Lab Chat API"
    API_DESCRIPTION: str = "Chat API with streaming support using OllamaAgent"
    API_VERSION: str = "0.1.0"

    # External service API keys
    BRAVE_SEARCH_API_KEY: str = "YOUR_BRAVE_SEARCH_API_KEY_HERE"

    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True
    REDIS_SESSION_TTL_DAYS: int = 30

    # General Agent Tool Toggles
    GENERAL_AGENT_DATE_TIME_TOOL: bool = False
    GENERAL_AGENT_BRAVE_SEARCH_TOOL: bool = False
    GENERAL_AGENT_PYTHON_REPL_TOOL: bool = False
    GENERAL_AGENT_OLLAMA_WEB_SEARCH_TOOL: bool = False
    GENERAL_AGENT_OLLAMA_WEB_FETCH_TOOL: bool = False

    # PostgreSQL settings
    POSTGRES_URL: str = "postgresql+asyncpg://slmlab:slmlab@localhost:5432/slmlab"
    POSTGRES_ENABLED: bool = True

    # LangSmith settings
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "SLM Lab"


settings = Settings()

# Set LOG_LEVEL in environment so logger.py can read it before config is imported
os.environ.setdefault("LOG_LEVEL", settings.LOG_LEVEL)

from BE.logger import setup_logger

_logger = setup_logger(__name__)
_logger.info(
    "Configuration loaded (model=%s, base_url=%s)",
    settings.MODEL_NAME,
    settings.OLLAMA_BASE_URL,
)

# Export OLLAMA_API_KEY so the ollama client picks it up for web search/fetch
if settings.OLLAMA_API_KEY:
    os.environ["OLLAMA_API_KEY"] = settings.OLLAMA_API_KEY

# Export LangSmith settings to environment so LangChain picks them up
if settings.LANGSMITH_TRACING:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    _logger.info("LangSmith tracing enabled (project=%s)", settings.LANGSMITH_PROJECT)
else:
    _logger.debug("LangSmith tracing disabled")
