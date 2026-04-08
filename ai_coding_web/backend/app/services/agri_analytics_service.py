"""농산물 가격 분석 서비스 — 로컬 DB(SQLAlchemy) 기반."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.config import Settings
from backend.app.db import SessionLocal
from backend.app.db_models import AgriPriceAnalytics, AgriPriceHistory, AgriPriceRaw
from backend.app.models.agri_analytics import (
  AgriAnalyticsResponse,
  AgriCategoryItem,
  AgriCategoryStats,
  AgriCategoryStatsResponse,
  AgriItemSeriesPoint,
  AgriItemSeriesResponse,
  AgriPriceRawResponse,
  AgriRiceSeriesResponse,
  AgriWeeklyPoint,
)


def _linreg(xs: list[int], ys: list[float]) -> tuple[float, float]:
  """최소자승법 선형 회귀 → (slope, intercept)."""
  n = len(xs)
  sx = sum(xs)
  sy = sum(ys)
  sxy = sum(x * y for x, y in zip(xs, ys))
  sx2 = sum(x * x for x in xs)
  denom = n * sx2 - sx * sx
  if denom == 0:
    return 0.0, sy / n if n else 0.0
  slope = (n * sxy - sx * sy) / denom
  intercept = (sy - slope * sx) / n
  return slope, intercept


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

  # ── 카테고리별 통계 ──────────────────────────────────────────────────────

  def get_category_stats(self) -> AgriCategoryStatsResponse | None:
    """AgriPriceRaw.items 를 ctgry_nm 별로 집계해 카테고리별 통계 반환."""
    with self._session_factory() as db:
      row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
    if not row:
      return None

    updated_at = row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat()
    items: list[dict] = row.items or []

    # ctgry_nm → [(item_nm, price), ...]
    groups: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for it in items:
      ctgry = str(it.get("ctgry_nm") or it.get("category") or "other").strip() or "other"
      nm = str(it.get("item_nm") or it.get("품목명") or "").strip()
      price, _ = _survey_prices_from_payload(it)
      if price is not None and price > 0:
        groups[ctgry].append((nm, price))

    categories: list[AgriCategoryStats] = []
    for ctgry_nm, pairs in sorted(groups.items()):
      prices = [p for _, p in pairs]
      min_p = min(prices)
      max_p = max(prices)
      avg_p = round(sum(prices) / len(prices), 1)

      cheapest_pair = min(pairs, key=lambda x: x[1])
      most_exp_pair = max(pairs, key=lambda x: x[1])

      categories.append(
        AgriCategoryStats(
          ctgry_nm=ctgry_nm,
          count=len(pairs),
          min_price=min_p,
          max_price=max_p,
          avg_price=avg_p,
          cheapest=AgriCategoryItem(item_nm=cheapest_pair[0], price=cheapest_pair[1]),
          most_expensive=AgriCategoryItem(item_nm=most_exp_pair[0], price=most_exp_pair[1]),
        )
      )

    return AgriCategoryStatsResponse(
      updated_at=updated_at,
      categories=categories,
      meta={"source_table": "agri_price_raw", "item_count": len(items)},
    )

  # ── 쌀 주차별 시계열 + 선형 회귀 예측 ─────────────────────────────────────

  def get_rice_weekly_series(self) -> AgriRiceSeriesResponse | None:
    """AgriPriceHistory 에서 쌀 데이터를 주차별로 집계하고 선형 회귀로 다음 구간 예측."""
    # 1) raw 에서 쌀 item_cd 찾기
    rice_item_cd: str | None = None
    rice_item_nm = "쌀"
    with self._session_factory() as db:
      raw_row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
    if raw_row:
      for it in raw_row.items or []:
        nm = str(it.get("item_nm") or it.get("품목명") or "")
        if "쌀" in nm:
          rice_item_cd = str(it.get("item_cd") or "").strip() or None
          rice_item_nm = nm
          break

    # 2) AgriPriceHistory 조회 (item_cd 있으면 필터, 없으면 payload 에서 item_nm 매칭)
    with self._session_factory() as db:
      if rice_item_cd:
        q = select(AgriPriceHistory).where(AgriPriceHistory.item_cd == rice_item_cd)
      else:
        q = select(AgriPriceHistory)
      rows = db.scalars(q.order_by(AgriPriceHistory.exmn_ymd.asc())).all()

    # 3) item_cd 없는 경우 payload의 item_nm 으로 필터
    if not rice_item_cd:
      filtered = []
      for r in rows:
        p = r.payload or {}
        if isinstance(p, str):
          try:
            p = json.loads(p)
          except json.JSONDecodeError:
            p = {}
        nm = str(p.get("item_nm") or p.get("품목명") or "")
        if "쌀" in nm:
          filtered.append(r)
          rice_item_nm = nm or rice_item_nm
      rows = filtered

    if not rows:
      return AgriRiceSeriesResponse(
        item_nm=rice_item_nm,
        item_cd=rice_item_cd,
        weekly_series=[],
        forecast={"note": "No data"},
        meta={"row_count": 0},
      )

    # 4) 주차별 집계
    week_buckets: dict[str, list[float]] = defaultdict(list)
    for r in rows:
      p = r.payload or {}
      if isinstance(p, str):
        try:
          p = json.loads(p)
        except json.JSONDecodeError:
          p = {}
      price, _ = _survey_prices_from_payload(p)
      if price is None or price <= 0:
        continue
      ymd = r.exmn_ymd or ""
      if len(ymd) == 8:
        try:
          dt = datetime.strptime(ymd, "%Y%m%d")
          iso = dt.isocalendar()
          label = f"{iso[0]}-W{iso[1]:02d}"
          week_buckets[label].append(price)
        except ValueError:
          pass

    weekly_series: list[AgriWeeklyPoint] = []
    for label in sorted(week_buckets.keys()):
      vals = week_buckets[label]
      weekly_series.append(AgriWeeklyPoint(week_label=label, avg_price=round(sum(vals) / len(vals), 1)))

    # 5) 선형 회귀 (numpy 없이)
    forecast: dict[str, Any] = {"method": "linear_extrapolation"}
    if len(weekly_series) >= 2:
      xs = list(range(len(weekly_series)))
      ys = [p.avg_price for p in weekly_series]
      slope, intercept = _linreg(xs, ys)
      next_x = len(weekly_series)
      next_est = round(intercept + slope * next_x, 1)
      last_y = ys[-1]
      wow_pct = round((next_est - last_y) / last_y * 100, 2) if last_y else None
      forecast.update(
        {
          "next_step_estimate": next_est,
          "slope_per_week": round(slope, 2),
          "week_over_week_pct": wow_pct,
          "note": f"Linear extrapolation over {len(weekly_series)} weekly buckets",
        }
      )
    else:
      forecast["note"] = "Insufficient data (fewer than 2 periods)"

    return AgriRiceSeriesResponse(
      item_nm=rice_item_nm,
      item_cd=rice_item_cd,
      weekly_series=weekly_series,
      forecast=forecast,
      meta={"row_count": len(rows), "week_count": len(weekly_series)},
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
