from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.time import utc_now_iso

router = APIRouter()


@router.get("/health")
def health():
  return {"ok": True, "ts": utc_now_iso()}

