from __future__ import annotations

import logging

from fastapi import Depends, Header, HTTPException, Request, Response, status

from backend.app.config import Settings, get_settings
from backend.app.db import SessionLocal
from backend.app.repositories.auth_store import AuthStore
from backend.app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


def set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
  response.set_cookie(
    key=settings.auth_cookie_name,
    value=token,
    httponly=True,
    secure=settings.auth_cookie_secure,
    samesite=settings.auth_cookie_samesite,
    max_age=settings.auth_session_ttl_hours * 3600,
    path="/",
  )


def clear_auth_cookie(response: Response, settings: Settings) -> None:
  response.delete_cookie(key=settings.auth_cookie_name, path="/")


def get_auth_store() -> AuthStore:
  return AuthStore(SessionLocal)


def get_auth_service(
  store: AuthStore = Depends(get_auth_store),
  settings: Settings = Depends(get_settings),
) -> AuthService:
  return AuthService(store, settings)


def get_session_token(
  request: Request,
  settings: Settings = Depends(get_settings),
) -> str | None:
  return request.cookies.get(settings.auth_cookie_name)


def get_current_user(
  request: Request,
  settings: Settings = Depends(get_settings),
  auth_service: AuthService = Depends(get_auth_service),
) -> dict:
  token = request.cookies.get(settings.auth_cookie_name)
  user = auth_service.get_user_by_session(token)
  if not user:
    if settings.app_env.lower() == "development":
      logger.warning("인증 실패: 유효한 세션 쿠키 없음 | path=%s", request.url.path)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
  return user


def require_etl_token(
  x_etl_token: str | None = Header(default=None),
  settings: Settings = Depends(get_settings),
) -> None:
  if settings.etl_shared_secret and x_etl_token == settings.etl_shared_secret:
    return
  raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효한 ETL 토큰이 필요합니다.")
