"""
Application Configuration and Environment Settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM Settings
    LLM_PROVIDER: str = "gemini"  # 'gemini', 'openai', or 'mock'
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Database Settings (Read-Only user)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "smart_meter_dw"
    POSTGRES_USER: str = "nl2sql_readonly"
    POSTGRES_PASSWORD: str = "readonly_secure_pass_2026"
    POSTGRES_SCHEMA: str = "analytics_mart"

    # Security & Guardrails
    MAX_ROW_LIMIT: int = 100
    STATEMENT_TIMEOUT_MS: int = 5000
    ENABLE_MOCK_FALLBACK: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
