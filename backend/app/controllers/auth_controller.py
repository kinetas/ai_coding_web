from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from backend.app.auth import clear_auth_cookie, get_auth_service, get_current_user, get_session_token, set_auth_cookie
from backend.app.config import Settings, get_settings
from backend.app.models.auth import AuthSessionResponse, LoginPayload, RegisterPayload, UserResponse
from backend.app.services.auth_service import AuthService


router = APIRouter()


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
