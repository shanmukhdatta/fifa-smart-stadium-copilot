"""
Centralized application configuration.

All environment-dependent values live here and ONLY here. No module in the
codebase should call os.environ directly -- they import `settings` from
this module. This keeps configuration auditable and testable (tests can
monkeypatch `settings` instead of touching the real environment).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = "sk-placeholder-for-local-dev"
    llm_model: str = "gpt-4o-mini"

    # Auth
    jwt_secret_key: str = "insecure-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # App
    app_env: str = "development"
    rate_limit_per_minute: int = 30
    cors_allowed_origins: list[str] = ["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:8000"]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor -- avoids re-parsing env on every call."""
    return Settings()


settings = get_settings()
