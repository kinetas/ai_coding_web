"""
의료·교통·관광·환경: .env 로 지정한 공공 API → 원본·범용 분석 → analysis 스냅샷용 차트.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from crawler.generic_item_analytics import build_generic_public_charts, build_summary_and_distribution
from crawler.public_data_portal import fetch_portal_json_pages, load_query_dict_from_env

# ETL/백엔드와 동일 코드명 (health, traffic, tour, env)
PUBLIC_API_CATEGORIES = frozenset({"health", "traffic", "tour", "env"})

_ENV_PREFIX: dict[str, str] = {
  "health": "PD_HEALTH",
  "traffic": "PD_TRAFFIC",
  "tour": "PD_TOUR",
  "env": "PD_ENV",
}


def _service_key() -> str:
  return (os.getenv("DATA_GO_KR_SERVICE_KEY") or os.getenv("PUBLIC_DATA_SERVICE_KEY") or "").strip()


def category_public_api_config(category: str) -> tuple[str, dict[str, Any]] | None:
  if category not in PUBLIC_API_CATEGORIES:
    return None
  prefix = _ENV_PREFIX[category]
  path = (os.getenv(f"{prefix}_API_PATH") or "").strip()
  if not path:
    return None
  q = load_query_dict_from_env(os.getenv(f"{prefix}_API_QUERY_JSON"))
  max_rows = int((os.getenv(f"{prefix}_NUM_OF_ROWS") or "500").strip() or "500")
  return path, {"extra": q, "max_rows": max_rows}


def fetch_category_public_items(category: str) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
  cfg = category_public_api_config(category)
  key = _service_key()
  if not cfg or not key:
    return None
  path, opts = cfg
  try:
    items, meta = fetch_portal_json_pages(
      service_key=key,
      api_path=path,
      extra_params=opts["extra"],
      max_rows=min(1000, max(10, opts["max_rows"])),
    )
  except Exception:
    return None
  meta = {**meta, "category_code": category}
  return items, meta


def build_public_category_bundle(category: str) -> dict[str, Any] | None:
  """
  공공 API 성공 시: raw 행, analytics 행, analysis_snapshots용 body(line,bar,donut,accents).
  실패 시 None.
  """
  got = fetch_category_public_items(category)
  if not got:
    return None
  items, api_meta = got
  if not items:
    return None

  charts = build_generic_public_charts(items, category=category)
  summary, distribution = build_summary_and_distribution(items)
  now = datetime.now(timezone.utc).isoformat()

  cfg_path = category_public_api_config(category)
  path_hint = (cfg_path[0][:200] if cfg_path else "") or ""
  raw_row = {
    "category_code": category,
    "slug": "latest",
    "items": items,
    "api_meta": api_meta,
    "source": "data_go_kr",
    "meta": {
      "ingested_at": now,
      "item_count": len(items),
      "api_path_hint": path_hint,
    },
  }

  analytics_row = {
    "category_code": category,
    "slug": "latest",
    "chart_bundle": charts,
    "summary": summary,
    "distribution": distribution,
    "source": "data_go_kr",
    "meta": {
      "generated_at": now,
      "item_count": len(items),
      "derived_from": "public_api",
    },
  }

  body = {
    "line": charts["line"],
    "bar": charts["bar"],
    "donut": charts["donut"],
    "accents": charts.get("accents") or {"line": "#6AE4FF", "bar": "#B79BFF"},
  }

  return {"raw_row": raw_row, "analytics_row": analytics_row, "analysis_body": body, "items": items}


def merge_public_api_into_analysis(
  category: str,
  rss_body: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
  """공공 API 우선 덮어쓰기. (raw, analytics) 행 또는 None."""
  bundle = build_public_category_bundle(category)
  if not bundle or not bundle.get("items"):
    return rss_body, None, None
  return bundle["analysis_body"], bundle["raw_row"], bundle["analytics_row"]
