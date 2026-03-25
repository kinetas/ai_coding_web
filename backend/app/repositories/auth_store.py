from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.security import hash_password, hash_token
from backend.app.db_models import AuthSession, SavedBuilderAnalysis, User


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

  def get_user_by_supabase_uid(self, supabase_uid: str) -> dict | None:
    with self._session_factory() as db:
      user = db.scalar(select(User).where(User.supabase_uid == supabase_uid))
      return self._to_user(user) if user else None

  def upsert_user_from_supabase(self, supabase_uid: str, email: str, nickname: str) -> dict:
    """Supabase JWT(sub)와 동기화. 로컬 데모 사용자(이메일만 겹침)는 supabase_uid를 채워 연결."""
    normalized_email = (email or "").strip().lower()
    if "@" not in normalized_email:
      raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="유효한 이메일이 필요합니다.")
    nick = (nickname or "").strip() or normalized_email.split("@")[0]

    with self._session_factory() as db:
      user = db.scalar(select(User).where(User.supabase_uid == supabase_uid))
      if user:
        changed = False
        if user.email != normalized_email:
          other = db.scalar(select(User).where(User.email == normalized_email, User.id != user.id))
          if other:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")
          user.email = normalized_email
          changed = True
        if nick and user.nickname != nick:
          user.nickname = nick
          changed = True
        if changed:
          db.commit()
          db.refresh(user)
        return self._to_user(user)

      existing = db.scalar(select(User).where(User.email == normalized_email))
      if existing:
        if existing.supabase_uid and existing.supabase_uid != supabase_uid:
          raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이메일이 다른 Supabase 계정과 연결되어 있습니다.")
        existing.supabase_uid = supabase_uid
        if nick:
          existing.nickname = nick
        db.commit()
        db.refresh(existing)
        return self._to_user(existing)

      placeholder_hash = hash_password(secrets.token_hex(32))
      row = User(
        email=normalized_email,
        nickname=nick,
        password_hash=placeholder_hash,
        status="active",
        supabase_uid=supabase_uid,
      )
      db.add(row)
      db.commit()
      db.refresh(row)
      return self._to_user(row)

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
    """로컬 SQLite 사용자 및 연관 세션·저장 분석 삭제."""
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
      "supabase_uid": getattr(user, "supabase_uid", None),
      "email": user.email,
      "nickname": user.nickname,
      "status": getattr(user, "status", "active"),
      "created_at": user.created_at.isoformat() if user.created_at else "",
      "updated_at": user.updated_at.isoformat() if getattr(user, "updated_at", None) else "",
    }
    if include_password:
      data["password_hash"] = user.password_hash
    return data
