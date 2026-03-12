from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Final


PBKDF2_ITERATIONS: Final[int] = 120_000


def hash_password(password: str, salt: str | None = None) -> str:
  real_salt = salt or secrets.token_hex(16)
  digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), real_salt.encode("utf-8"), PBKDF2_ITERATIONS)
  return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${real_salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
  try:
    algorithm, iterations, salt, digest = encoded.split("$", 3)
  except ValueError:
    return False
  if algorithm != "pbkdf2_sha256":
    return False
  candidate = hash_password(password, salt=salt)
  expected = f"pbkdf2_sha256${iterations}${salt}${digest}"
  return hmac.compare_digest(candidate, expected)


def generate_session_token() -> str:
  return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
  return hashlib.sha256(token.encode("utf-8")).hexdigest()
