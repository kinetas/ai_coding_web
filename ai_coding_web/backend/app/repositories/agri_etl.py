"""공공데이터 농가격 API → 로컬 DB(agri_price_*) 적재."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.db_models import AgriPriceAnalytics, AgriPriceHistory, AgriPriceRaw
from crawler.at_price_trend import agri_price_history_row


def _norm_item_cd(hr: dict[str, Any]) -> str:
  raw = hr.get("item_cd")
  if raw and str(raw).strip():
    return str(raw).strip()[:32]
  ik = hr.get("item_key") or ""
  s = str(ik).strip()
  return (s[:32] if s else "?")[:32]


def upsert_agri_price_from_full_package(full: dict[str, Any], session_factory: sessionmaker) -> tuple[int, int]:
  """
  `fetch_full_agri_from_env()` / `build_agri_price_rows_from_items()` 결과를 로컬 DB에 반영.
  반환: (history_저장_건수, history_스킵_건수)
  """
  db_row = full["db_row"]
  raw_db_row = full["raw_db_row"]
  items: list[dict[str, Any]] = list(raw_db_row.get("items") or [])

  with session_factory() as db:
    row_a = db.scalar(select(AgriPriceAnalytics).where(AgriPriceAnalytics.slug == "latest"))
    if row_a:
      row_a.source = db_row.get("source") or "data_go_kr"
      row_a.meta = db_row.get("meta") or {}
      row_a.region_stats = db_row.get("region_stats") or []
      row_a.overall = db_row.get("overall") or {}
      row_a.forecast = db_row.get("forecast") or {}
      row_a.distribution = db_row.get("distribution") or {}
      row_a.chart_bundle = db_row.get("chart_bundle") or {}
    else:
      db.add(
        AgriPriceAnalytics(
          slug="latest",
          source=db_row.get("source") or "data_go_kr",
          meta=db_row.get("meta") or {},
          region_stats=db_row.get("region_stats") or [],
          overall=db_row.get("overall") or {},
          forecast=db_row.get("forecast") or {},
          distribution=db_row.get("distribution") or {},
          chart_bundle=db_row.get("chart_bundle") or {},
        )
      )

    row_r = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
    if row_r:
      row_r.source = raw_db_row.get("source") or "data_go_kr"
      row_r.meta = raw_db_row.get("meta") or {}
      row_r.api_meta = raw_db_row.get("api_meta") or {}
      row_r.items = items
    else:
      db.add(
        AgriPriceRaw(
          slug="latest",
          source=raw_db_row.get("source") or "data_go_kr",
          meta=raw_db_row.get("meta") or {},
          api_meta=raw_db_row.get("api_meta") or {},
          items=items,
        )
      )

    n_ok = 0
    n_skip = 0
    for it in items:
      hr = agri_price_history_row(it)
      if not hr:
        n_skip += 1
        continue
      item_cd = _norm_item_cd(hr)
      vrty_cd = hr.get("vrty_cd")
      grd_cd = hr.get("grd_cd")
      se_cd = hr.get("se_cd")
      exmn = hr["exmn_ymd"]
      payload = hr.get("payload") or {}

      # 가이드 4-1: item_cd + vrty_cd + grd_cd + se_cd + exmn_ymd 로 시계열 식별
      q = select(AgriPriceHistory).where(
        AgriPriceHistory.item_cd == item_cd,
        AgriPriceHistory.exmn_ymd == exmn,
      )
      if vrty_cd is None:
        q = q.where(AgriPriceHistory.vrty_cd.is_(None))
      else:
        q = q.where(AgriPriceHistory.vrty_cd == vrty_cd)
      if grd_cd is None:
        q = q.where(AgriPriceHistory.grd_cd.is_(None))
      else:
        q = q.where(AgriPriceHistory.grd_cd == grd_cd)
      if se_cd is None:
        q = q.where(AgriPriceHistory.se_cd.is_(None))
      else:
        q = q.where(AgriPriceHistory.se_cd == se_cd)

      existing = db.scalar(q)
      if existing:
        existing.payload = payload
      else:
        db.add(AgriPriceHistory(
          item_cd=item_cd,
          vrty_cd=vrty_cd,
          grd_cd=grd_cd,
          se_cd=se_cd,
          exmn_ymd=exmn,
          payload=payload,
        ))
      db.flush()
      n_ok += 1

    db.commit()
  return n_ok, n_skip
