"""Application configuration.

Values are read from environment variables or from a `.env` file placed in the
`backend` folder. See `.env.example` for every supported setting.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "I-ITSM"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    database_url: str = f"sqlite:///{(BASE_DIR / 'itsm.db').as_posix()}"

    secret_key: str = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    frontend_origin: str = "http://localhost:5173"

    sla_monitor_enabled: bool = True
    sla_monitor_interval_seconds: int = 60
    sla_warning_percent: int = 75
    default_technician_workload_limit: int = 5
    duplicate_similarity_threshold: float = 0.45

    seed_demo_data: bool = True
    bcrypt_rounds: int = 12

    # Used only when SEED_DEMO_DATA=false and the database has no users yet: the very first
    # administrator account plus the standard categories, services and SLA policies are created.
    initial_admin_email: str | None = None
    initial_admin_password: str | None = None
    initial_admin_name: str = "System Administrator"

    @property
    def uses_default_secret(self) -> bool:
        return self.secret_key == "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
