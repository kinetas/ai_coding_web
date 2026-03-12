from __future__ import annotations

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
  id: int
  email: str
  name: str


class RegisterPayload(BaseModel):
  email: str = Field(min_length=5, max_length=255)
  password: str = Field(min_length=8, max_length=120)
  name: str = Field(min_length=2, max_length=80)


class LoginPayload(BaseModel):
  email: str = Field(min_length=5, max_length=255)
  password: str = Field(min_length=8, max_length=120)


class AuthSessionResponse(BaseModel):
  ok: bool = True
  user: UserResponse
