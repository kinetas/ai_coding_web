from __future__ import annotations

from sqlalchemy import text
from sqlalchemy import select

from backend.app.config import get_settings
from backend.app.core.security import hash_password
from backend.app.db import Base, SessionLocal, engine
from backend.app.db_models import User
from backend.app.repositories.memory_store import ContentStore


def init_database() -> None:
  Base.metadata.create_all(bind=engine)
  _migrate_schema()

  ContentStore(SessionLocal).seed_defaults()

  settings = get_settings()
  if not settings.auth_seed_demo_user:
    return

  with SessionLocal() as db:
    existing = db.scalar(select(User).where(User.email == settings.auth_demo_user_email))
    if existing:
      return
    db.add(
      User(
        email=settings.auth_demo_user_email,
        nickname="Demo User",
        status="active",
        password_hash=hash_password(settings.auth_demo_user_password),
      )
    )
    db.commit()


def _migrate_schema() -> None:
  url = str(engine.url)
  if url.startswith("sqlite"):
    _migrate_sqlite()
  else:
    _migrate_postgres()


def _migrate_sqlite() -> None:
  """SQLite 개발 환경 경량 마이그레이션."""
  with engine.begin() as conn:
    exists = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")).fetchone()
    if not exists:
      return

    cols = conn.execute(text("PRAGMA table_info(users)")).fetchall()
    col_names = {row[1] for row in cols}

    # name → nickname
    if "name" in col_names and "nickname" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users RENAME COLUMN name TO nickname")
      col_names.discard("name")
      col_names.add("nickname")

    # status 추가
    if "status" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'")
      col_names.add("status")

    # updated_at 추가
    if "updated_at" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
      col_names.add("updated_at")

    # supabase_uid 제거 (있으면, SQLite 3.35.0+ 지원)
    if "supabase_uid" in col_names:
      try:
        conn.exec_driver_sql("ALTER TABLE users DROP COLUMN supabase_uid")
        conn.exec_driver_sql("DROP INDEX IF EXISTS ix_users_supabase_uid")
      except Exception:
        pass


def _migrate_postgres() -> None:
  """PostgreSQL 운영 환경 마이그레이션."""
  with engine.begin() as conn:
    result = conn.execute(text(
      "SELECT column_name FROM information_schema.columns "
      "WHERE table_name='users' AND column_name='supabase_uid'"
    ))
    if result.fetchone():
      conn.execute(text("ALTER TABLE users DROP COLUMN supabase_uid"))
