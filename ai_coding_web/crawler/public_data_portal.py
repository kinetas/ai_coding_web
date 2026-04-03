"""
공공데이터포털(data.go.kr) OpenAPI 공통 파싱·호출.
표준 JSON: response.header / response.body.items.item
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx


def parse_portal_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
  body = (payload.get("response") or {}).get("body") or payload.get("body") or {}
  items = body.get("items")
  if items is None:
    return []
  if isinstance(items, dict):
    raw = items.get("item")
  else:
    raw = items
  if raw is None:
    return []
  if isinstance(raw, dict):
    return [raw]
  if isinstance(raw, list):
    return [x for x in raw if isinstance(x, dict)]
  return []


def _portal_base_url() -> str:
  return (os.getenv("PD_API_BASE") or os.getenv("AT_PRICE_API_BASE", "https://apis.data.go.kr") or "https://apis.data.go.kr").rstrip(
    "/"
  )


def fetch_portal_json_pages(
  *,
  service_key: str,
  api_path: str,
  extra_params: dict[str, Any] | None = None,
  timeout: float = 60.0,
  max_rows: int = 500,
  max_pages: int = 200,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  """
  serviceKey + pageNo + numOfRows + returnType/resultType + extra_params 병합.
  totalCount 기준 페이지네이션.
  """
  path = api_path.strip().replace("//", "/")
  if not path.startswith("/"):
    path = "/" + path
  url = _portal_base_url() + path

  base: dict[str, Any] = {
    "serviceKey": service_key,
    "numOfRows": max_rows,
    "pageNo": 1,
  }
  rt = (os.getenv("AT_PRICE_RESULT_TYPE", "json") or "json").strip().lower()
  if rt in ("json", "xml"):
    base["returnType"] = "json" if rt == "json" else "xml"
    base["resultType"] = rt
  if extra_params:
    base.update({k: v for k, v in extra_params.items() if v is not None})

  all_items: list[dict[str, Any]] = []
  last_meta: dict[str, Any] = {}
  total_count: int | None = None

  with httpx.Client(timeout=timeout, headers={"User-Agent": "EtDemoETL/1.0"}, follow_redirects=True) as client:
    page = 1
    while page <= max_pages:
      params = {**base, "pageNo": page}
      r = client.get(url, params=params)
      r.raise_for_status()
      try:
        data = r.json()
      except Exception as err:
        raise ValueError(f"JSON 파싱 실패: {err}") from err
      head = (data.get("response") or {}).get("header") or {}
      code = str(head.get("resultCode", "00"))
      if code not in ("00", "0", "NORMAL_SERVICE"):
        raise RuntimeError(f"공공데이터 API 오류 resultCode={code} {head.get('resultMsg', '')}")

      body = (data.get("response") or {}).get("body") or {}
      tc_raw = body.get("totalCount")
      try:
        total_count = int(tc_raw) if tc_raw is not None else None
      except (TypeError, ValueError):
        total_count = None

      items = parse_portal_items(data)
      last_meta = {
        "totalCount": total_count,
        "resultCode": str(head.get("resultCode", "")),
        "resultMsg": str(head.get("resultMsg", ""))[:500],
        "pageNo": page,
      }
      all_items.extend(items)
      if not items:
        break
      if total_count is not None and len(all_items) >= total_count:
        break
      if len(items) < max_rows:
        break
      page += 1

  meta = {
    **last_meta,
    "pages_fetched": last_meta.get("pageNo", 1),
    "items_returned": len(all_items),
  }
  return all_items, meta


def load_query_dict_from_env(env_value: str | None) -> dict[str, Any]:
  if not (env_value or "").strip():
    return {}
  try:
    o = json.loads(env_value)
    return dict(o) if isinstance(o, dict) else {}
  except json.JSONDecodeError:
    return {}
