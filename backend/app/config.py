from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _parse_bool(value: str | None, default: bool) -> bool:
  if value is None:
    return default
  return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None) -> list[str]:
  if not value:
    return []
  return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
  app_env: str
  app_name: str
  app_version: str
  database_url: str
  cors_allowed_origins: list[str]
  auth_cookie_name: str
  auth_cookie_secure: bool
  auth_cookie_samesite: str
  auth_session_ttl_hours: int
  auth_seed_demo_user: bool
  auth_demo_user_email: str
  auth_demo_user_password: str
  etl_shared_secret: str

  @property
  def is_production(self) -> bool:
    return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
  app_env = os.getenv("APP_ENV", "development").strip() or "development"
  default_origins = "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:3000,http://localhost:3000"
  return Settings(
    app_env=app_env,
    app_name=os.getenv("APP_NAME", "Et Demo API").strip() or "Et Demo API",
    app_version=os.getenv("APP_VERSION", "1.0.0").strip() or "1.0.0",
    database_url=os.getenv("DATABASE_URL", "sqlite:///./et_demo.db").strip() or "sqlite:///./et_demo.db",
    cors_allowed_origins=_parse_csv(os.getenv("CORS_ALLOWED_ORIGINS", default_origins)),
    auth_cookie_name=os.getenv("AUTH_COOKIE_NAME", "et_session").strip() or "et_session",
    auth_cookie_secure=_parse_bool(os.getenv("AUTH_COOKIE_SECURE"), app_env.lower() == "production"),
    auth_cookie_samesite=os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower() or "lax",
    auth_session_ttl_hours=max(1, int(os.getenv("AUTH_SESSION_TTL_HOURS", "168"))),
    auth_seed_demo_user=_parse_bool(os.getenv("AUTH_SEED_DEMO_USER"), True),
    auth_demo_user_email=os.getenv("AUTH_DEMO_USER_EMAIL", "demo@et.ai").strip() or "demo@et.ai",
    auth_demo_user_password=os.getenv("AUTH_DEMO_USER_PASSWORD", "etl1234").strip() or "etl1234",
    etl_shared_secret=os.getenv("ETL_SHARED_SECRET", "").strip(),
  )
