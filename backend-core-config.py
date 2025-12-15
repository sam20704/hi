# backend/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SAP Chatbot Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"

    # Database
    SAP_DB_PATH: str = "./dummy.db"

    # Optional future infra
    REDIS_URL: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
