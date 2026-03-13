from __future__ import annotations

from sqlalchemy import text
from sqlalchemy import select

from backend.app.config import get_settings
from backend.app.core.security import hash_password
from backend.app.db import Base, SessionLocal, engine
from backend.app.db_models import User
from backend.app.repositories.memory_store import ContentStore


def init_database() -> None:
  settings = get_settings()
  Base.metadata.create_all(bind=engine)
  _migrate_sqlite_schema()

  content_store = ContentStore(SessionLocal)
  content_store.seed_defaults()

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


def _migrate_sqlite_schema() -> None:
  """
  data.md 단계(1) 기준으로 필드명을 정리하기 위한 최소 마이그레이션.
  SQLite 개발 환경에서만 동작하도록 가볍게 처리합니다.
  """
  if not str(engine.url).startswith("sqlite"):
    return

  with engine.begin() as conn:
    exists = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")).fetchone()
    if not exists:
      return

    cols = conn.execute(text("PRAGMA table_info(users)")).fetchall()
    col_names = {row[1] for row in cols}  # row[1] = name

    # name -> nickname
    if "name" in col_names and "nickname" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users RENAME COLUMN name TO nickname")
      col_names.remove("name")
      col_names.add("nickname")

    # add status
    if "status" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'")
      col_names.add("status")

    # add updated_at
    if "updated_at" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
      col_names.add("updated_at")
