"""Environment configuration, loaded via pydantic-settings.

Nothing here is required to run the scanner against the synthetic environment or
the offline storage fallback — every field has a safe default. Real values come
from a local .env file (never committed).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase — optional. If unset, storage falls back to a local JSON file.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # Storage backend selection: "auto" (default, falls back to local JSON) or
    # "supabase" (requires supabase_configured). Kept in Settings so all config
    # flows through one place rather than a stray os.getenv.
    storage_backend: str = "auto"

    # API key gate. Empty (the default) means auth is DISABLED — every endpoint is
    # open, which keeps local dev and the zero-setup demo frictionless. Set this
    # (env: API_KEY) before exposing the API beyond localhost: real-credential scans
    # and every write then require the key in the `X-API-Key` header. The synthetic
    # demo scan and all reads stay open so the public /demo keeps working.
    api_key: str = ""

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Scoring
    inactivity_days: int = 90

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def auth_enabled(self) -> bool:
        """True once an API key is configured; otherwise the API is open."""
        return bool(self.api_key)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
