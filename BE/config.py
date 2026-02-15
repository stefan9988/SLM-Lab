import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_comma_separated(value: str | list[str]) -> list[str]:
    """Parse a comma-separated string into a list, or pass through a list."""
    if isinstance(value, list):
        return value
    if not value or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Logging
    LOG_LEVEL: str = "INFO"

    VITE_API_URL: str = "http://localhost:8000"
    VITE_PORT: int = 3000

    # CORS settings (comma-separated strings, parsed in app.py)
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = "Content-Type,Authorization"
    CORS_EXPOSE_HEADERS: str = ""
    CORS_MAX_AGE: int = 600

    # Google OAuth / JWT settings
    GOOGLE_CLIENT_ID: str = ""
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_EXPIRATION_HOURS: int = 24

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
    REDIS_URL: str = "redis://default:slmlab@localhost:6379/0"
    REDIS_PASSWORD: str = "slmlab"
    REDIS_ENABLED: bool = True
    REDIS_SESSION_TTL_DAYS: int = 30

    # General Agent Tool Toggles
    GENERAL_AGENT_DATE_TIME_TOOL: bool = False
    GENERAL_AGENT_BRAVE_SEARCH_TOOL: bool = False
    GENERAL_AGENT_PYTHON_REPL_TOOL: bool = False
    GENERAL_AGENT_OLLAMA_WEB_SEARCH_TOOL: bool = False
    GENERAL_AGENT_OLLAMA_WEB_FETCH_TOOL: bool = False
    GENERAL_AGENT_READ_FILE_CONTENT_TOOL: bool = False
    GENERAL_AGENT_SEARCH_CHUNKS_TOOL: bool = False
    GENERAL_AGENT_DELEGATE_TOOL: bool = False

    # Document Agent Tool Toggles
    DOCUMENT_AGENT_DATE_TIME_TOOL: bool = False
    DOCUMENT_AGENT_BRAVE_SEARCH_TOOL: bool = False
    DOCUMENT_AGENT_PYTHON_REPL_TOOL: bool = False
    DOCUMENT_AGENT_OLLAMA_WEB_SEARCH_TOOL: bool = False
    DOCUMENT_AGENT_OLLAMA_WEB_FETCH_TOOL: bool = False
    DOCUMENT_AGENT_READ_FILE_CONTENT_TOOL: bool = False
    DOCUMENT_AGENT_SEARCH_CHUNKS_TOOL: bool = False
    DOCUMENT_AGENT_DELEGATE_TOOL: bool = False

    # PostgreSQL settings
    POSTGRES_URL: str = "postgresql+asyncpg://slmlab:slmlab@localhost:5432/slmlab"
    POSTGRES_ENABLED: bool = True
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10
    POSTGRES_POOL_RECYCLE: int = 3600
    POSTGRES_POOL_PRE_PING: bool = True

    # Qdrant settings
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = "slmlab"
    QDRANT_ENABLED: bool = False
    QDRANT_COLLECTION_NAME: str = "slmlab"
    QDRANT_GRPC_PORT: int = 6334

    # Embedding settings
    EMBEDDING_ENABLED: bool = False
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSIONS: int = 768
    EMBEDDING_CHUNK_SIZE: int = 1000
    EMBEDDING_CHUNK_OVERLAP: int = 200

    # Archive retry settings
    ARCHIVE_MAX_RETRIES: int = 3
    ARCHIVE_RETRY_DELAY: float = 1.0
    ARCHIVE_TIMEOUT: float = 30.0

    # LangSmith settings
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "SLM Lab"


settings = Settings()

_initialized = False


def init_config() -> None:
    """Apply side effects: set env vars, configure logging and LangSmith.

    Safe to call multiple times; runs only once.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    os.environ.setdefault("LOG_LEVEL", settings.LOG_LEVEL)

    from BE.logger import setup_logger

    _logger = setup_logger(__name__)
    _logger.info(
        "Configuration loaded (model=%s, base_url=%s)",
        settings.MODEL_NAME,
        settings.OLLAMA_BASE_URL,
    )

    if settings.OLLAMA_API_KEY:
        os.environ["OLLAMA_API_KEY"] = settings.OLLAMA_API_KEY

    if settings.LANGSMITH_TRACING:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
        _logger.info(
            "LangSmith tracing enabled (project=%s)", settings.LANGSMITH_PROJECT
        )
    else:
        _logger.debug("LangSmith tracing disabled")
