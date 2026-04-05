from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from backend.app.core.security import hash_token
from backend.app.db_models import AuthSession, User


class AuthStore:
  def __init__(self, session_factory: sessionmaker):
    self._session_factory = session_factory

  def create_user(self, email: str, nickname: str, password_hash: str, status: str = "active") -> dict:
    with self._session_factory() as db:
      user = User(email=email, nickname=nickname, password_hash=password_hash, status=status)
      db.add(user)
      db.commit()
      db.refresh(user)
      return self._to_user(user)

  def get_user_by_email(self, email: str) -> dict | None:
    with self._session_factory() as db:
      user = db.scalar(select(User).where(User.email == email))
      return self._to_user(user) if user else None

  def get_user_with_password_by_email(self, email: str) -> dict | None:
    with self._session_factory() as db:
      user = db.scalar(select(User).where(User.email == email))
      return self._to_user(user, include_password=True) if user else None

  def create_session(self, user_id: int, raw_token: str, ttl_hours: int) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    token_hash = hash_token(raw_token)
    with self._session_factory() as db:
      db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
      db.add(AuthSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at))
      db.commit()

  def get_user_by_session_token(self, raw_token: str) -> dict | None:
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    with self._session_factory() as db:
      session = db.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == token_hash)
        .where(AuthSession.expires_at > now)
      )
      if not session:
        return None
      return self._to_user(session.user)

  def delete_session(self, raw_token: str) -> None:
    token_hash = hash_token(raw_token)
    with self._session_factory() as db:
      db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))
      db.commit()

  def delete_expired_sessions(self) -> None:
    now = datetime.now(timezone.utc)
    with self._session_factory() as db:
      db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
      db.commit()

  def delete_local_user_by_id(self, user_id: int) -> bool:
    from backend.app.db_models import SavedBuilderAnalysis
    with self._session_factory() as db:
      user = db.get(User, user_id)
      if not user:
        return False
      db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
      db.execute(delete(SavedBuilderAnalysis).where(SavedBuilderAnalysis.user_id == user_id))
      db.delete(user)
      db.commit()
      return True

  @staticmethod
  def _to_user(user: User, include_password: bool = False) -> dict:
    data = {
      "id": user.id,
      "email": user.email,
      "nickname": user.nickname,
      "status": getattr(user, "status", "active"),
      "created_at": user.created_at.isoformat() if user.created_at else "",
      "updated_at": user.updated_at.isoformat() if getattr(user, "updated_at", None) else "",
    }
    if include_password:
      data["password_hash"] = user.password_hash
    return data
