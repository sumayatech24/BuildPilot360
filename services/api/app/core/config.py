"""Application settings, loaded from environment / .env (database & API driven, no hardcoded secrets)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BuildPilot360 API"
    environment: str = "development"

    database_url: str = "sqlite:///./buildpilot360.db"
    # Optional dedicated Postgres schema to isolate tables on a shared database.
    db_schema: str = ""

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    cors_origins: str = "http://localhost:5173,http://localhost:4173,app://."

    ai_provider: str = "stub"
    ai_api_key: str = ""
    ai_model: str = ""

    # Auto-create tables + seed master/config + load the blueprint on first boot.
    # Lets a hosted deploy come up populated with no manual step.
    seed_on_start: bool = False

    seed_owner_email: str = "owner@buildpilot360.dev"
    seed_owner_password: str = "ChangeMe123!"
    seed_tenant_name: str = "BuildPilot360"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
