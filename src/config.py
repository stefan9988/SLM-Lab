from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Application settings
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Model settings
    MODEL_NAME: str = "llama2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"


settings = Settings()
