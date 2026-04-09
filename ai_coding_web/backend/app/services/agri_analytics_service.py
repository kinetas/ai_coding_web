"""농산물 가격 분석 서비스 — 로컬 DB(SQLAlchemy) 기반."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
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
  AgriPriceMover,
  AgriPriceMoversResponse,
  AgriPriceRawResponse,
  AgriRiceSeriesResponse,
  AgriUnitFamilyStats,
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


# ── 단위 분류 (가이드 6번 실무 규칙, 7번 unit_family) ────────────────────────

_WEIGHT_UNITS = {"kg", "g"}
_COUNT_UNITS = {"개", "마리", "포기", "구"}
_PACK_UNITS = {"장", "묶음", "손", "속", "봉"}
_VOLUME_UNITS = {"L"}


def _unit_family(unit: str) -> str:
  """가이드 7번 unit_family 분류."""
  u = str(unit or "").strip()
  if u in _WEIGHT_UNITS:
    return "weight"
  if u in _COUNT_UNITS:
    return "count"
  if u in _PACK_UNITS:
    return "pack"
  if u in _VOLUME_UNITS:
    return "volume"
  return "special"


def _price_for_family(p: dict[str, Any], family: str) -> float | None:
  """
  가이드 실무 규칙:
  - weight(kg/g): exmn_dd_cnvs_avg_prc 우선 (kg 환산 단가)
  - 그 외: exmn_dd_avg_prc (개당/포기당 등 원시가격)
  """
  if family == "weight":
    v = _to_float_agri(
      p.get("exmn_dd_cnvs_avg_prc") or p.get("조사일kg환산평균가격")
    )
    if v is None:
      v = _to_float_agri(p.get("exmn_dd_avg_prc") or p.get("조사일평균가격"))
    return v
  return _to_float_agri(p.get("exmn_dd_avg_prc") or p.get("조사일평균가격"))


def _price_label(family: str, unit: str, unit_sz: str) -> str:
  """사람이 읽기 좋은 가격 단위 레이블."""
  if family == "weight":
    return "원/kg환산"
  sz = str(unit_sz or "").strip()
  u = str(unit or "").strip()
  if sz and u:
    return f"원/{sz}{u}"
  if u:
    return f"원/{u}"
  return "원"


def _wow_pct(p: dict[str, Any], family: str) -> float | None:
  """전주 대비 % (가이드 7번 price_wow_pct / price_cnvs_wow_pct)."""
  if family == "weight":
    cur = _to_float_agri(p.get("exmn_dd_cnvs_avg_prc") or p.get("조사일kg환산평균가격"))
    prev = _to_float_agri(p.get("ww1_bfr_cnvs_avg_prc") or p.get("1주일전kg환산평균가격"))
  else:
    cur = _to_float_agri(p.get("exmn_dd_avg_prc") or p.get("조사일평균가격"))
    prev = _to_float_agri(p.get("ww1_bfr_avg_prc") or p.get("1주일전평균가격"))
  if cur is None or prev is None or prev == 0:
    return None
  return round((cur - prev) / prev * 100, 2)


def _w4_pct(p: dict[str, Any], family: str) -> float | None:
  """4주 대비 % (가이드 7번 price_4w_pct / price_cnvs_4w_pct)."""
  if family == "weight":
    cur = _to_float_agri(p.get("exmn_dd_cnvs_avg_prc") or p.get("조사일kg환산평균가격"))
    prev = _to_float_agri(p.get("ww4_bfr_cnvs_avg_prc") or p.get("4주일전kg환산평균가격"))
  else:
    cur = _to_float_agri(p.get("exmn_dd_avg_prc") or p.get("조사일평균가격"))
    prev = _to_float_agri(p.get("ww4_bfr_avg_prc") or p.get("4주일전평균가격"))
  if cur is None or prev is None or prev == 0:
    return None
  return round((cur - prev) / prev * 100, 2)


def _kst_today_ymd() -> str:
  """KST 기준 오늘 날짜(YYYYMMDD)."""
  kst = timezone(timedelta(hours=9))
  return datetime.now(kst).date().strftime("%Y%m%d")


def _item_exmn_ymd_raw(it: dict[str, Any]) -> str:
  return str(it.get("exmn_ymd") or it.get("exmnYmd") or "").strip()


def _items_latest_survey_lte_kst_today(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
  """
  KST 오늘을 넘지 않는 조사일(exmn_ymd) 중 가장 늦은 날짜의 행만 남긴다.
  이력 병합 raw에 여러 조사일이 섞여 있어도 차트 집계와 동일한 최신 스냅샷만 등락에 사용한다.
  """
  if not items:
    return [], ""

  dates: list[str] = []
  for it in items:
    ymd = _item_exmn_ymd_raw(it)
    if ymd and len(ymd) == 8 and ymd.isdigit():
      dates.append(ymd)

  if not dates:
    return list(items), ""

  today = _kst_today_ymd()
  candidates = [d for d in set(dates) if d <= today]
  if not candidates:
    candidates = list(set(dates))

  latest = max(candidates)
  filtered = [it for it in items if _item_exmn_ymd_raw(it) == latest]
  return filtered, latest


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
    """
    AgriPriceRaw.items 를 ctgry_nm × unit_family 별로 집계.

    가이드 핵심 규칙:
    - weight(kg/g): exmn_dd_cnvs_avg_prc (kg 환산 단가) → 서로 다른 포장 규격도 비교 가능
    - 그 외(개/마리/포기 등): exmn_dd_avg_prc, unit_sz 구분 필수
    - item_nm 만으로 합치지 않음: 카테고리 수준 집계는 unit_family 내에서만
    """
    with self._session_factory() as db:
      row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
    if not row:
      return None

    updated_at = row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat()
    items: list[dict] = row.items or []

    # ctgry_nm → unit_family → [(item_nm, price, unit_label), ...]
    groups: dict[str, dict[str, list[tuple[str, float, str]]]] = defaultdict(lambda: defaultdict(list))

    for it in items:
      ctgry = str(it.get("ctgry_nm") or it.get("category") or "other").strip() or "other"
      nm = str(it.get("item_nm") or it.get("품목명") or "").strip()
      unit = str(it.get("unit") or "").strip()
      unit_sz = str(it.get("unit_sz") or "").strip()
      family = _unit_family(unit)
      price = _price_for_family(it, family)
      if price is not None and price > 0:
        label = _price_label(family, unit, unit_sz)
        groups[ctgry][family].append((nm, price, label))

    _FAMILY_ORDER = ["weight", "count", "pack", "volume", "special"]

    categories: list[AgriCategoryStats] = []
    for ctgry_nm in sorted(groups.keys()):
      family_map = groups[ctgry_nm]
      total_count = sum(len(v) for v in family_map.values())

      # 단위군별 세부 통계
      unit_breakdown: list[AgriUnitFamilyStats] = []
      for fam in _FAMILY_ORDER:
        triplets = family_map.get(fam, [])
        if not triplets:
          continue
        prices = [p for _, p, _ in triplets]
        # weight 계열 레이블: "원/kg환산", 나머지는 가장 흔한 unit_label
        label_counts: dict[str, int] = defaultdict(int)
        for _, _, lbl in triplets:
          label_counts[lbl] += 1
        rep_label = max(label_counts, key=lambda k: label_counts[k])

        cheapest_t = min(triplets, key=lambda x: x[1])
        most_exp_t = max(triplets, key=lambda x: x[1])
        unit_breakdown.append(
          AgriUnitFamilyStats(
            unit_family=fam,
            price_label=rep_label,
            count=len(prices),
            avg_price=round(sum(prices) / len(prices), 1),
            min_price=round(min(prices), 1),
            max_price=round(max(prices), 1),
            cheapest=AgriCategoryItem(item_nm=cheapest_t[0], price=cheapest_t[1], unit_label=cheapest_t[2]),
            most_expensive=AgriCategoryItem(item_nm=most_exp_t[0], price=most_exp_t[1], unit_label=most_exp_t[2]),
          )
        )

      # 대표 통계: weight 계열 우선, 없으면 첫 번째 단위군
      rep_fam_stats = next(
        (s for s in unit_breakdown if s.unit_family == "weight"),
        unit_breakdown[0] if unit_breakdown else None,
      )

      categories.append(
        AgriCategoryStats(
          ctgry_nm=ctgry_nm,
          count=total_count,
          min_price=rep_fam_stats.min_price if rep_fam_stats else None,
          max_price=rep_fam_stats.max_price if rep_fam_stats else None,
          avg_price=rep_fam_stats.avg_price if rep_fam_stats else None,
          price_label=rep_fam_stats.price_label if rep_fam_stats else "원",
          cheapest=rep_fam_stats.cheapest if rep_fam_stats else None,
          most_expensive=rep_fam_stats.most_expensive if rep_fam_stats else None,
          unit_breakdown=unit_breakdown,
        )
      )

    return AgriCategoryStatsResponse(
      updated_at=updated_at,
      categories=categories,
      meta={"source_table": "agri_price_raw", "item_count": len(items)},
    )

  # ── 가격 등락 품목 (WoW / 4주) ────────────────────────────────────────────

  def get_price_movers(self, top_n: int = 10) -> AgriPriceMoversResponse | None:
    """
    KST 오늘 이하의 조사일 중 가장 최근 exmn_ymd 행만 사용해 전주 대비 등락률 상위 품목을 계산한다.
    (이력 병합 raw에 여러 조사일이 있어도 최신 스냅샷 한 시점만 반영.)
    가이드 5-1 추천 지표: 전주 대비 증감률 (price_wow_pct).
    """
    with self._session_factory() as db:
      row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
    if not row:
      return None

    updated_at = row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat()
    raw_items: list[dict] = row.items or []
    items, survey_date = _items_latest_survey_lte_kst_today(raw_items)

    movers: list[AgriPriceMover] = []
    for it in items:
      unit = str(it.get("unit") or "").strip()
      unit_sz = str(it.get("unit_sz") or "").strip()
      family = _unit_family(unit)
      wow = _wow_pct(it, family)
      if wow is None:
        continue
      w4 = _w4_pct(it, family)
      price_cur = _price_for_family(it, family)
      prev_key = "ww1_bfr_cnvs_avg_prc" if family == "weight" else "ww1_bfr_avg_prc"
      price_prev = _to_float_agri(it.get(prev_key))

      movers.append(
        AgriPriceMover(
          item_nm=str(it.get("item_nm") or "").strip(),
          vrty_nm=str(it.get("vrty_nm") or "").strip(),
          grd_nm=str(it.get("grd_nm") or "").strip(),
          se_nm=str(it.get("se_nm") or "").strip(),
          ctgry_nm=str(it.get("ctgry_nm") or "").strip(),
          unit_label=_price_label(family, unit, unit_sz),
          price_cur=price_cur,
          price_prev=price_prev,
          wow_pct=wow,
          w4_pct=w4,
        )
      )

    movers.sort(key=lambda x: (x.wow_pct or 0), reverse=True)
    top_risers = [m for m in movers if (m.wow_pct or 0) > 0][:top_n]
    top_fallers = sorted(
      [m for m in movers if (m.wow_pct or 0) < 0],
      key=lambda x: (x.wow_pct or 0),
    )[:top_n]

    return AgriPriceMoversResponse(
      updated_at=updated_at,
      survey_date=survey_date,
      top_risers=top_risers,
      top_fallers=top_fallers,
      meta={
        "source_table": "agri_price_raw",
        "item_count": len(raw_items),
        "movers_item_count": len(items),
        "movers_computed": len(movers),
        "movers_latest_exmn_ymd": survey_date,
        "movers_today_kst_ymd": _kst_today_ymd(),
        "movers_scope": "latest_exmn_ymd_lte_kst_today",
      },
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
