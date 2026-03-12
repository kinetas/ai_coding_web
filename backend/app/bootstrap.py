from __future__ import annotations

from sqlalchemy import select

from backend.app.config import get_settings
from backend.app.core.security import hash_password
from backend.app.db import Base, SessionLocal, engine
from backend.app.db_models import User
from backend.app.repositories.memory_store import ContentStore


def init_database() -> None:
  settings = get_settings()
  Base.metadata.create_all(bind=engine)

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
        name="Demo User",
        password_hash=hash_password(settings.auth_demo_user_password),
      )
    )
    db.commit()
