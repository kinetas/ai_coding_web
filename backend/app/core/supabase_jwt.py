from __future__ import annotations

from typing import Any

import jwt
from jwt import InvalidIssuerError, PyJWKClient, PyJWTError

# Supabase: 레거시는 HS256(JWT Secret), 신규 JWT 서명 키는 RS256/ES256 + JWKS
_ASYM_ALGS = frozenset({"RS256", "RS384", "RS512", "PS256", "ES256", "ES384", "ES512"})
# 서버 시계가 Supabase보다 느리면 iat가 미래로 보여 ImmatureSignatureError → leeway로 완화
_JWT_LEEWAY_SECONDS = 120


def decode_supabase_access_token(
  token: str,
  *,
  secret: str,
  issuer: str | None,
) -> dict[str, Any]:
  """
  Supabase access_token 검증.
  - HS256: SUPABASE_JWT_SECRET(대칭 키)
  - RS256 등: {issuer}/.well-known/jwks.json 공개 키
  """
  # verify_iat: Supabase iat는 UTC 기준인데 PC 시계가 느리면 ImmatureSignatureError → iat 미래 검증 생략(exp는 그대로 검증)
  options: dict[str, bool] = {"require": ["sub", "exp", "aud"], "verify_iat": False}
  try:
    header = jwt.get_unverified_header(token)
  except PyJWTError as exc:
    raise ValueError("JWT 헤더를 읽을 수 없습니다.") from exc

  alg = str(header.get("alg") or "HS256").upper()

  if alg == "HS256":
    if not (secret or "").strip():
      raise ValueError("SUPABASE_JWT_SECRET is empty")
    decode_kwargs: dict[str, Any] = {
      "algorithms": ["HS256"],
      "audience": "authenticated",
      "options": options,
    }
    if issuer:
      decode_kwargs["issuer"] = issuer
    try:
      return jwt.decode(token, secret, leeway=_JWT_LEEWAY_SECONDS, **decode_kwargs)
    except InvalidIssuerError:
      if not issuer:
        raise
      decode_kwargs.pop("issuer", None)
      return jwt.decode(token, secret, leeway=_JWT_LEEWAY_SECONDS, **decode_kwargs)

  if alg in _ASYM_ALGS:
    if not issuer:
      raise ValueError("RS256 등 비대칭 JWT는 issuer(SUPABASE_URL 기반 SUPABASE_JWT_ISSUER)가 필요합니다.")
    jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
    jwks_client = PyJWKClient(jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    decode_kwargs = {
      "algorithms": [alg],
      "audience": "authenticated",
      "options": options,
      "issuer": issuer,
    }
    try:
      return jwt.decode(token, signing_key.key, leeway=_JWT_LEEWAY_SECONDS, **decode_kwargs)
    except InvalidIssuerError:
      decode_kwargs.pop("issuer", None)
      return jwt.decode(token, signing_key.key, leeway=_JWT_LEEWAY_SECONDS, **decode_kwargs)

  raise ValueError(f"지원하지 않는 JWT 알고리즘: {alg}")
