"""
Settings loaded from .env via pydantic-settings.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(..., description="OpenAI API key")
    agent_model: str = Field("gpt-4o")
    agent_temperature: float = Field(0.0)
    agent_max_iterations: int = Field(25)

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_pat: str = Field("", description="GitHub personal access token")
    github_default_owner: str = Field("", description="Default GitHub owner/org")

    # ── Postgres ──────────────────────────────────────────────────────────────
    postgres_host: str = Field("localhost")
    postgres_port: int = Field(5432)
    postgres_user: str = Field("ops_user")
    postgres_password: str = Field("ops_password")
    postgres_db: str = Field("ops_db")

    # ── Notion ────────────────────────────────────────────────────────────────
    notion_api_key: str = Field("", description="Notion integration token")
    notion_notes_database_id: str = Field("", description="Notion DB ID for notes")

    # ── Local Files ───────────────────────────────────────────────────────────
    local_files_root: Path = Field(
        Path("D:/personal_ops"),
        description="Root path the filesystem server can access",
    )

    @field_validator("local_files_root", mode="before")
    @classmethod
    def parse_path(cls, v: str) -> Path:
        return Path(v).expanduser().resolve()

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
