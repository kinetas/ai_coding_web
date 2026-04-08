from __future__ import annotations

from fastapi import HTTPException, status

from backend.app.config import Settings
from backend.app.core.security import generate_session_token, hash_password, verify_password
from backend.app.repositories.auth_store import AuthStore


class AuthService:
  def __init__(self, store: AuthStore, settings: Settings):
    self._store = store
    self._settings = settings

  def register(self, email: str, nickname: str, password: str) -> tuple[dict, str]:
    normalized_email = self._normalize_email(email)
    if self._store.get_user_by_email(normalized_email):
      raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")

    user = self._store.create_user(
      email=normalized_email,
      nickname=nickname.strip(),
      password_hash=hash_password(password),
      status="active",
    )
    token = generate_session_token()
    self._store.create_session(user["id"], token, self._settings.auth_session_ttl_hours)
    return user, token

  def login(self, email: str, password: str) -> tuple[dict, str]:
    normalized_email = self._normalize_email(email)
    user = self._store.get_user_with_password_by_email(normalized_email)
    if not user or not verify_password(password, user["password_hash"]):
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    if user.get("status") and user["status"] != "active":
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다.")

    token = generate_session_token()
    self._store.create_session(user["id"], token, self._settings.auth_session_ttl_hours)
    return self._public_user(user), token

  def get_user_by_session(self, token: str | None) -> dict | None:
    if not token:
      return None
    self._store.delete_expired_sessions()
    return self._store.get_user_by_session_token(token)

  def update_nickname(self, user_id: int, nickname: str) -> dict:
    user = self._store.update_nickname(user_id, nickname.strip())
    if not user:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user

  def delete_account(self, user_id: int, token: str | None) -> None:
    if token:
      self._store.delete_session(token)
    self._store.delete_local_user_by_id(user_id)

  def logout(self, token: str | None) -> None:
    if token:
      self._store.delete_session(token)

  @staticmethod
  def _normalize_email(email: str) -> str:
    value = (email or "").strip().lower()
    if "@" not in value or "." not in value.split("@")[-1]:
      raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="유효한 이메일 주소를 입력해 주세요.")
    return value

  @staticmethod
  def _public_user(user: dict) -> dict:
    return {
      "id": user["id"],
      "email": user["email"],
      "nickname": user.get("nickname") or "",
      "status": user.get("status") or "active",
      "created_at": user.get("created_at", ""),
      "updated_at": user.get("updated_at", ""),
    }
