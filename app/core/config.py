# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Tell BaseSettings to read from .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "FastAPI Cron Job App"
    DEBUG: bool = False
    VAPI_API_KEY: str
    VAPI_BASE_URL: str
    VAPI_ASSISTANT_ID: str
    VAPI_PHONE_NUMBER_ID: str
    MONGO_DB_URL: str
    DATA_SOURCE_URL: str
    MONGO_DATABASE_NAME: str

settings = Settings()
