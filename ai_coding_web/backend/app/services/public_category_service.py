from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.app.config import Settings
from backend.app.models.public_category import PublicCategoryAnalyticsResponse, PublicCategoryRawResponse
from backend.app.models.types import PublicCategory


class PublicCategoryService:
  """Supabase `public_category_*` 테이블 조회."""

  def __init__(self, settings: Settings):
    self._url = settings.supabase_url.rstrip("/")
    self._rest = f"{self._url}/rest/v1"
    self._key = settings.supabase_service_role_key.strip() or settings.supabase_anon_key.strip()

  def _headers(self) -> dict[str, str]:
    return {
      "apikey": self._key,
      "Authorization": f"Bearer {self._key}",
      "Accept": "application/json",
    }

  def get_analytics(self, category_code: PublicCategory) -> PublicCategoryAnalyticsResponse | None:
    if not self._key or not self._url:
      return None
    with httpx.Client(timeout=45.0) as client:
      r = client.get(
        f"{self._rest}/public_category_analytics",
        headers=self._headers(),
        params={
          "category_code": f"eq.{category_code}",
          "slug": "eq.latest",
          "select": "*",
          "limit": "1",
        },
      )
      r.raise_for_status()
      rows = r.json()
    if not rows:
      return None
    row = rows[0]
    raw_ts = row.get("updated_at")
    updated_at = raw_ts if isinstance(raw_ts, str) else datetime.now(timezone.utc).isoformat()

    def _as_obj(v: Any) -> Any:
      if isinstance(v, str):
        try:
          return json.loads(v)
        except json.JSONDecodeError:
          return v
      return v

    def _as_dict(v: Any) -> dict[str, Any]:
      o = _as_obj(v)
      return dict(o) if isinstance(o, dict) else {}

    return PublicCategoryAnalyticsResponse(
      category_code=category_code,
      slug=str(row.get("slug", "latest")),
      updated_at=updated_at,
      source=str(row.get("source") or "data_go_kr"),
      meta=_as_dict(row.get("meta")),
      chart_bundle=_as_dict(row.get("chart_bundle")),
      summary=_as_dict(row.get("summary")),
      distribution=_as_dict(row.get("distribution")),
    )

  def get_raw(self, category_code: PublicCategory) -> PublicCategoryRawResponse | None:
    if not self._key or not self._url:
      return None
    with httpx.Client(timeout=60.0) as client:
      r = client.get(
        f"{self._rest}/public_category_raw",
        headers=self._headers(),
        params={
          "category_code": f"eq.{category_code}",
          "slug": "eq.latest",
          "select": "*",
          "limit": "1",
        },
      )
      r.raise_for_status()
      rows = r.json()
    if not rows:
      return None
    row = rows[0]
    raw_ts = row.get("updated_at")
    updated_at = raw_ts if isinstance(raw_ts, str) else datetime.now(timezone.utc).isoformat()

    def _as_obj(v: Any) -> Any:
      if isinstance(v, str):
        try:
          return json.loads(v)
        except json.JSONDecodeError:
          return v
      return v

    def _as_dict(v: Any) -> dict[str, Any]:
      o = _as_obj(v)
      return dict(o) if isinstance(o, dict) else {}

    raw_items = row.get("items")
    items_o = _as_obj(raw_items)
    items = [x for x in items_o if isinstance(x, dict)] if isinstance(items_o, list) else []

    return PublicCategoryRawResponse(
      category_code=category_code,
      slug=str(row.get("slug", "latest")),
      updated_at=updated_at,
      source=str(row.get("source") or "data_go_kr"),
      meta=_as_dict(row.get("meta")),
      api_meta=_as_dict(row.get("api_meta")),
      items=items,
    )
