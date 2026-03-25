from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from backend.app.config import Settings


def delete_supabase_auth_user(settings: Settings, supabase_uid: str) -> None:
  """Supabase Admin API로 auth.users 행 삭제(public.users 등 FK CASCADE는 DB 설정 따름)."""
  if not settings.supabase_url or not settings.supabase_service_role_key:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="SUPABASE_URL 및 SUPABASE_SERVICE_ROLE_KEY가 서버에 설정되어 있어야 합니다.",
    )
  uid = (supabase_uid or "").strip()
  if not uid:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효한 사용자 ID가 없습니다.")

  base = settings.supabase_url.rstrip("/")
  url = f"{base}/auth/v1/admin/users/{uid}"
  headers = {
    "Authorization": f"Bearer {settings.supabase_service_role_key}",
    "apikey": settings.supabase_service_role_key,
  }
  try:
    with httpx.Client(timeout=30.0) as client:
      response = client.delete(url, headers=headers)
  except httpx.HTTPError as exc:
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f"Supabase Admin 호출 실패: {exc!s}",
    ) from exc

  if response.status_code not in (200, 204):
    detail = response.text[:500] if response.text else response.reason_phrase
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f"Supabase 계정 삭제 실패 ({response.status_code}): {detail}",
    )
