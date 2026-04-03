from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from backend.app.auth import clear_auth_cookie, get_auth_service, get_auth_store, get_current_user, get_session_token, set_auth_cookie
from backend.app.config import Settings, get_settings
from backend.app.models.auth import (
  AuthSessionResponse,
  LoginPayload,
  RegisterPayload,
  SupabaseRefreshPayload,
  SupabaseSignInPayload,
  SupabaseSignUpPayload,
  SupabaseUserUpdatePayload,
  UserResponse,
)
from backend.app.repositories.auth_store import AuthStore
from backend.app.services.auth_service import AuthService
from backend.app.services.supabase_admin import delete_supabase_auth_user
from backend.app.services.supabase_auth_proxy import (
  refresh_session as supabase_refresh_session,
  sign_in_with_password,
  sign_out as supabase_sign_out,
  sign_up as supabase_sign_up,
  update_user as supabase_update_user,
)


router = APIRouter()
# Supabase 이메일 로그인/가입/로그아웃/갱신/프로필은 /auth/supabase/* 로 백엔드가 Auth REST에 프록시합니다.
# /auth/register·/auth/login 은 로컬 SQLite 세션용 레거시입니다.


@router.get("/config/public")
def public_supabase_config(settings: Settings = Depends(get_settings)) -> dict[str, str]:
  """프론트의 config.js와 동일 값을 맞추기 위한 공개 설정(anon 키는 원래 공개용)."""
  return {
    "supabaseUrl": settings.supabase_url or "",
    "supabaseAnonKey": settings.supabase_anon_key or "",
  }


@router.post("/auth/supabase/sign-in")
def supabase_sign_in(payload: SupabaseSignInPayload, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
  return sign_in_with_password(settings, payload.email, payload.password)


@router.post("/auth/supabase/sign-up")
def supabase_sign_up_route(payload: SupabaseSignUpPayload, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
  return supabase_sign_up(settings, payload.email, payload.password, payload.nickname)


@router.post("/auth/supabase/sign-out")
def supabase_sign_out_route(
  authorization: Annotated[str | None, Header()] = None,
  settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
  if not authorization or not authorization.startswith("Bearer "):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer 토큰이 필요합니다.")
  supabase_sign_out(settings, authorization[len("Bearer ") :].strip())
  return {"ok": True}


@router.post("/auth/supabase/refresh")
def supabase_refresh(payload: SupabaseRefreshPayload, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
  return supabase_refresh_session(settings, payload.refresh_token)


@router.patch("/auth/supabase/user")
def supabase_patch_user(
  payload: SupabaseUserUpdatePayload,
  authorization: Annotated[str | None, Header()] = None,
  settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
  if not authorization or not authorization.startswith("Bearer "):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer 토큰이 필요합니다.")
  return supabase_update_user(
    settings,
    authorization[len("Bearer ") :].strip(),
    payload.email,
    payload.nickname,
  )


@router.post("/auth/register", response_model=AuthSessionResponse)
def register(
  payload: RegisterPayload,
  response: Response,
  settings: Settings = Depends(get_settings),
  auth_service: AuthService = Depends(get_auth_service),
):
  user, token = auth_service.register(payload.email, payload.nickname, payload.password)
  set_auth_cookie(response, token, settings)
  return {"ok": True, "user": user}


@router.post("/auth/login", response_model=AuthSessionResponse)
def login(
  payload: LoginPayload,
  response: Response,
  settings: Settings = Depends(get_settings),
  auth_service: AuthService = Depends(get_auth_service),
):
  user, token = auth_service.login(payload.email, payload.password)
  set_auth_cookie(response, token, settings)
  return {"ok": True, "user": user}


@router.post("/auth/logout")
def logout(
  response: Response,
  token: str | None = Depends(get_session_token),
  settings: Settings = Depends(get_settings),
  auth_service: AuthService = Depends(get_auth_service),
):
  auth_service.logout(token)
  clear_auth_cookie(response, settings)
  return {"ok": True}


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
  return current_user


@router.delete("/auth/account")
def delete_account(
  authorization: Annotated[str | None, Header()] = None,
  settings: Settings = Depends(get_settings),
  auth_store: AuthStore = Depends(get_auth_store),
  current_user: dict = Depends(get_current_user),
):
  """
  Supabase 로그인 계정만 탈퇴: Auth(auth.users) Admin 삭제 후 로컬 SQLite 사용자 삭제.
  Bearer 토큰 필수(서비스 롤로 Auth 삭제 검증).
  """
  if not authorization or not authorization.startswith("Bearer "):
    raise HTTPException(status_code=400, detail="탈퇴는 Authorization: Bearer(Supabase 세션)로만 가능합니다.")

  supabase_uid = current_user.get("supabase_uid")
  if not supabase_uid:
    raise HTTPException(
      status_code=400,
      detail="Supabase로 연동된 계정만 탈퇴할 수 있습니다. 로컬 데모 세션은 관리자에게 문의하세요.",
    )

  delete_supabase_auth_user(settings, str(supabase_uid))
  user_id = int(current_user["id"])
  auth_store.delete_local_user_by_id(user_id)
  return {"ok": True}
