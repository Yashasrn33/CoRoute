"""Application configuration, loaded from environment / repo-root .env.

See .env.example at the repo root for the full set of variables and the
privacy-relevant split between the RLS-subject role (DATABASE_URL) and the
isolated synthesis reader (DATABASE_URL_SYNTHESIS).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# repo root = two levels up from this file (backend/app/core/config.py)
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_base_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"
    log_level: str = "info"

    # Database
    # Request-path role: must be RLS-subject (no BYPASSRLS). Privacy invariant #2.
    database_url: str = (
        "postgresql+asyncpg://localhost:5432/coroute"
    )
    # Isolated AI-synthesis reader (BYPASSRLS). Server-side synthesis ONLY. Invariant #3.
    database_url_synthesis: str | None = None
    # Migration runner / table owner (sync psycopg driver, used by Alembic only).
    database_url_migrate: str | None = None

    # Auth (magic-link JWT)
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expires_minutes: int = 43200
    magic_link_ttl_minutes: int = 15

    # LLM provider for option synthesis.
    #   auto  -> anthropic if a key is set, else stub
    #   anthropic | ollama | stub  -> force that provider
    llm_provider: str = "auto"

    # Claude API — model IDs verified against the claude-api skill.
    anthropic_api_key: str | None = None
    claude_model: str = "claude-opus-4-8"
    claude_model_cheap: str = "claude-sonnet-4-6"

    # Ollama (local models, e.g. phi3:mini). Used when llm_provider=ollama.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi3:mini"

    def resolve_llm_provider(self) -> str:
        if self.llm_provider != "auto":
            return self.llm_provider
        return "anthropic" if self.anthropic_api_key else "stub"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
