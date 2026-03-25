from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status

import jwt
from jwt import PyJWTError

from backend.app.config import Settings, get_settings
from backend.app.core.jwt_debug import log_jwt_verify_failure, safe_jwt_preview_for_log
from backend.app.core.supabase_jwt import decode_supabase_access_token
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


def _bearer_token(authorization: str | None) -> str | None:
  if not authorization:
    return None
  prefix = "Bearer "
  if not authorization.startswith(prefix):
    return None
  raw = authorization[len(prefix) :].strip()
  return raw or None


def get_current_user(
  request: Request,
  authorization: Annotated[str | None, Header()] = None,
  settings: Settings = Depends(get_settings),
  auth_service: AuthService = Depends(get_auth_service),
  auth_store: AuthStore = Depends(get_auth_store),
) -> dict:
  bearer = _bearer_token(authorization)
  if bearer:
    try:
      hdr = jwt.get_unverified_header(bearer)
      token_alg = str(hdr.get("alg") or "HS256").upper()
    except Exception:
      token_alg = "HS256"
    if token_alg == "HS256" and not settings.supabase_jwt_secret:
      raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="서버에 SUPABASE_JWT_SECRET이 설정되지 않았습니다. Dashboard → Settings → API의 JWT 서명 비밀값을 넣어 주세요.",
      )
    if token_alg != "HS256" and not settings.supabase_jwt_issuer:
      raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="비대칭 JWT(RS256 등) 검증에는 SUPABASE_URL(또는 SUPABASE_JWT_ISSUER)이 필요합니다. JWKS URL로 공개 키를 불러옵니다.",
      )
    verify_mode = "hs256_secret" if token_alg == "HS256" else "jwks_asymmetric"
    jwks_url = None
    if settings.supabase_jwt_issuer:
      jwks_url = f"{settings.supabase_jwt_issuer.rstrip('/')}/.well-known/jwks.json"
    try:
      payload = decode_supabase_access_token(
        bearer,
        secret=settings.supabase_jwt_secret,
        issuer=settings.supabase_jwt_issuer,
      )
    except (PyJWTError, ValueError) as exc:
      log_jwt_verify_failure(
        token_alg=token_alg,
        verify_mode=verify_mode,
        exc=exc,
        settings_app_env=settings.app_env,
        expected_jwt_issuer=settings.supabase_jwt_issuer,
        jwks_url=jwks_url,
      )
      if settings.app_env.lower() == "development":
        preview = safe_jwt_preview_for_log(bearer)
        logger.warning("JWT 미검증 요약(개발 전용, 서명 무시): %s", preview)
      detail = "유효하지 않거나 만료된 토큰입니다."
      if settings.app_env.lower() == "development":
        detail = f"{detail} ({type(exc).__name__}: {exc!s})"
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail) from exc
    sub = str(payload.get("sub") or "").strip()
    if not sub:
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰에 사용자 정보가 없습니다.")
    meta = payload.get("user_metadata") if isinstance(payload.get("user_metadata"), dict) else {}
    app_meta = payload.get("app_metadata") if isinstance(payload.get("app_metadata"), dict) else {}
    email = str(
      payload.get("email") or meta.get("email") or app_meta.get("email") or ""
    ).strip()
    nickname = str(meta.get("full_name") or meta.get("nickname") or "").strip()
    if not email:
      if settings.app_env.lower() == "development":
        logger.warning(
          "JWT에 이메일 클레임 없음(개발) | payload_keys=%s",
          sorted(payload.keys())[:30],
        )
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰에 이메일이 없습니다.")
    return auth_store.upsert_user_from_supabase(sub, email, nickname)

  token = request.cookies.get(settings.auth_cookie_name)
  user = auth_service.get_user_by_session(token)
  if not user:
    if settings.app_env.lower() == "development":
      logger.warning(
        "인증 실패: Authorization Bearer 없음 + 유효한 세션 쿠키 없음 | path=%s",
        request.url.path,
      )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
  return user


def require_etl_token(
  x_etl_token: str | None = Header(default=None),
  settings: Settings = Depends(get_settings),
) -> None:
  if settings.etl_shared_secret and x_etl_token == settings.etl_shared_secret:
    return
  raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효한 ETL 토큰이 필요합니다.")
