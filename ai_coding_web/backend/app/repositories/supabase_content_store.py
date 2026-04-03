"""
워드클라우드·분석 스냅샷을 Supabase PostgREST로 읽고(필요 시 service_role로 씀).

단순 스크립트: category, region, text — scripts/supabase_etl_schema.sql
정규화 스키마: category_code, wc_region_code, term_text 및 etl_runs(source_code, status_code)
→ 환경변수 SUPABASE_WORDCLOUD_SCHEMA=normalized

로컬 SQLite(ContentStore)와 동일한 메서드 모양으로 서비스에 주입합니다.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import httpx

from backend.app.config import Settings
from backend.app.models.analysis import Accents
from backend.app.models.types import Category, Page, Region
from backend.app.models.wordcloud import Word


def _use_normalized_supabase(_settings: Settings) -> bool:
  """환경변수 SUPABASE_WORDCLOUD_SCHEMA=normalized 일 때만 FK·코드형 wordcloud/etl_runs 스키마를 사용합니다."""
  v = (os.getenv("SUPABASE_WORDCLOUD_SCHEMA", "") or "").strip().lower()
  return v in ("1", "true", "yes", "normalized")


class SupabaseContentStore:
  def __init__(self, settings: Settings):
    self._url = settings.supabase_url.rstrip("/")
    self._rest = f"{self._url}/rest/v1"
    self._key = settings.supabase_service_role_key.strip() or settings.supabase_anon_key.strip()
    if not self._key:
      raise ValueError("Supabase content store requires SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY")
    self._normalized = _use_normalized_supabase(settings)

  def _headers(self, *, minimal: bool = True) -> dict[str, str]:
    h = {
      "apikey": self._key,
      "Authorization": f"Bearer {self._key}",
      "Content-Type": "application/json",
    }
    if minimal:
      h["Prefer"] = "return=minimal"
    return h

  @staticmethod
  def _map_etl_source_code(source: str) -> str:
    s = (source or "").lower()
    if "crawl" in s or "rss" in s or "news" in s:
      return "news"
    return "internal_etl"

  @staticmethod
  def _map_etl_status_code(status: str) -> str:
    if status in ("success", "failed", "running"):
      return status
    return "success"

  def get_wordcloud(self, category: Category, region: Region) -> List[Dict[str, float]]:
    if self._normalized:
      params: dict[str, str] = {
        "wc_region_code": f"eq.{region}",
        "select": "term_text,weight,category_code",
        "order": "weight.desc",
        "limit": "80",
      }
      if category != "all":
        params["category_code"] = f"eq.{category}"
      text_key = "term_text"
    else:
      params = {"region": f"eq.{region}", "select": "text,weight", "order": "weight.desc", "limit": "80"}
      if category != "all":
        params["category"] = f"eq.{category}"
      text_key = "text"

    with httpx.Client(timeout=45.0) as client:
      r = client.get(f"{self._rest}/wordcloud_terms", headers=self._headers(), params=params)
      r.raise_for_status()
      rows = r.json()

    if category == "all":
      merged: Dict[str, float] = {}
      for row in rows:
        t = str(row.get(text_key, ""))
        if not t:
          continue
        merged[t] = merged.get(t, 0.0) + float(row.get("weight") or 0)
      words = [{"text": k, "weight": v} for k, v in merged.items()]
      words.sort(key=lambda item: float(item["weight"]), reverse=True)
      return words[:28]

    return [{"text": str(row[text_key]), "weight": float(row["weight"])} for row in rows[:28]]

  def set_wordcloud(self, category: Category, region: Region, words: List[Word]) -> int:
    if category == "all":
      raise ValueError("ingest 시 category=all 은 지원하지 않습니다.")

    if self._normalized:
      del_params = {"category_code": f"eq.{category}", "wc_region_code": f"eq.{region}"}

      def row_builder(d: dict) -> dict:
        return {
          "category_code": category,
          "wc_region_code": region,
          "term_text": str(d["text"]),
          "weight": float(d["weight"]),
        }
    else:
      del_params = {"category": f"eq.{category}", "region": f"eq.{region}"}

      def row_builder(d: dict) -> dict:
        return {"category": category, "region": region, "text": str(d["text"]), "weight": float(d["weight"])}

    with httpx.Client(timeout=60.0) as client:
      dr = client.delete(f"{self._rest}/wordcloud_terms", headers=self._headers(), params=del_params)
      if dr.status_code not in (200, 204):
        dr.raise_for_status()

      payload = []
      for word in words:
        d = word.model_dump() if hasattr(word, "model_dump") else dict(word)
        payload.append(row_builder(d))

      if not payload:
        return 0
      ir = client.post(f"{self._rest}/wordcloud_terms", headers=self._headers(), content=json.dumps(payload).encode())
      ir.raise_for_status()
    return len(payload)

  def get_analysis(self, page: Page) -> Optional[Dict]:
    with httpx.Client(timeout=45.0) as client:
      r = client.get(
        f"{self._rest}/analysis_snapshots",
        headers=self._headers(),
        params={"page": f"eq.{page}", "select": "line,bar,donut,accents", "limit": "1"},
      )
      r.raise_for_status()
      rows = r.json()
    if not rows:
      return None
    row = rows[0]
    return {
      "line": list(row.get("line") or []),
      "bar": list(row.get("bar") or []),
      "donut": list(row.get("donut") or []),
      "accents": dict(row.get("accents") or {"line": "#6AE4FF", "bar": "#B79BFF"}),
    }

  def set_analysis(
    self,
    page: Page,
    line: List[float],
    bar: List[float],
    donut: List[float],
    accents: Optional[Accents],
  ) -> None:
    body = {
      "page": page,
      "line": list(line),
      "bar": list(bar),
      "donut": list(donut),
      "accents": (accents.model_dump() if accents else None) or {"line": "#6AE4FF", "bar": "#B79BFF"},
    }
    headers = {**self._headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    with httpx.Client(timeout=60.0) as client:
      r = client.post(
        f"{self._rest}/analysis_snapshots?on_conflict=page",
        headers=headers,
        content=json.dumps([body], ensure_ascii=False).encode(),
      )
      r.raise_for_status()

  def seed_defaults(self) -> None:
    return

  def record_etl_run(self, source: str, status: str, details: str = "") -> None:
    if self._normalized:
      row = {
        "source_code": self._map_etl_source_code(source),
        "status_code": self._map_etl_status_code(status),
        "details": details or "",
      }
    else:
      row = {"source": source, "status": status, "details": details or ""}

    with httpx.Client(timeout=30.0) as client:
      r = client.post(
        f"{self._rest}/etl_runs",
        headers=self._headers(),
        content=json.dumps([row], ensure_ascii=False).encode(),
      )
      if r.status_code not in (200, 201):
        r.raise_for_status()
