"""Application configuration, loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Switchyard backend.

    All values have safe local-development defaults. Nothing here should
    ever hold a real secret — actual keys are supplied via environment
    variables or a local .env file (see .env.example), never committed.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "switchyard"
    environment: str = "development"
    debug: bool = True

    database_url: str = "sqlite:///./switchyard.db"

    # Provider API keys are optional in development: the mock provider
    # does not require any of these.
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None

    # Overrides the default (repo-root)/benchmarks/tasks directory.
    # Mainly used by tests to point at a fixture directory instead.
    benchmarks_dir: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
