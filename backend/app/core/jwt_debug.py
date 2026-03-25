"""
JWT 디버그용: 서명 검증 없이 헤더/페이로드 일부만 추출 (로그 전용).
토큰 전체·이메일 전체·비밀값은 절대 로그하지 않음.
"""

from __future__ import annotations

import base64
import json
import logging
from time import time
from typing import Any

import jwt
from jwt import PyJWTError

logger = logging.getLogger(__name__)


def _b64url_decode_segment(segment: str) -> bytes:
  pad = "=" * (-len(segment) % 4)
  return base64.urlsafe_b64decode(segment + pad)


def safe_jwt_preview_for_log(token: str) -> dict[str, Any]:
  """콘솔 디버그용 요약. 검증 없음."""
  out: dict[str, Any] = {}
  parts = (token or "").strip().split(".")
  if len(parts) != 3:
    out["parse_error"] = "not_a_jwt"
    return out

  try:
    header = jwt.get_unverified_header(token)
    out["header_alg"] = header.get("alg")
    out["header_kid"] = header.get("kid")
    out["header_typ"] = header.get("typ")
  except PyJWTError as exc:
    out["header_error"] = f"{type(exc).__name__}: {exc!s}"
    return out

  try:
    raw = _b64url_decode_segment(parts[1])
    payload = json.loads(raw.decode("utf-8"))
  except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
    out["payload_error"] = f"{type(exc).__name__}: {exc!s}"
    return out

  out["iss"] = payload.get("iss")
  out["aud"] = payload.get("aud")
  exp = payload.get("exp")
  out["exp"] = exp
  if isinstance(exp, (int, float)):
    now = int(time())
    out["exp_in_seconds"] = int(exp) - now
    out["expired"] = int(exp) < now

  sub = str(payload.get("sub") or "")
  out["sub_len"] = len(sub)
  if sub:
    out["sub_prefix"] = sub[:8] + "…" if len(sub) > 8 else sub

  meta = payload.get("user_metadata") if isinstance(payload.get("user_metadata"), dict) else {}
  app_meta = payload.get("app_metadata") if isinstance(payload.get("app_metadata"), dict) else {}
  has_root = bool(str(payload.get("email") or "").strip())
  has_um = bool(str(meta.get("email") or "").strip())
  has_am = bool(str(app_meta.get("email") or "").strip())
  out["email_claim"] = {"root": has_root, "user_metadata": has_um, "app_metadata": has_am}

  keys = sorted(payload.keys())
  out["payload_keys"] = keys[:40]
  if len(keys) > 40:
    out["payload_keys_truncated"] = True

  return out


def log_jwt_verify_failure(
  *,
  token_alg: str,
  verify_mode: str,
  exc: Exception,
  settings_app_env: str,
  expected_jwt_issuer: str | None,
  jwks_url: str | None,
) -> None:
  """검증 실패 시 WARNING 한 줄 + 개발 환경에서만 상세."""
  msg = (
    "JWT 검증 실패 | alg=%s | mode=%s | err=%s | detail=%s"
    % (token_alg, verify_mode, type(exc).__name__, exc)
  )
  logger.warning(msg)
  if (settings_app_env or "").lower() != "development":
    return
  logger.warning(
    "JWT 설정 힌트(개발) | SUPABASE_JWT_ISSUER(기대)=%s | JWKS=%s",
    expected_jwt_issuer or "(없음)",
    jwks_url or "(HS256 경로에서는 미사용)",
  )
