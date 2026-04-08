from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EtAppProfileRow(BaseModel):
  """사용자 앱 프로필 행 모델."""

  id: UUID = Field(description="auth.users.id 와 동일")
  nickname: str | None = None
  created_at: datetime
  updated_at: datetime
