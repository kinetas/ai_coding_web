from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException, status

from backend.app.config import Settings


def _auth_base(settings: Settings) -> str:
  if not settings.supabase_url:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="SUPABASE_URL이 설정되어 있지 않습니다.",
    )
  return f"{settings.supabase_url.rstrip('/')}/auth/v1"


def _anon_headers(settings: Settings) -> dict[str, str]:
  if not settings.supabase_anon_key:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="SUPABASE_ANON_KEY가 설정되어 있지 않습니다.",
    )
  key = settings.supabase_anon_key
  return {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
  }


def _user_headers(settings: Settings, access_token: str) -> dict[str, str]:
  if not settings.supabase_anon_key:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="SUPABASE_ANON_KEY가 설정되어 있지 않습니다.",
    )
  return {
    "apikey": settings.supabase_anon_key,
    "Authorization": f"Bearer {access_token.strip()}",
    "Content-Type": "application/json",
  }


def _raise_from_response(response: httpx.Response, default_status: int) -> None:
  try:
    body = response.json()
  except json.JSONDecodeError:
    raise HTTPException(status_code=default_status, detail=response.text[:500] or "Supabase Auth 요청 실패") from None
  msg = body.get("msg") or body.get("error_description") or body.get("message") or body.get("error")
  if isinstance(msg, dict):
    msg = str(msg)
  if not msg:
    msg = response.text[:500] or "Supabase Auth 요청 실패"
  code = response.status_code if 400 <= response.status_code < 600 else default_status
  raise HTTPException(status_code=code, detail=str(msg))


def sign_in_with_password(settings: Settings, email: str, password: str) -> dict[str, Any]:
  url = f"{_auth_base(settings)}/token?grant_type=password"
  payload = {"email": (email or "").strip(), "password": password or ""}
  with httpx.Client(timeout=30.0) as client:
    response = client.post(url, headers=_anon_headers(settings), json=payload)
  if response.status_code >= 400:
    _raise_from_response(response, status.HTTP_401_UNAUTHORIZED)
  return response.json()


def sign_up(settings: Settings, email: str, password: str, nickname: str) -> dict[str, Any]:
  url = f"{_auth_base(settings)}/signup"
  meta: dict[str, str] = {}
  nick = (nickname or "").strip()
  if nick:
    meta["full_name"] = nick
    meta["nickname"] = nick
  payload: dict[str, Any] = {"email": (email or "").strip(), "password": password or ""}
  if meta:
    payload["data"] = meta
  with httpx.Client(timeout=30.0) as client:
    response = client.post(url, headers=_anon_headers(settings), json=payload)
  if response.status_code >= 400:
    _raise_from_response(response, status.HTTP_400_BAD_REQUEST)
  return response.json()


def sign_out(settings: Settings, access_token: str) -> None:
  url = f"{_auth_base(settings)}/logout"
  with httpx.Client(timeout=30.0) as client:
    response = client.post(url, headers=_user_headers(settings, access_token))
  if response.status_code >= 400:
    _raise_from_response(response, status.HTTP_400_BAD_REQUEST)


def refresh_session(settings: Settings, refresh_token: str) -> dict[str, Any]:
  url = f"{_auth_base(settings)}/token?grant_type=refresh_token"
  payload = {"refresh_token": (refresh_token or "").strip()}
  with httpx.Client(timeout=30.0) as client:
    response = client.post(url, headers=_anon_headers(settings), json=payload)
  if response.status_code >= 400:
    _raise_from_response(response, status.HTTP_401_UNAUTHORIZED)
  return response.json()


def update_user(settings: Settings, access_token: str, email: str | None, nickname: str | None) -> dict[str, Any]:
  url = f"{_auth_base(settings)}/user"
  body: dict[str, Any] = {}
  if email is not None and str(email).strip():
    body["email"] = str(email).strip()
  if nickname is not None:
    nick = str(nickname).strip()
    if nick:
      body["data"] = {"full_name": nick, "nickname": nick}
  if not body:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="변경할 이메일 또는 닉네임을 보내 주세요.")
  with httpx.Client(timeout=30.0) as client:
    response = client.put(url, headers=_user_headers(settings, access_token), json=body)
  if response.status_code >= 400:
    _raise_from_response(response, status.HTTP_400_BAD_REQUEST)
  return response.json()
