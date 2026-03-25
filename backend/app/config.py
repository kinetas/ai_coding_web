from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _project_root() -> Path:
  """`ai_coding_web` (backend의 상위 디렉터리). cwd와 무관하게 고정."""
  return Path(__file__).resolve().parent.parent.parent


def _load_dotenv_file() -> None:
  """프로젝트 루트 `ai_coding_web/.env` 를 로드합니다. 로컬 파일 값이 우선합니다(override=True)."""
  try:
    from dotenv import load_dotenv
  except ImportError:
    return
  env_path = _project_root() / ".env"
  if env_path.is_file():
    load_dotenv(env_path, override=True)


_load_dotenv_file()


def _normalize_database_url(url: str) -> str:
  """
  SQLite에서 `./foo.db` 같은 상대 경로는 기본적으로 cwd 기준이라 실행 위치마다 DB가 달라집니다.
  상대 경로는 항상 프로젝트 루트 기준으로 해석합니다.
  """
  url = url.strip()
  if not url.startswith("sqlite:///"):
    return url
  prefix = "sqlite:///"
  path_part = url[len(prefix) :]
  if not path_part:
    return url
  p = Path(path_part)
  if p.is_absolute():
    return url
  resolved = (_project_root() / p).resolve()
  return f"sqlite:///{resolved.as_posix()}"


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
  supabase_url: str
  supabase_anon_key: str
  supabase_jwt_secret: str
  supabase_jwt_issuer: str | None
  supabase_service_role_key: str
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
  raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./et_demo.db").strip() or "sqlite:///./et_demo.db"
  supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
  supabase_anon_key = (os.getenv("SUPABASE_ANON_KEY") or "").strip()
  jwt_secret = (os.getenv("SUPABASE_JWT_SECRET") or "").strip()
  jwt_issuer_env = (os.getenv("SUPABASE_JWT_ISSUER") or "").strip()
  jwt_issuer: str | None = jwt_issuer_env or None
  if not jwt_issuer and supabase_url:
    base = supabase_url.rstrip("/")
    jwt_issuer = f"{base}/auth/v1"
  return Settings(
    app_env=app_env,
    app_name=os.getenv("APP_NAME", "Et Demo API").strip() or "Et Demo API",
    app_version=os.getenv("APP_VERSION", "1.0.0").strip() or "1.0.0",
    database_url=_normalize_database_url(raw_db_url),
    supabase_url=supabase_url,
    supabase_anon_key=supabase_anon_key,
    supabase_jwt_secret=jwt_secret,
    supabase_jwt_issuer=jwt_issuer,
    supabase_service_role_key=(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip(),
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


# .env 를 먼저 읽은 뒤 캐시를 비워, uvicorn 재시작 시 항상 디스크의 .env 기준이 되도록 함
get_settings.cache_clear()
