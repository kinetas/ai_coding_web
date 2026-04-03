from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.app.config import Settings
from backend.app.models.agri_analytics import (
  AgriAnalyticsResponse,
  AgriItemSeriesPoint,
  AgriItemSeriesResponse,
  AgriPriceRawResponse,
)


def _to_float_agri(v: Any) -> float | None:
  if v is None or v == "":
    return None
  s = str(v).strip().replace(",", "")
  if not s or s.lower() in {"null", "none"}:
    return None
  try:
    return float(s)
  except ValueError:
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
      return None
    try:
      return float(m.group(0))
    except ValueError:
      return None


def _survey_prices_from_payload(p: dict[str, Any]) -> tuple[float | None, float | None]:
  """kg환산 우선, 없으면 평균가( at_price_trend._current_price 와 동일 키 )."""
  cur = _to_float_agri(
    p.get("exmn_dd_cnvs_avg_prc")
    or p.get("exmn_dd_avg_prc")
    or p.get("조사일kg환산평균가격")
    or p.get("조사일평균가격")
  )
  raw = _to_float_agri(p.get("exmn_dd_avg_prc") or p.get("조사일평균가격"))
  return cur, raw


class AgriAnalyticsService:
  """Supabase `agri_price_analytics` 조회(프론트용 농산물 가격 분석 패키지)."""

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

  def get_latest(self) -> AgriAnalyticsResponse | None:
    if not self._key or not self._url:
      return None
    with httpx.Client(timeout=45.0) as client:
      r = client.get(
        f"{self._rest}/agri_price_analytics",
        headers=self._headers(),
        params={"slug": "eq.latest", "select": "*", "limit": "1"},
      )
      r.raise_for_status()
      rows = r.json()
    if not rows:
      return None
    row = rows[0]
    raw_ts = row.get("updated_at")
    if isinstance(raw_ts, str):
      updated_at = raw_ts
    elif raw_ts is None:
      updated_at = datetime.now(timezone.utc).isoformat()
    else:
      updated_at = str(raw_ts)

    def _as_obj(v: Any) -> Any:
      if isinstance(v, str):
        try:
          return json.loads(v)
        except json.JSONDecodeError:
          return v
      return v

    rs = _as_obj(row.get("region_stats"))
    if isinstance(rs, list):
      region_stats = rs
    elif isinstance(rs, dict):
      region_stats = [rs]
    else:
      region_stats = []

    def _as_dict(v: Any) -> dict[str, Any]:
      o = _as_obj(v)
      return dict(o) if isinstance(o, dict) else {}

    return AgriAnalyticsResponse(
      slug=str(row.get("slug", "latest")),
      updated_at=updated_at,
      source=str(row.get("source") or "data_go_kr"),
      meta=_as_dict(row.get("meta")),
      region_stats=region_stats,
      overall=_as_dict(row.get("overall")),
      forecast=_as_dict(row.get("forecast")),
      distribution=_as_dict(row.get("distribution")),
      chart_bundle=_as_dict(row.get("chart_bundle")),
    )

  def get_raw_latest(self) -> AgriPriceRawResponse | None:
    if not self._key or not self._url:
      return None
    with httpx.Client(timeout=60.0) as client:
      r = client.get(
        f"{self._rest}/agri_price_raw",
        headers=self._headers(),
        params={"slug": "eq.latest", "select": "*", "limit": "1"},
      )
      r.raise_for_status()
      rows = r.json()
    if not rows:
      return None
    row = rows[0]
    raw_ts = row.get("updated_at")
    if isinstance(raw_ts, str):
      updated_at = raw_ts
    elif raw_ts is None:
      updated_at = datetime.now(timezone.utc).isoformat()
    else:
      updated_at = str(raw_ts)

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
    if isinstance(items_o, list):
      items = [x for x in items_o if isinstance(x, dict)]
    else:
      items = []

    return AgriPriceRawResponse(
      slug=str(row.get("slug", "latest")),
      updated_at=updated_at,
      source=str(row.get("source") or "data_go_kr"),
      meta=_as_dict(row.get("meta")),
      api_meta=_as_dict(row.get("api_meta")),
      items=items,
    )

  def get_item_price_series(self, item_cd: str, vrty_cd: str | None = None) -> AgriItemSeriesResponse | None:
    """Supabase agri_price_history 에서 품목코드(·품종)별 조사일 시계열 — API 재호출 없음."""
    if not self._key or not self._url:
      return None
    item_cd = (item_cd or "").strip()
    if not item_cd:
      return None

    params: dict[str, str] = {
      "item_cd": f"eq.{item_cd}",
      "select": "exmn_ymd,payload,vrty_cd",
      "order": "exmn_ymd.asc",
      "limit": "3000",
    }
    if vrty_cd and vrty_cd.strip():
      params["vrty_cd"] = f"eq.{vrty_cd.strip()}"

    with httpx.Client(timeout=60.0) as client:
      r = client.get(f"{self._rest}/agri_price_history", headers=self._headers(), params=params)
      if r.status_code in (404, 406):
        return AgriItemSeriesResponse(
          item_cd=item_cd,
          vrty_cd=vrty_cd.strip() if vrty_cd and vrty_cd.strip() else None,
          points=[],
          meta={
            "source_table": "agri_price_history",
            "note": "테이블 미생성 또는 스키마 미적용 시 scripts/supabase_agri_price_history.sql 실행",
          },
        )
      if r.status_code != 200:
        return None
      rows = r.json()

    points: list[AgriItemSeriesPoint] = []
    for row in rows:
      if not isinstance(row, dict):
        continue
      ymd = str(row.get("exmn_ymd") or "").strip()
      p = row.get("payload")
      if isinstance(p, str):
        try:
          p = json.loads(p)
        except json.JSONDecodeError:
          p = {}
      if not isinstance(p, dict):
        p = {}
      nm = str(p.get("item_nm") or p.get("품목명") or "")[:80]
      pr, raw = _survey_prices_from_payload(p)
      points.append(
        AgriItemSeriesPoint(exmn_ymd=ymd or "?", item_nm=nm, price=pr, price_raw=raw)
      )

    return AgriItemSeriesResponse(
      item_cd=item_cd,
      vrty_cd=vrty_cd.strip() if vrty_cd and vrty_cd.strip() else None,
      points=points,
      meta={"source_table": "agri_price_history", "row_count": len(points)},
    )
