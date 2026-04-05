"""농산물 가격 분석 서비스 — 로컬 DB(SQLAlchemy) 기반."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.config import Settings
from backend.app.db import SessionLocal
from backend.app.db_models import AgriPriceAnalytics, AgriPriceHistory, AgriPriceRaw
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
  cur = _to_float_agri(
    p.get("exmn_dd_cnvs_avg_prc")
    or p.get("exmn_dd_avg_prc")
    or p.get("조사일kg환산평균가격")
    or p.get("조사일평균가격")
  )
  raw = _to_float_agri(p.get("exmn_dd_avg_prc") or p.get("조사일평균가격"))
  return cur, raw


class AgriAnalyticsService:
  """로컬 DB(SQLite/PostgreSQL)에서 농산물 가격 분석 데이터 조회."""

  def __init__(self, settings: Settings, session_factory: sessionmaker | None = None):
    self._session_factory: sessionmaker = session_factory or SessionLocal

  def get_latest(self) -> AgriAnalyticsResponse | None:
    with self._session_factory() as db:
      row = db.scalar(select(AgriPriceAnalytics).where(AgriPriceAnalytics.slug == "latest"))
    if not row:
      return None
    updated_at = row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat()
    return AgriAnalyticsResponse(
      slug=row.slug,
      updated_at=updated_at,
      source=row.source,
      meta=row.meta or {},
      region_stats=row.region_stats or [],
      overall=row.overall or {},
      forecast=row.forecast or {},
      distribution=row.distribution or {},
      chart_bundle=row.chart_bundle or {},
    )

  def get_raw_latest(self) -> AgriPriceRawResponse | None:
    with self._session_factory() as db:
      row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
    if not row:
      return None
    updated_at = row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat()
    return AgriPriceRawResponse(
      slug=row.slug,
      updated_at=updated_at,
      source=row.source,
      meta=row.meta or {},
      api_meta=row.api_meta or {},
      items=row.items or [],
    )

  def get_item_price_series(self, item_cd: str, vrty_cd: str | None = None) -> AgriItemSeriesResponse | None:
    item_cd = (item_cd or "").strip()
    if not item_cd:
      return None

    with self._session_factory() as db:
      q = select(AgriPriceHistory).where(AgriPriceHistory.item_cd == item_cd)
      if vrty_cd and vrty_cd.strip():
        q = q.where(AgriPriceHistory.vrty_cd == vrty_cd.strip())
      q = q.order_by(AgriPriceHistory.exmn_ymd.asc())
      rows = db.scalars(q).all()

    points: list[AgriItemSeriesPoint] = []
    for r in rows:
      p = r.payload or {}
      if isinstance(p, str):
        try:
          p = json.loads(p)
        except json.JSONDecodeError:
          p = {}
      nm = str(p.get("item_nm") or p.get("품목명") or "")[:80]
      pr, raw = _survey_prices_from_payload(p)
      points.append(AgriItemSeriesPoint(exmn_ymd=r.exmn_ymd or "?", item_nm=nm, price=pr, price_raw=raw))

    return AgriItemSeriesResponse(
      item_cd=item_cd,
      vrty_cd=vrty_cd.strip() if vrty_cd and vrty_cd.strip() else None,
      points=points,
      meta={"source_table": "agri_price_history", "row_count": len(points)},
    )
