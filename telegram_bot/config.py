from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramSettings(BaseSettings):
    """Telegram bot configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_USER_ID: int = 0
    TELEGRAM_SESSION_ID: str = "telegram_main"
    TELEGRAM_BOT_USER_ID: str = "telegram_bot_user"
    TELEGRAM_LLM_PROVIDER: str = ""
    TELEGRAM_MODEL_NAME: str = ""


settings = TelegramSettings()
