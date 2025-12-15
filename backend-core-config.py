from pydantic_settings import BaseSettings
from pathlib import Path

# Always resolves to the backend/ directory
BASE_DIR = Path(__file__).resolve().parents[2]

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

    SAP_DB_PATH: str = str(BASE_DIR / "sap_dummy.db")

    # Optional future infra
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


# Single global settings object
settings = Settings()
