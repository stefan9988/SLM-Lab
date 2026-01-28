from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Model settings
    MODEL_NAME: str = "llama2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"


settings = Settings()
