"""
app/config.py

Central configuration. All secrets from environment.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Llama 3.2 (Critic) ──────────────────────────
    LLAMA_API_KEY: str
    LLAMA_BASE_URL: str = "https://api.together.xyz/v1"
    LLAMA_MODEL: str = "meta-llama/Llama-3.2-3B-Instruct"
    LLAMA_MAX_TOKENS: int = 2048
    LLAMA_TEMPERATURE: float = 0.0
    LLAMA_TIMEOUT: int = 30

    # ── Claude (Reflection) ─────────────────────────
    CLAUDE_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 2048
    CLAUDE_TEMPERATURE: float = 0.0
    CLAUDE_TIMEOUT: int = 60

    # ── Retry / Resilience ──────────────────────────
    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: float = 1.0

    # ── Logging ─────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
