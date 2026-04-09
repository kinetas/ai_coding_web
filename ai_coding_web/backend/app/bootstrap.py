from __future__ import annotations

from sqlalchemy import text
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError

from backend.app.config import get_settings
from backend.app.core.security import hash_password
from backend.app.db import Base, SessionLocal, engine
from backend.app.db_models import User
from backend.app.repositories.builder_store import BuilderStore
from backend.app.repositories.memory_store import ContentStore


def init_database() -> None:
  Base.metadata.create_all(bind=engine)
  _migrate_schema()

  ContentStore(SessionLocal).seed_defaults()
  BuilderStore(SessionLocal).seed_catalog_if_empty()

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
  """SQLite lightweight migrations."""
  with engine.begin() as conn:
    exists = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")).fetchone()
    if not exists:
      return

    cols = conn.execute(text("PRAGMA table_info(users)")).fetchall()
    col_names = {row[1] for row in cols}

    # name -> nickname
    if "name" in col_names and "nickname" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users RENAME COLUMN name TO nickname")
      col_names.discard("name")
      col_names.add("nickname")

    # add status
    if "status" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'")
      col_names.add("status")

    # add updated_at
    if "updated_at" not in col_names:
      conn.exec_driver_sql("ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
      col_names.add("updated_at")

    # drop supabase_uid if present (SQLite 3.35+)
    if "supabase_uid" in col_names:
      try:
        conn.exec_driver_sql("ALTER TABLE users DROP COLUMN supabase_uid")
        conn.exec_driver_sql("DROP INDEX IF EXISTS ix_users_supabase_uid")
      except Exception:
        pass

    exists_saved = conn.execute(
      text("SELECT name FROM sqlite_master WHERE type='table' AND name='saved_builder_analyses'")
    ).fetchone()
    if exists_saved:
      sb_cols = conn.execute(text("PRAGMA table_info(saved_builder_analyses)")).fetchall()
      sb_names = {row[1] for row in sb_cols}
      if "category_label" not in sb_names:
        conn.exec_driver_sql(
          "ALTER TABLE saved_builder_analyses ADD COLUMN category_label VARCHAR(40) NOT NULL DEFAULT ''"
        )

    exists_bc = conn.execute(
      text("SELECT name FROM sqlite_master WHERE type='table' AND name='builder_keyword_catalog'")
    ).fetchone()
    if exists_bc:
      bc_cols = conn.execute(text("PRAGMA table_info(builder_keyword_catalog)")).fetchall()
      bc_names = {row[1] for row in bc_cols}
      if "분류" in bc_names:
        conn.exec_driver_sql('ALTER TABLE builder_keyword_catalog RENAME COLUMN "분류" TO classification')

    # agri_price_history: grd_cd / se_cd 추가 (가이드 4-1 시계열 식별 키)
    exists_aph = conn.execute(
      text("SELECT name FROM sqlite_master WHERE type='table' AND name='agri_price_history'")
    ).fetchone()
    if exists_aph:
      aph_cols = conn.execute(text("PRAGMA table_info(agri_price_history)")).fetchall()
      aph_names = {row[1] for row in aph_cols}
      if "grd_cd" not in aph_names:
        conn.exec_driver_sql("ALTER TABLE agri_price_history ADD COLUMN grd_cd VARCHAR(32)")
      if "se_cd" not in aph_names:
        conn.exec_driver_sql("ALTER TABLE agri_price_history ADD COLUMN se_cd VARCHAR(32)")

    _migrate_legacy_korean_labels(conn)


def _migrate_postgres() -> None:
  """PostgreSQL production migrations."""
  with engine.begin() as conn:
    result = conn.execute(text(
      "SELECT column_name FROM information_schema.columns "
      "WHERE table_name='users' AND column_name='supabase_uid'"
    ))
    if result.fetchone():
      conn.execute(text("ALTER TABLE users DROP COLUMN supabase_uid"))

    r_cat = conn.execute(
      text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='saved_builder_analyses' "
        "AND column_name='category_label'"
      )
    )
    if not r_cat.fetchone():
      conn.execute(
        text(
          "ALTER TABLE saved_builder_analyses ADD COLUMN category_label VARCHAR(40) NOT NULL DEFAULT ''"
        )
      )
      conn.execute(
        text(
          "CREATE INDEX IF NOT EXISTS ix_saved_builder_analyses_category_label "
          "ON saved_builder_analyses (category_label)"
        )
      )

    has_bc = conn.execute(
      text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='builder_keyword_catalog')"
      )
    ).scalar()
    if has_bc:
      cols = conn.execute(
        text(
          "SELECT column_name FROM information_schema.columns "
          "WHERE table_schema='public' AND table_name='builder_keyword_catalog'"
        )
      ).fetchall()
      colset = {row[0] for row in cols}
      if "분류" in colset:
        conn.execute(text('ALTER TABLE builder_keyword_catalog RENAME COLUMN "분류" TO classification'))

    # agri_price_history: grd_cd / se_cd 추가
    r_aph = conn.execute(
      text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='agri_price_history')"
      )
    ).scalar()
    if r_aph:
      aph_cols = conn.execute(
        text(
          "SELECT column_name FROM information_schema.columns "
          "WHERE table_schema='public' AND table_name='agri_price_history'"
        )
      ).fetchall()
      aph_names = {row[0] for row in aph_cols}
      if "grd_cd" not in aph_names:
        conn.execute(text("ALTER TABLE agri_price_history ADD COLUMN grd_cd TEXT"))
      if "se_cd" not in aph_names:
        conn.execute(text("ALTER TABLE agri_price_history ADD COLUMN se_cd TEXT"))

    _migrate_legacy_korean_labels(conn)


def _migrate_legacy_korean_labels(conn) -> None:
  """Map legacy Korean labels to English slugs (saved analyses + keyword catalog)."""
  mapping = {
    "농산물 시세": "agri_prices",
    "의료": "health",
    "교통": "traffic",
    "관광": "tourism",
    "환경": "environment",
  }
  for old, new in mapping.items():
    conn.execute(
      text("UPDATE saved_builder_analyses SET category_label = :new WHERE category_label = :old"),
      {"new": new, "old": old},
    )
  try:
    for old, new in mapping.items():
      conn.execute(
        text("UPDATE builder_keyword_catalog SET classification = :new WHERE classification = :old"),
        {"new": new, "old": old},
      )
  except (ProgrammingError, OperationalError):
    pass
