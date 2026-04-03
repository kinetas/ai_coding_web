from __future__ import annotations

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
  id: int
  email: str
  nickname: str
  status: str = "active"
  created_at: str = ""
  updated_at: str = ""
  supabase_uid: str | None = None


class RegisterPayload(BaseModel):
  email: str = Field(min_length=5, max_length=255)
  password: str = Field(min_length=8, max_length=120)
  nickname: str = Field(min_length=2, max_length=80)


class LoginPayload(BaseModel):
  email: str = Field(min_length=5, max_length=255)
  password: str = Field(min_length=1, max_length=120)


class AuthSessionResponse(BaseModel):
  ok: bool = True
  user: UserResponse


class SupabaseSignInPayload(BaseModel):
  email: str = Field(min_length=3, max_length=255)
  password: str = Field(min_length=1, max_length=120)


class SupabaseSignUpPayload(BaseModel):
  email: str = Field(min_length=3, max_length=255)
  password: str = Field(min_length=8, max_length=120)
  nickname: str = Field(default="", max_length=80)


class SupabaseRefreshPayload(BaseModel):
  refresh_token: str = Field(min_length=10)


class SupabaseUserUpdatePayload(BaseModel):
  email: str | None = Field(default=None, max_length=255)
  nickname: str | None = Field(default=None, max_length=80)
