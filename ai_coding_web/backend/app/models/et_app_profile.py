from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EtAppProfileRow(BaseModel):
  """Supabase `public.et_app_profiles` (MCP 마이그레이션). 클라이언트는 anon 키 + RLS로 접근."""

  id: UUID = Field(description="auth.users.id 와 동일")
  nickname: str | None = None
  created_at: datetime
  updated_at: datetime
