"""
1) 크롤링(Google News RSS) → 워드클라우드·분석 지표 생성
2) Supabase PostgREST로 적재 (service_role 권장)

워드클라우드는 `crawler/news_pipeline` 에서 기사 전체 텍스트로 토큰 빈도를 집계한 뒤,
`WORDCLOUD_MIN_TERM_COUNT`(기본 10) 이상만 후보로 두고 `WORDCLOUD_TOP_N`(기본 15) 상위만 적재합니다.
수집량은 `NEWS_RSS_MAX_ITEMS`(기본 80, 최대 250) 로 조절합니다.

사전: `.env`에 SUPABASE_URL·SUPABASE_SERVICE_ROLE_KEY.
정규화된 wordcloud_terms(category_code, wc_region_code, term_text) 프로젝트는 SUPABASE_WORDCLOUD_SCHEMA=normalized 추가.
단순 스크립트 스키마(scripts/supabase_etl_schema.sql)만 쓰면 해당 변수는 비움.

  python etl_supabase.py --mode crawl --all
  python etl_supabase.py --mode crawl --category agri --region kr
  python etl_supabase.py --agri-public-only
  python etl_supabase.py --agri-ingest-raw
  python etl_supabase.py --agri-analyze-from-stored
  python etl_supabase.py --mode sample
  python etl_supabase.py --mode sample --dry-run

  스키마 정합: scripts/supabase_align_etl.sql (Supabase SQL Editor)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import httpx


def _project_root() -> Path:
  return Path(__file__).resolve().parent


def _load_dotenv() -> None:
  try:
    from dotenv import load_dotenv
  except ImportError:
    return
  env = _project_root() / ".env"
  if env.is_file():
    load_dotenv(env, override=True)


def _rest_headers(service_key: str, *, minimal: bool = True) -> dict[str, str]:
  h = {
    "apikey": service_key,
    "Authorization": f"Bearer {service_key}",
    "Content-Type": "application/json",
  }
  if minimal:
    h["Prefer"] = "return=minimal"
  return h


def _wordcloud_normalized() -> bool:
  """SUPABASE_WORDCLOUD_SCHEMA=normalized: FK형 wordcloud_terms·etl_runs(코드 컬럼)."""
  v = (os.getenv("SUPABASE_WORDCLOUD_SCHEMA", "") or "").strip().lower()
  return v in ("1", "true", "yes", "normalized")


def _etl_source_code(label: str) -> str:
  l = (label or "").lower()
  if "crawl" in l or "rss" in l or "news" in l:
    return "news"
  return "internal_etl"


def _build_sample_wordcloud() -> list[dict]:
  base_words = [
    {"text": "사과", "weight": 86},
    {"text": "배추", "weight": 72},
    {"text": "양파", "weight": 66},
    {"text": "쌀값", "weight": 64},
    {"text": "도매가격", "weight": 58},
    {"text": "기상", "weight": 52},
    {"text": "산지", "weight": 50},
    {"text": "수급", "weight": 46},
    {"text": "물가", "weight": 44},
  ]
  words = []
  for w in base_words:
    jitter = random.randint(-6, 9)
    words.append({"text": w["text"], "weight": max(0, w["weight"] + jitter)})
  return words


def _build_sample_analysis() -> tuple[list[float], list[float], list[float], dict[str, str]]:
  line = [random.randint(18, 80) for _ in range(12)]
  bar = [random.randint(6, 28) for _ in range(5)]
  donut = [random.randint(10, 50) for _ in range(4)]
  accents = {"line": "#6AE4FF", "bar": "#B79BFF"}
  return line, bar, donut, accents


def _upload_wordcloud(
  client: httpx.Client,
  rest: str,
  headers: dict[str, str],
  *,
  category: str,
  region: str,
  words: list[dict],
) -> None:
  del_url = f"{rest}/wordcloud_terms"
  if _wordcloud_normalized():
    dr = client.delete(
      del_url,
      headers=headers,
      params={"category_code": f"eq.{category}", "wc_region_code": f"eq.{region}"},
    )
    rows = [
      {"category_code": category, "wc_region_code": region, "term_text": w["text"], "weight": float(w["weight"])}
      for w in words
    ]
  else:
    dr = client.delete(del_url, headers=headers, params={"category": f"eq.{category}", "region": f"eq.{region}"})
    rows = [{"category": category, "region": region, "text": w["text"], "weight": float(w["weight"])} for w in words]

  if dr.status_code not in (200, 204):
    raise SystemExit(f"wordcloud delete 실패 {dr.status_code}: {dr.text[:500]}")

  ir = client.post(f"{rest}/wordcloud_terms", headers=headers, content=json.dumps(rows, ensure_ascii=False).encode())
  if ir.status_code not in (200, 201):
    raise SystemExit(f"wordcloud insert 실패 {ir.status_code}: {ir.text[:500]}")


# Supabase `agri_price_analytics` 컬럼과 1:1 (알 수 없는 키는 제거해 PostgREST 오류 방지)
_AGRI_ANALYTICS_KEYS = frozenset(
  {"slug", "region_stats", "overall", "forecast", "distribution", "chart_bundle", "source", "meta"}
)


def _upsert_agri_analytics(client: httpx.Client, rest: str, base_headers: dict[str, str], row: dict) -> None:
  clean = {k: v for k, v in row.items() if k in _AGRI_ANALYTICS_KEYS}
  upsert_headers = {**base_headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
  r = client.post(
    f"{rest}/agri_price_analytics?on_conflict=slug",
    headers=upsert_headers,
    content=json.dumps([clean], ensure_ascii=False).encode(),
  )
  if r.status_code not in (200, 201):
    raise SystemExit(f"agri_price_analytics upsert 실패 {r.status_code}: {r.text[:500]}")


_AGRI_RAW_KEYS = frozenset({"slug", "items", "api_meta", "source", "meta"})

_AGRI_HISTORY_KEYS = frozenset({"exmn_ymd", "item_key", "item_cd", "vrty_cd", "grd_cd", "se_cd", "payload"})


def _upsert_agri_price_history_batch(
  client: httpx.Client, rest: str, base_headers: dict[str, str], items: list[dict[str, Any]]
) -> int:
  """조사일·품목키 단위로 payload upsert. 테이블 없으면 예외(호출부에서 처리)."""
  from crawler.at_price_trend import agri_price_history_row

  rows: list[dict[str, Any]] = []
  for it in items:
    r = agri_price_history_row(it)
    if r:
      rows.append({k: v for k, v in r.items() if k in _AGRI_HISTORY_KEYS})
  if not rows:
    return 0
  upsert_headers = {**base_headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
  chunk = 400
  total = 0
  for i in range(0, len(rows), chunk):
    part = rows[i : i + chunk]
    resp = client.post(
      f"{rest}/agri_price_history?on_conflict=exmn_ymd,item_key",
      headers=upsert_headers,
      content=json.dumps(part, ensure_ascii=False, default=str).encode(),
    )
    if resp.status_code not in (200, 201):
      raise SystemExit(f"agri_price_history upsert 실패 {resp.status_code}: {resp.text[:500]}")
    total += len(part)
  return total


def _fetch_latest_exmn_ymd_from_history(
  client: httpx.Client, rest: str, base_headers: dict[str, str]
) -> str | None:
  h = {k: v for k, v in base_headers.items() if k.lower() != "prefer"}
  r = client.get(
    f"{rest}/agri_price_history",
    headers=h,
    params={"select": "exmn_ymd", "order": "exmn_ymd.desc", "limit": "1"},
  )
  if r.status_code != 200:
    return None
  rows = r.json()
  if not rows:
    return None
  y = str(rows[0].get("exmn_ymd") or "").strip()
  return y or None


def _fetch_items_payloads_for_exmn_ymd(
  client: httpx.Client, rest: str, base_headers: dict[str, str], ymd: str
) -> list[dict[str, Any]]:
  h = {k: v for k, v in base_headers.items() if k.lower() != "prefer"}
  out: list[dict[str, Any]] = []
  offset = 0
  page = 1000
  while True:
    r = client.get(
      f"{rest}/agri_price_history",
      headers=h,
      params={
        "exmn_ymd": f"eq.{ymd}",
        "select": "payload",
        "limit": str(page),
        "offset": str(offset),
      },
    )
    if r.status_code != 200:
      break
    rows = r.json()
    if not rows:
      break
    for row in rows:
      p = row.get("payload")
      if isinstance(p, dict):
        out.append(p)
      elif isinstance(p, str):
        try:
          o = json.loads(p)
          if isinstance(o, dict):
            out.append(o)
        except json.JSONDecodeError:
          pass
    if len(rows) < page:
      break
    offset += page
  return out


def _items_for_latest_agri_analytics(
  client: httpx.Client,
  rest: str,
  base_headers: dict[str, str],
  stored_raw: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  """
  집계용 item[]: agri_price_history(최신 조사일) 우선, 비어 있으면 agri_price_raw.items.
  """
  ymd = _fetch_latest_exmn_ymd_from_history(client, rest, base_headers)
  if ymd:
    items = _fetch_items_payloads_for_exmn_ymd(client, rest, base_headers, ymd)
    if items:
      return items, {"analytics_items_source": "agri_price_history", "exmn_ymd": ymd}
  items = _items_from_agri_raw_row(stored_raw)
  return items, {"analytics_items_source": "agri_price_raw", "exmn_ymd": None}


def _upsert_agri_price_raw(client: httpx.Client, rest: str, base_headers: dict[str, str], row: dict) -> None:
  clean = {k: v for k, v in row.items() if k in _AGRI_RAW_KEYS}
  upsert_headers = {**base_headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
  r = client.post(
    f"{rest}/agri_price_raw?on_conflict=slug",
    headers=upsert_headers,
    content=json.dumps([clean], ensure_ascii=False).encode(),
  )
  if r.status_code not in (200, 201):
    raise SystemExit(f"agri_price_raw upsert 실패 {r.status_code}: {r.text[:500]}")


_PUBLIC_CAT_RAW_KEYS = frozenset({"category_code", "slug", "items", "api_meta", "source", "meta"})


def _upsert_public_category_raw(client: httpx.Client, rest: str, base_headers: dict[str, str], row: dict) -> None:
  clean = {k: v for k, v in row.items() if k in _PUBLIC_CAT_RAW_KEYS}
  upsert_headers = {**base_headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
  r = client.post(
    f"{rest}/public_category_raw?on_conflict=category_code,slug",
    headers=upsert_headers,
    content=json.dumps([clean], ensure_ascii=False).encode(),
  )
  if r.status_code not in (200, 201):
    raise SystemExit(f"public_category_raw upsert 실패 {r.status_code}: {r.text[:500]}")


_PUBLIC_CAT_ANALYTICS_KEYS = frozenset(
  {"category_code", "slug", "chart_bundle", "summary", "distribution", "source", "meta"}
)


def _upsert_public_category_analytics(client: httpx.Client, rest: str, base_headers: dict[str, str], row: dict) -> None:
  clean = {k: v for k, v in row.items() if k in _PUBLIC_CAT_ANALYTICS_KEYS}
  upsert_headers = {**base_headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
  r = client.post(
    f"{rest}/public_category_analytics?on_conflict=category_code,slug",
    headers=upsert_headers,
    content=json.dumps([clean], ensure_ascii=False).encode(),
  )
  if r.status_code not in (200, 201):
    raise SystemExit(f"public_category_analytics upsert 실패 {r.status_code}: {r.text[:500]}")


def _coerce_json_mapping(v: Any) -> dict[str, Any]:
  if v is None:
    return {}
  if isinstance(v, dict):
    return dict(v)
  if isinstance(v, str):
    try:
      o = json.loads(v)
      return dict(o) if isinstance(o, dict) else {}
    except json.JSONDecodeError:
      return {}
  return {}


def _items_from_agri_raw_row(row: dict[str, Any]) -> list[dict[str, Any]]:
  raw = row.get("items")
  if isinstance(raw, str):
    try:
      raw = json.loads(raw)
    except json.JSONDecodeError:
      return []
  if isinstance(raw, list):
    return [x for x in raw if isinstance(x, dict)]
  return []


def _fetch_agri_price_raw_latest(
  client: httpx.Client, rest: str, base_headers: dict[str, str]
) -> dict[str, Any] | None:
  r = client.get(
    f"{rest}/agri_price_raw",
    headers=base_headers,
    params={"slug": "eq.latest", "select": "*", "limit": "1"},
  )
  if r.status_code != 200:
    return None
  rows = r.json()
  return rows[0] if rows else None


def _agri_package_from_stored_raw_row(row: dict[str, Any]) -> dict[str, Any]:
  from crawler.at_price_trend import build_agri_supabase_rows_from_items

  items = _items_from_agri_raw_row(row)
  api_meta = _coerce_json_mapping(row.get("api_meta"))
  source = str(row.get("source") or "data_go_kr")
  raw_ts = row.get("updated_at")
  meta_extra: dict[str, Any] = {"derived_from": "agri_price_raw"}
  if isinstance(raw_ts, str):
    meta_extra["raw_row_updated_at"] = raw_ts
  elif raw_ts is not None:
    meta_extra["raw_row_updated_at"] = str(raw_ts)
  return build_agri_supabase_rows_from_items(
    items,
    api_meta=api_meta,
    source=source,
    meta_extra=meta_extra,
  )


def _agri_package_from_supabase_stored(
  client: httpx.Client,
  rest: str,
  base_headers: dict[str, str],
  stored: dict[str, Any],
) -> dict[str, Any]:
  """집계는 Supabase `agri_price_history`(최신 조사일) 우선, 없으면 raw.items."""
  from crawler.at_price_trend import build_agri_supabase_rows_from_items

  items, src_info = _items_for_latest_agri_analytics(client, rest, base_headers, stored)
  if not items:
    items = _items_from_agri_raw_row(stored)
  api_meta = _coerce_json_mapping(stored.get("api_meta"))
  api_meta.update(src_info)
  source = str(stored.get("source") or "data_go_kr")
  raw_ts = stored.get("updated_at")
  meta_extra: dict[str, Any] = {"derived_from": "agri_price_history_or_raw"}
  if isinstance(raw_ts, str):
    meta_extra["raw_row_updated_at"] = raw_ts
  elif raw_ts is not None:
    meta_extra["raw_row_updated_at"] = str(raw_ts)
  return build_agri_supabase_rows_from_items(
    items,
    api_meta=api_meta,
    source=source,
    meta_extra=meta_extra,
  )


def _upload_analysis(
  client: httpx.Client,
  rest: str,
  base_headers: dict[str, str],
  *,
  page: str,
  line: list[float],
  bar: list[float],
  donut: list[float],
  accents: dict[str, str],
) -> None:
  analysis_body = {"page": page, "line": line, "bar": bar, "donut": donut, "accents": accents}
  upsert_headers = {**base_headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
  ar = client.post(
    f"{rest}/analysis_snapshots?on_conflict=page",
    headers=upsert_headers,
    content=json.dumps([analysis_body], ensure_ascii=False).encode(),
  )
  if ar.status_code not in (200, 201):
    raise SystemExit(f"analysis upsert 실패 {ar.status_code}: {ar.text[:500]}")


def _upload_etl_runs(client: httpx.Client, rest: str, headers: dict[str, str], details: list[tuple[str, str]]) -> None:
  if _wordcloud_normalized():
    payload = [
      {"source_code": _etl_source_code(src), "status_code": "success", "details": det or ""} for src, det in details
    ]
  else:
    payload = [{"source": src, "status": "success", "details": det} for src, det in details]
  er = client.post(f"{rest}/etl_runs", headers=headers, content=json.dumps(payload, ensure_ascii=False).encode())
  if er.status_code not in (200, 201):
    raise SystemExit(f"etl_runs insert 실패 {er.status_code}: {er.text[:500]}")


def run_etl(
  supabase_url: str,
  service_key: str,
  *,
  category: str,
  region: str,
  analysis_page: str,
  dry_run: bool,
) -> None:
  base = supabase_url.rstrip("/")
  rest = f"{base}/rest/v1"
  headers = _rest_headers(service_key)

  words = _build_sample_wordcloud()
  line, bar, donut, accents = _build_sample_analysis()

  if dry_run:
    print(json.dumps({"wordcloud": {"category": category, "region": region, "words": words}}, ensure_ascii=False, indent=2))
    print(json.dumps({"analysis": {"page": analysis_page, "line": line, "bar": bar, "donut": donut, "accents": accents}}, ensure_ascii=False, indent=2))
    return

  with httpx.Client(timeout=120.0) as client:
    _upload_wordcloud(client, rest, headers, category=category, region=region, words=words)
    _upload_analysis(client, rest, headers, page=analysis_page, line=line, bar=bar, donut=donut, accents=accents)
    _upload_etl_runs(
      client,
      rest,
      headers,
      [
        ("wordcloud_ingest_supabase", f"category={category},region={region},count={len(words)}"),
        ("analysis_ingest_supabase", f"page={analysis_page}"),
      ],
    )

  print("OK: Supabase 적재 완료 (sample: wordcloud_terms, analysis_snapshots, etl_runs)")


def run_crawl_etl(
  supabase_url: str,
  service_key: str,
  *,
  category: str | None,
  region: str | None,
  load_all: bool,
  dry_run: bool,
) -> None:
  from crawler.news_pipeline import (
    CATEGORY_TO_ANALYSIS_PAGE,
    build_analysis_payload,
    build_word_weights,
    category_keyword_label,
    collect_for_category,
  )

  base = supabase_url.rstrip("/")
  rest = f"{base}/rest/v1"
  headers = _rest_headers(service_key)

  categories_all = ["agri", "health", "traffic", "tour", "env"]
  regions_all = ["kr", "global"]

  if load_all:
    cat_list = categories_all
    reg_list = regions_all
  else:
    if not category or not region:
      raise SystemExit("--mode crawl 에서 --all 이 아니면 --category 와 --region 이 필요합니다.")
    cat_list = [category]
    reg_list = [region]

  job_count = 0
  analysis_count = 0

  def run_one_category(client: httpx.Client | None, c: str) -> None:
    nonlocal job_count, analysis_count
    label_kr = category_keyword_label(c, "kr")
    label_gl = category_keyword_label(c, "global")
    print(f"[crawl+etl] category={c} search_kr={label_kr!r} search_global={label_gl!r}", flush=True)

    entries_for_analysis = None
    for r in reg_list:
      entries = collect_for_category(c, r)
      if r == "kr":
        entries_for_analysis = entries
      words = build_word_weights(entries, category=c)
      if not words and not entries:
        words = _build_sample_wordcloud()[:12]
      if dry_run:
        print(f"  (dry-run) wordcloud {c}/{r} terms={len(words)}", flush=True)
      else:
        assert client is not None
        _upload_wordcloud(client, rest, headers, category=c, region=r, words=words)
        print(f"  OK wordcloud → Supabase category={c} region={r} terms={len(words)}", flush=True)
      job_count += 1

    if c in CATEGORY_TO_ANALYSIS_PAGE:
      if entries_for_analysis is None:
        entries_for_analysis = collect_for_category(c, "kr")
      body = build_analysis_payload(c, "kr", entries_for_analysis)
      page = CATEGORY_TO_ANALYSIS_PAGE[c]
      if dry_run:
        print(f"  (dry-run) analysis page={page} (from KR {c!r} articles)", flush=True)
      else:
        assert client is not None
        from crawler.category_public_bundle import PUBLIC_API_CATEGORIES, merge_public_api_into_analysis

        if c in PUBLIC_API_CATEGORIES:
          try:
            merged, raw_pub, an_pub = merge_public_api_into_analysis(c, body)
            body = merged
            if raw_pub:
              _upsert_public_category_raw(client, rest, headers, raw_pub)
            if an_pub:
              _upsert_public_category_analytics(client, rest, headers, an_pub)
            if raw_pub:
              print(f"  OK public_data raw+analytics → category={c}", flush=True)
          except Exception as ex:
            print(f"  [public API {c}] 뉴스 분석 유지: {ex}", flush=True)
        _upload_analysis(
          client,
          rest,
          headers,
          page=page,
          line=body["line"],
          bar=body["bar"],
          donut=body["donut"],
          accents=body["accents"],
        )
        print(f"  OK analysis → Supabase page={page}", flush=True)
      analysis_count += 1

  if dry_run:
    for c in cat_list:
      run_one_category(None, c)
    print(
      json.dumps(
        {"summary": {"wordcloud_jobs": job_count, "analysis_pages": analysis_count, "dry_run": True}},
        ensure_ascii=False,
        indent=2,
      )
    )
    return

  with httpx.Client(timeout=120.0) as client:
    for i, c in enumerate(cat_list):
      run_one_category(client, c)
      if load_all and i + 1 < len(cat_list):
        time.sleep(0.6)

    # 농산물(analysis-1): 공공데이터 가격 추이 API가 설정돼 있으면 차트를 실데이터로 덮어씀
    merge_agri_prices = not dry_run and (load_all or category == "agri")
    if merge_agri_prices:
      try:
        from crawler.at_price_trend import ingest_raw_row_from_env

        raw_db_row = ingest_raw_row_from_env()
        if raw_db_row:
          _upsert_agri_price_raw(client, rest, headers, raw_db_row)
          items_in = raw_db_row.get("items") or []
          try:
            n_h = _upsert_agri_price_history_batch(client, rest, headers, items_in)
            print(f"  OK agri_price_history upsert {n_h} rows", flush=True)
          except Exception as e:
            print(
              f"  [agri_price_history] {e} (테이블 미생성 시 scripts/supabase_agri_price_history.sql 실행)",
              flush=True,
            )
          stored = _fetch_agri_price_raw_latest(client, rest, headers)
          if stored:
            full = _agri_package_from_supabase_stored(client, rest, headers, stored)
            c = full["charts"]
            _upload_analysis(
              client,
              rest,
              headers,
              page="analysis-1",
              line=c["line"],
              bar=c["bar"],
              donut=c["donut"],
              accents=c["accents"],
            )
            _upsert_agri_analytics(client, rest, headers, full["db_row"])
            print(
              "OK analysis-1 + agri_price_raw + agri_price_history + agri_price_analytics ← 공공데이터·DB 집계",
              flush=True,
            )
          else:
            print(
              "[공공데이터 가격] 원본은 저장됐으나 agri_price_raw 재조회 실패 → analysis-1·analytics 미갱신",
              flush=True,
            )
        else:
          print("[공공데이터 가격] DATA_GO_KR_SERVICE_KEY / AT_PRICE_API_PATH 없음 → analysis-1 은 뉴스 기준 유지", flush=True)
      except Exception as e:
        print(f"[공공데이터 가격] analysis-1 유지(뉴스·API 실패): {e}", flush=True)

    _upload_etl_runs(
      client,
      rest,
      headers,
      [
        (
          "crawl_wordcloud_supabase",
          f"sequential_categories={','.join(cat_list)},wordcloud_jobs={job_count}",
        ),
        ("crawl_analysis_supabase", f"analysis_pages={analysis_count},agri_price_api={'1' if merge_agri_prices else '0'}"),
      ],
    )

  print("OK: 카테고리 순서대로 크롤·ETL 완료 (wordcloud_terms, analysis_snapshots, etl_runs)")


def run_agri_ingest_raw_only(
  supabase_url: str,
  service_key: str,
  *,
  dry_run: bool,
) -> None:
  """공공 API → agri_price_raw 만 적재 (분석 없음)."""
  from crawler.at_price_trend import ingest_raw_row_from_env

  base = supabase_url.rstrip("/")
  rest = f"{base}/rest/v1"
  headers = _rest_headers(service_key)

  raw_db_row = ingest_raw_row_from_env()
  if not raw_db_row:
    print(
      "[agri-ingest] DATA_GO_KR_SERVICE_KEY·AT_PRICE_API_PATH 미설정이거나 API 호출 실패.",
      file=sys.stderr,
    )
    sys.exit(2)

  if dry_run:
    print(
      json.dumps(
        {"keys": list(raw_db_row.keys()), "item_count": len(raw_db_row.get("items") or [])},
        ensure_ascii=False,
        indent=2,
      )
    )
    return

  with httpx.Client(timeout=120.0) as client:
    _upsert_agri_price_raw(client, rest, headers, raw_db_row)
    try:
      n_h = _upsert_agri_price_history_batch(client, rest, headers, raw_db_row.get("items") or [])
      print(f"OK: agri_price_history upsert {n_h} rows", flush=True)
    except Exception as e:
      print(f"[agri_price_history] {e}", flush=True)
    _upload_etl_runs(client, rest, headers, [("crawl_agri_ingest_raw", f"items={len(raw_db_row.get('items') or [])}")])
  print("OK: agri_price_raw 원본 적재 (etl_runs)")


def run_agri_analyze_from_stored_raw(
  supabase_url: str,
  service_key: str,
  *,
  dry_run: bool,
) -> None:
  """Supabase agri_price_raw(latest) 읽기 → analysis-1 + agri_price_analytics."""
  base = supabase_url.rstrip("/")
  rest = f"{base}/rest/v1"
  headers = _rest_headers(service_key)

  with httpx.Client(timeout=120.0) as client:
    stored = _fetch_agri_price_raw_latest(client, rest, headers)
    if not stored:
      print(
        "[agri-analyze] agri_price_raw 에 slug=latest 행이 없습니다. --agri-ingest-raw 또는 --agri-public-only 로 원본을 먼저 넣으세요.",
        file=sys.stderr,
      )
      sys.exit(3)

    full = _agri_package_from_supabase_stored(client, rest, headers, stored)
    if dry_run:
      it_a, src = _items_for_latest_agri_analytics(client, rest, headers, stored)
      n_items = len(it_a) if it_a else len(_items_from_agri_raw_row(stored))
      print(
        json.dumps(
          {
            "item_count": n_items,
            "analytics_items_source": src.get("analytics_items_source"),
            "charts_keys": list(full["charts"].keys()),
            "db_row_keys": list(full["db_row"].keys()),
          },
          ensure_ascii=False,
          indent=2,
        )
      )
      return

    c = full["charts"]
    _upload_analysis(
      client,
      rest,
      headers,
      page="analysis-1",
      line=c["line"],
      bar=c["bar"],
      donut=c["donut"],
      accents=c["accents"],
    )
    _upsert_agri_analytics(client, rest, headers, full["db_row"])
    _upload_etl_runs(
      client,
      rest,
      headers,
      [("crawl_agri_analyze_from_raw", "analysis-1+agri_price_analytics")],
    )
  print("OK: Supabase(히스토리 우선) 기반 analysis-1 + agri_price_analytics (+ etl_runs)")


def run_agri_public_data_only(
  supabase_url: str,
  service_key: str,
  *,
  dry_run: bool,
) -> None:
  """공공데이터만: 원본 API → agri_price_raw 저장 후, 동일 DB 스냅샷으로 분석·저장."""
  from crawler.at_price_trend import ingest_raw_row_from_env

  base = supabase_url.rstrip("/")
  rest = f"{base}/rest/v1"
  headers = _rest_headers(service_key)

  raw_db_row = ingest_raw_row_from_env()
  if not raw_db_row:
    print(
      "[agri-public] DATA_GO_KR_SERVICE_KEY·AT_PRICE_API_PATH 미설정이거나 API 호출 실패(URL·JSON·resultCode 확인).",
      file=sys.stderr,
    )
    sys.exit(2)

  if dry_run:
    print(
      json.dumps(
        {
          "raw_db_row_keys": list(raw_db_row.keys()),
          "raw_item_count": len(raw_db_row.get("items") or []),
          "pipeline": "ingest_raw → read back agri_price_raw → build analytics",
        },
        ensure_ascii=False,
        indent=2,
      )
    )
    return

  with httpx.Client(timeout=120.0) as client:
    _upsert_agri_price_raw(client, rest, headers, raw_db_row)
    try:
      n_h = _upsert_agri_price_history_batch(client, rest, headers, raw_db_row.get("items") or [])
      print(f"OK: agri_price_history upsert {n_h} rows", flush=True)
    except Exception as e:
      print(f"[agri_price_history] {e}", flush=True)
    stored = _fetch_agri_price_raw_latest(client, rest, headers)
    if not stored:
      raise SystemExit(
        "agri_price_raw 저장 후 조회에 실패했습니다. Supabase에 scripts/supabase_agri_price_analytics.sql 을 적용했는지 확인하세요."
      )
    full = _agri_package_from_supabase_stored(client, rest, headers, stored)
    c = full["charts"]
    _upload_analysis(client, rest, headers, page="analysis-1", line=c["line"], bar=c["bar"], donut=c["donut"], accents=c["accents"])
    _upsert_agri_analytics(client, rest, headers, full["db_row"])
    _upload_etl_runs(
      client,
      rest,
      headers,
      [("crawl_agri_public_only", "ingest_raw→read_back→analysis-1+agri_price_analytics")],
    )
  print("OK: 원본(agri_price_raw) 적재 후 저장본 기준 가공(analysis-1, agri_price_analytics, etl_runs)")


def main() -> None:
  _load_dotenv()
  parser = argparse.ArgumentParser(description="크롤/샘플 ETL → Supabase")
  parser.add_argument("--mode", choices=["crawl", "sample"], default="crawl", help="crawl=RSS 기반, sample=난수 샘플")
  parser.add_argument("--all", action="store_true", help="--mode crawl: 모든 카테고리·지역(+분석 4페이지)")
  parser.add_argument("--category", default="agri", help="워드클라우드 category")
  parser.add_argument("--region", default="kr", help="워드클라우드 region (kr|global)")
  parser.add_argument("--page", default="analysis-1", dest="analysis_page", help="--mode sample 전용 분석 page")
  parser.add_argument(
    "--supabase-url",
    default=os.getenv("SUPABASE_URL", "").strip(),
    help="또는 SUPABASE_URL",
  )
  parser.add_argument(
    "--service-role-key",
    default=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
    help="또는 SUPABASE_SERVICE_ROLE_KEY",
  )
  parser.add_argument("--dry-run", action="store_true")
  parser.add_argument(
    "--agri-public-only",
    action="store_true",
    help="공공 API로 원본(agri_price_raw) 저장 후, DB에서 읽어 analysis-1·agri_price_analytics 반영",
  )
  parser.add_argument(
    "--agri-ingest-raw",
    action="store_true",
    help="공공 API → agri_price_raw 만 적재",
  )
  parser.add_argument(
    "--agri-analyze-from-stored",
    action="store_true",
    help="Supabase agri_price_raw(latest)만 읽어 analysis-1·agri_price_analytics 갱신",
  )
  args = parser.parse_args()

  if not args.supabase_url or not args.service_role_key:
    print("SUPABASE_URL 과 SUPABASE_SERVICE_ROLE_KEY 가 필요합니다 (.env 또는 인자).", file=sys.stderr)
    sys.exit(1)

  if args.agri_ingest_raw:
    run_agri_ingest_raw_only(args.supabase_url, args.service_role_key, dry_run=args.dry_run)
    return

  if args.agri_analyze_from_stored:
    run_agri_analyze_from_stored_raw(args.supabase_url, args.service_role_key, dry_run=args.dry_run)
    return

  if args.agri_public_only:
    run_agri_public_data_only(args.supabase_url, args.service_role_key, dry_run=args.dry_run)
    return

  if args.mode == "sample":
    run_etl(
      args.supabase_url,
      args.service_role_key,
      category=args.category,
      region=args.region,
      analysis_page=args.analysis_page,
      dry_run=args.dry_run,
    )
  else:
    run_crawl_etl(
      args.supabase_url,
      args.service_role_key,
      category=args.category,
      region=args.region,
      load_all=args.all,
      dry_run=args.dry_run,
    )


if __name__ == "__main__":
  main()
