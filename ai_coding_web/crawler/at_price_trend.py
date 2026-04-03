"""
한국농수산식품유통공사 「가격 추이 정보」류 OpenAPI 연동.

- 인증키·요청 경로는 공공데이터포털(data.go.kr) 해당 API 상세 → 활용신청 → 마이페이지 인증키,
  및 첨부 명세의 요청주소·필수 파라미터를 .env 에 맞춥니다.
- 참고: https://www.data.go.kr/data/15156069/openapi.do

응답은 일반적인 공공데이터포털 JSON 형식(response.header / response.body.items.item)을 가정합니다.
priceSequel/info 응답 필드: exmn_dd_avg_prc, ww1_bfr~ww4_bfr, item_nm, ctgry_nm 등.
요청은 returnType·필수 cond[exmn_ymd::EQ](YYYYMMDD)를 맞춥니다(미설정 시 KST 전일).
다건 이력: AT_PRICE_HISTORY_YEARS(기본 3)·올해까지 월 1회 샘플(매월 15일·당월은 오늘까지)로 조회 후 병합합니다.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import os
import re
import statistics
import time
from datetime import date, datetime, timedelta, timezone
from collections import Counter, defaultdict
from typing import Any

import httpx

# 명세: B552845/priceSequel/info — 4주전→당일 (ww4…ww1, exmn_dd). kg환산(cnvs) 우선.
# 구 명세 한글·타 서비스 별칭 병행.
_COND_EXMN_YMD = "cond[exmn_ymd::EQ]"

_TREND_COLS: list[tuple[str, ...]] = [
  (
    "ww4_bfr_cnvs_avg_prc",
    "ww4_bfr_avg_prc",
    "4주일전kg환산평균가격",
    "4주일전평균가격",
  ),
  (
    "ww3_bfr_cnvs_avg_prc",
    "ww3_bfr_avg_prc",
    "3주일전kg환산평균가격",
    "3주일전평균가격",
  ),
  (
    "ww2_bfr_cnvs_avg_prc",
    "ww2_bfr_avg_prc",
    "2주일전kg환산평균가격",
    "2주일전평균가격",
  ),
  (
    "ww1_bfr_cnvs_avg_prc",
    "ww1_bfr_avg_prc",
    "1주일전kg환산평균가격",
    "1주일전평균가격",
  ),
  (
    "exmn_dd_cnvs_avg_prc",
    "exmn_dd_avg_prc",
    "조사일kg환산평균가격",
    "조사일평균가격",
  ),
]

_NAME_KEYS = ("item_nm", "품목명", "itemName", "prductName", "productName")
_CATEGORY_KEYS = ("ctgry_nm", "부류명", "grpNm", "className", "productClsName")

# 지역·시장 구분(명세 필드명이 다를 수 있어 병렬 매칭)
_REGION_KEYS = (
  "조사지역명",
  "지역명",
  "시장명",
  "marketName",
  "saleArea",
  "areaNm",
  "도매시장명",
  "whsalName",
  "whsalNm",
  "cntyName",
)


def _service_base() -> str:
  return (os.getenv("AT_PRICE_API_BASE", "https://apis.data.go.kr") or "https://apis.data.go.kr").rstrip("/")


def _default_survey_date_ymd() -> str:
  """priceSequel 필수 cond[exmn_ymd::EQ] 기본값: KST 기준 전일(데이터 미공개일 대비)."""
  kst = timezone(timedelta(hours=9))
  d = datetime.now(kst).date() - timedelta(days=1)
  return d.strftime("%Y%m%d")


def _kst_today() -> date:
  kst = timezone(timedelta(hours=9))
  return datetime.now(kst).date()


def _monthly_survey_dates_ymd(*, years_back: int) -> list[str]:
  """
  올해(KST)를 끝으로, (올해 − years_back)년 1월부터 월 1회 조사일 후보(15일, 당월은 today 초과 시 today).
  예: years_back=3 → 2023-01 ~ 오늘이 속한 달까지.
  """
  today = _kst_today()
  start_year = today.year - int(years_back)
  y, m = start_year, 1
  out: list[str] = []
  while y < today.year or (y == today.year and m <= today.month):
    last = calendar.monthrange(y, m)[1]
    day = min(15, last)
    d = date(y, m, day)
    if d > today:
      d = today
    out.append(d.strftime("%Y%m%d"))
    if m == 12:
      y, m = y + 1, 1
    else:
      m += 1
  return out


def _item_exmn_ymd(it: dict[str, Any]) -> str:
  v = it.get("exmn_ymd") or it.get("exmnYmd") or ""
  return str(v).strip()


def _latest_exmn_items_only(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
  """여러 조사일이 섞인 원본 중 가장 최근 exmn_ymd 행만 (차트·집계용)."""
  dates = [_item_exmn_ymd(it) for it in items if _item_exmn_ymd(it)]
  if not dates:
    return items
  latest = max(dates)
  return [it for it in items if _item_exmn_ymd(it) == latest]


def _dedupe_historical_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
  seen: set[tuple[str, ...]] = set()
  out: list[dict[str, Any]] = []
  for it in items:
    key = (
      _item_exmn_ymd(it),
      str(it.get("item_cd") or ""),
      str(it.get("vrty_cd") or ""),
      str(it.get("grd_cd") or ""),
      str(it.get("se_cd") or ""),
    )
    if key in seen:
      continue
    seen.add(key)
    out.append(it)
  return out


def _parse_item_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
  """표준 포털 JSON에서 item 리스트 추출."""
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


def _to_float(v: Any) -> float | None:
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


def _item_prices_series(it: dict[str, Any]) -> list[float] | None:
  vals: list[float] = []
  for keys in _TREND_COLS:
    n: float | None = None
    for k in keys:
      if k in it:
        n = _to_float(it.get(k))
        if n is not None:
          break
    if n is None:
      return None
    vals.append(n)
  return vals


def _item_name(it: dict[str, Any]) -> str:
  for k in _NAME_KEYS:
    v = it.get(k)
    if v:
      return str(v).strip()[:40]
  return "항목"


def _item_category(it: dict[str, Any]) -> str:
  for k in _CATEGORY_KEYS:
    v = it.get(k)
    if v:
      return str(v).strip()[:24]
  return "기타"


def _item_region(it: dict[str, Any]) -> str:
  for k in _REGION_KEYS:
    v = it.get(k)
    if v:
      return str(v).strip()[:80]
  return "미상"


def _current_price(it: dict[str, Any]) -> float | None:
  return _to_float(
    it.get("exmn_dd_cnvs_avg_prc")
    or it.get("exmn_dd_avg_prc")
    or it.get("조사일kg환산평균가격")
    or it.get("조사일평균가격")
  )


def _linear_forecast_next(y: list[float]) -> tuple[float, float, str]:
  """주차 인덱스 0..n-1 선형회귀 후 다음 시점(t=n) 추정."""
  n = len(y)
  if n < 2:
    return (float(y[-1]) if y else 0.0), 0.0, "시계열 2점 미만"
  sx = sum(range(n))
  sxx = sum(i * i for i in range(n))
  sy = sum(y)
  sxy = sum(i * y[i] for i in range(n))
  denom = n * sxx - sx * sx
  if denom == 0:
    return float(y[-1]), 0.0, "기울기 산출 불가"
  b = (n * sxy - sx * sy) / denom
  a = (sy - b * sx) / n
  nxt = a + b * n
  return round(max(0.0, nxt), 4), round(b, 6), "주차 평균 시계열 선형 1스텝 외삽"


def _expand_5_to_12(series: list[float]) -> list[float]:
  if len(series) < 2:
    v = float(series[0]) if series else 0.0
    return [max(4.0, v % 80 or 10.0)] * 12
  out: list[float] = []
  n = len(series) - 1
  for i in range(12):
    x = i / 11 * n
    j = int(x)
    t = x - j
    if j >= n:
      out.append(float(series[-1]))
    else:
      a, b = float(series[j]), float(series[j + 1])
      out.append(round(a + t * (b - a), 2))
  return out


def _scale_series(vals: list[float], *, lo: float = 8.0, hi: float = 88.0) -> list[float]:
  if not vals:
    return [lo] * 12
  mn, mx = min(vals), max(vals)
  if mx <= mn:
    return [round((lo + hi) / 2, 2)] * len(vals)
  return [round(lo + (x - mn) / (mx - mn) * (hi - lo), 2) for x in vals]


def build_charts_from_items(items: list[dict[str, Any]]) -> dict[str, Any]:
  """
  여러 관점 반영:
  - line: 품목들의 (4주전→당일) 가격 추이 평균 → 12포인트 보간·스케일
  - bar: 당일(조사일) 평균가 상위 5개 품목의 상대 스케일
  - donut: 부류명(없으면 기타) 상위 4개 비중
  """
  series_list: list[list[float]] = []
  current_prices: list[tuple[str, float]] = []
  for it in items:
    s = _item_prices_series(it)
    if s:
      series_list.append(s)
    cur = _current_price(it)
    if cur is not None:
      current_prices.append((_item_name(it), cur))

  accents = {"line": "#9AF7D0", "bar": "#6AE4FF"}

  if len(series_list) < 1:
    line = [12, 14, 13, 15, 16, 18, 17, 19, 20, 21, 22, 24]
    bar = [10.0, 14.0, 12.0, 16.0, 13.0]
    donut = [35.0, 28.0, 22.0, 15.0]
    return {"line": line, "bar": bar, "donut": donut, "accents": accents}

  n = len(_TREND_COLS)
  means = []
  for i in range(n):
    col = [s[i] for s in series_list if len(s) > i]
    if col:
      means.append(sum(col) / len(col))
    else:
      means.append(0.0)

  line = _scale_series(_expand_5_to_12(means))

  current_prices.sort(key=lambda x: x[1], reverse=True)
  top5 = current_prices[:5]
  if not top5:
    bar = [12.0, 16.0, 14.0, 18.0, 15.0]
  else:
    mxp = top5[0][1] or 1.0
    bar = [max(6.0, round(28.0 * (p / mxp), 2)) for _, p in top5]
    while len(bar) < 5:
      bar.append(8.0)

  cats = [_item_category(it) for it in items]
  cnt = Counter(cats)
  top4 = cnt.most_common(4)
  if len(top4) < 2:
    donut = [40.0, 30.0, 20.0, 10.0]
  else:
    total = sum(c for _, c in top4) or 1
    donut = [max(8.0, round(100.0 * c / total, 2)) for _, c in top4]
    while len(donut) < 4:
      donut.append(12.0)

  return {"line": line, "bar": bar[:5], "donut": donut[:4], "accents": accents}


def build_deep_analytics(items: list[dict[str, Any]], *, charts: dict[str, Any]) -> dict[str, Any]:
  """지역별 min/max/평균, 전체 분포, 가격대 분위, 주차 평균 시계열 기반 단기 추정."""
  prices_all: list[float] = []
  by_region: dict[str, list[float]] = defaultdict(list)

  for it in items:
    p = _current_price(it)
    if p is None:
      continue
    prices_all.append(p)
    by_region[_item_region(it)].append(p)

  overall: dict[str, Any] = {}
  if prices_all:
    overall = {
      "min": round(min(prices_all), 2),
      "max": round(max(prices_all), 2),
      "avg": round(sum(prices_all) / len(prices_all), 2),
      "spread": round(max(prices_all) - min(prices_all), 2),
      "count": len(prices_all),
    }

  region_stats: list[dict[str, Any]] = []
  for reg, ps in by_region.items():
    if not ps:
      continue
    region_stats.append(
      {
        "region": reg,
        "min": round(min(ps), 2),
        "max": round(max(ps), 2),
        "avg": round(sum(ps) / len(ps), 2),
        "count": len(ps),
      }
    )
  region_stats.sort(key=lambda x: (-x["count"], x["region"]))

  distribution: dict[str, Any] = {"bins": [], "unit_hint": "원(명세 기준, kg환산·평균가 등)"}
  if prices_all:
    srt = sorted(prices_all)
    n = len(srt)
    bins = []
    for i in range(5):
      lo_i = int(n * i / 5)
      hi_i = (int(n * (i + 1) / 5) - 1) if i < 4 else n - 1
      chunk = srt[lo_i : hi_i + 1]
      if chunk:
        bins.append(
          {
            "label": f"Q{i + 1}",
            "price_min": round(chunk[0], 2),
            "price_max": round(chunk[-1], 2),
            "count": len(chunk),
          }
        )
    distribution["bins"] = bins

  # 평균 주차 시계열(4주전→당일) — build_charts와 동일 로직
  series_list: list[list[float]] = []
  for it in items:
    s = _item_prices_series(it)
    if s:
      series_list.append(s)
  mean_series: list[float] = []
  if series_list:
    for i in range(len(_TREND_COLS)):
      col = [s[i] for s in series_list if len(s) > i]
      mean_series.append(sum(col) / len(col) if col else 0.0)

  forecast: dict[str, Any] = {
    "method": "linear_extrapolation",
    "note": "단기 선형 외삽·참고용이며 실제 거래가와 다를 수 있습니다.",
  }
  if len(mean_series) >= 2:
    nxt, slope, _txt = _linear_forecast_next(mean_series)
    prev, last = mean_series[-2], mean_series[-1]
    wow = round((100.0 * (last - prev) / prev), 2) if prev else 0.0
    forecast.update(
      {
        "mean_series_weeks": [round(x, 2) for x in mean_series],
        "labels_weeks": ["4주전", "3주전", "2주전", "1주전", "조사일"],
        "next_step_estimate": nxt,
        "slope_per_week": slope,
        "week_over_week_pct": wow,
      }
    )

  return {
    "overall": overall,
    "region_stats": region_stats,
    "distribution": distribution,
    "forecast": forecast,
    "charts": {
      "line": charts.get("line", []),
      "bar": charts.get("bar", []),
      "donut": charts.get("donut", []),
      "accents": charts.get("accents", {}),
    },
  }


def item_natural_key(it: dict[str, Any]) -> str:
  """동일 품목을 조사일 간 매칭하기 위한 키(코드 우선, 없으면 명칭 해시)."""
  parts = [str(it.get(k) or "").strip() for k in ("se_cd", "item_cd", "vrty_cd", "grd_cd")]
  if any(parts):
    return "|".join(parts)[:400]
  blob = f"{it.get('item_nm', '')}|{it.get('vrty_nm', '')}|{it.get('grd_nm', '')}"
  return "h:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:40]


def build_extended_history_analytics(items: list[dict[str, Any]]) -> dict[str, Any]:
  """
  여러 조사일(exmn_ymd)이 섞인 원본으로, 연속 조사일 쌍 간 가격 변동 요약.
  (API 필드 ww1~는 '조사일 기준 주간'이고, 여기서는 '저장된 조사일 스냅샷' 간 비교.)
  """
  by_key: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
  dates_set: set[str] = set()
  for it in items:
    ymd = _item_exmn_ymd(it)
    if not ymd:
      continue
    dates_set.add(ymd)
    by_key[item_natural_key(it)].append((ymd, it))

  distinct_dates = sorted(dates_set)
  out: dict[str, Any] = {
    "survey_dates_distinct": distinct_dates,
    "survey_date_count": len(distinct_dates),
    "item_key_count": len(by_key),
  }
  if len(distinct_dates) < 2:
    out["note"] = "저장된 조사일이 2개 미만이면 조사일 간 전수 비교는 제한됩니다."
    return out

  d_prev, d_last = distinct_dates[-2], distinct_dates[-1]
  movers: list[dict[str, Any]] = []
  changes: list[float] = []
  for key, row_list in by_key.items():
    m_prev = next((it for y, it in row_list if y == d_prev), None)
    m_last = next((it for y, it in row_list if y == d_last), None)
    if not m_prev or not m_last:
      continue
    p0 = _current_price(m_prev)
    p1 = _current_price(m_last)
    if p0 is None or p1 is None or p0 == 0:
      continue
    pct = 100.0 * (p1 - p0) / p0
    changes.append(pct)
    movers.append(
      {
        "item_key": key,
        "item_nm": _item_name(m_last),
        "exmn_ymd_prev": d_prev,
        "exmn_ymd_last": d_last,
        "price_prev": round(p0, 2),
        "price_last": round(p1, 2),
        "pct_change": round(pct, 2),
      }
    )
  movers.sort(key=lambda x: abs(x["pct_change"]), reverse=True)
  out["latest_survey_pair"] = {"prev": d_prev, "last": d_last}
  out["median_pct_change_prev_to_last_survey"] = (
    round(float(statistics.median(changes)), 2) if changes else None
  )
  out["top_movers_by_abs_pct_change"] = movers[:40]
  rising = sorted((m for m in movers if m["pct_change"] > 0), key=lambda x: -x["pct_change"])[:15]
  falling = sorted((m for m in movers if m["pct_change"] < 0), key=lambda x: x["pct_change"])[:15]
  out["top_risers_pct"] = rising
  out["top_fallers_pct"] = falling
  return out


def _opt_code_str(v: Any) -> str | None:
  if v is None:
    return None
  s = str(v).strip()
  return s if s and s.lower() != "none" else None


def agri_price_history_row(it: dict[str, Any]) -> dict[str, Any] | None:
  """Supabase agri_price_history upsert용 행. 조사일·키 없으면 스킵."""
  ymd = _item_exmn_ymd(it)
  if not ymd:
    return None
  ik = item_natural_key(it)
  if not ik:
    return None
  return {
    "exmn_ymd": ymd,
    "item_key": ik,
    "item_cd": _opt_code_str(it.get("item_cd")),
    "vrty_cd": _opt_code_str(it.get("vrty_cd")),
    "grd_cd": _opt_code_str(it.get("grd_cd")),
    "se_cd": _opt_code_str(it.get("se_cd")),
    "payload": dict(it),
  }


def fetch_price_items(
  *,
  service_key: str,
  api_path: str,
  timeout: float = 45.0,
  max_rows: int = 200,
  override_exmn_ymd: str | None = None,
  paginate_all: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  """
  api_path: 명세의 경로(예: /B552xxx/서비스명/오퍼레이션명). 선행 슬래시 있거나 없어도 됨.
  추가 쿼리는 AT_PRICE_API_QUERY_JSON 환경변수(JSON 객체 문자열).
  override_exmn_ymd: 이력 수집 시 해당 조사일로 cond[exmn_ymd::EQ] 고정.
  paginate_all: totalCount/pageNo 기준 전 페이지 병합.
  """
  path = api_path.strip().replace("//", "/")
  if not path.startswith("/"):
    path = "/" + path
  url = _service_base() + path

  base: dict[str, Any] = {
    "serviceKey": service_key,
    "numOfRows": max_rows,
  }
  rt = (os.getenv("AT_PRICE_RESULT_TYPE", "json") or "json").strip().lower()
  if rt in ("json", "xml"):
    base["returnType"] = "json" if rt == "json" else "xml"
    base["resultType"] = rt

  extra_raw = (os.getenv("AT_PRICE_API_QUERY_JSON") or "").strip()
  if extra_raw:
    try:
      extra = json.loads(extra_raw)
      if isinstance(extra, dict):
        base.update({k: v for k, v in extra.items() if v is not None})
    except json.JSONDecodeError:
      pass

  if override_exmn_ymd:
    base[_COND_EXMN_YMD] = override_exmn_ymd.strip()
  else:
    exmn = (base.get(_COND_EXMN_YMD) or "").strip()
    if not exmn:
      exmn = (os.getenv("AT_PRICE_EXMN_YMD") or "").strip()
    if not exmn:
      exmn = _default_survey_date_ymd()
    base[_COND_EXMN_YMD] = exmn

  def _one_page(client: httpx.Client, page_no: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {**base, "pageNo": page_no}
    r = client.get(url, params=params)
    r.raise_for_status()
    try:
      data = r.json()
    except Exception as err:
      raise ValueError(f"JSON 파싱 실패(응답이 XML일 수 있음). returnType/json·명세 확인: {err}") from err

    head = (data.get("response") or {}).get("header") or {}
    code = str(head.get("resultCode", "00"))
    if code not in ("00", "0", "NORMAL_SERVICE"):
      msg = head.get("resultMsg", "")
      raise RuntimeError(f"공공데이터 API 오류 resultCode={code} {msg}")

    body = (data.get("response") or {}).get("body") or {}
    tc_raw = body.get("totalCount")
    try:
      total_count = int(tc_raw) if tc_raw is not None else None
    except (TypeError, ValueError):
      total_count = None
    api_meta = {
      "totalCount": total_count,
      "resultCode": str(head.get("resultCode", "")),
      "resultMsg": str(head.get("resultMsg", ""))[:500],
    }
    return _parse_item_list(data), api_meta

  with httpx.Client(timeout=timeout, headers={"User-Agent": "EtDemoETL/1.0"}, follow_redirects=True) as client:
    if not paginate_all:
      items, api_meta = _one_page(client, 1)
      return items, api_meta

    all_items: list[dict[str, Any]] = []
    page = 1
    last_meta: dict[str, Any] = {}
    total_count: int | None = None
    while page <= 1000:
      items, api_meta = _one_page(client, page)
      last_meta = api_meta
      tc = api_meta.get("totalCount")
      if isinstance(tc, int):
        total_count = tc
      all_items.extend(items)
      if not items:
        break
      if total_count is not None and len(all_items) >= total_count:
        break
      if len(items) < max_rows:
        break
      page += 1

    merged_meta = {
      **last_meta,
      "pages_fetched": page,
      "items_returned": len(all_items),
    }
    if total_count is not None:
      merged_meta["totalCount"] = total_count
    return all_items, merged_meta


def fetch_price_items_history_merged(
  *,
  service_key: str,
  api_path: str,
  timeout: float = 45.0,
  max_rows: int = 200,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  """
  올해 기준 years_back년 전 1월~현재까지 월별 조사일로 반복 호출 후 item 병합.
  AT_PRICE_HISTORY_YEARS: 기본 3, 0이면 단일 조사일(기본 cond)·paginate_all 만 사용.
  AT_PRICE_REQUEST_SLEEP_SEC: 호출 간 대기(기본 0.25).
  """
  raw_y = (os.getenv("AT_PRICE_HISTORY_YEARS") or "3").strip()
  try:
    years_back = int(raw_y)
  except ValueError:
    years_back = 3

  sleep_s = float((os.getenv("AT_PRICE_REQUEST_SLEEP_SEC") or "0.25").strip() or "0.25")

  if years_back <= 0:
    return fetch_price_items(
      service_key=service_key,
      api_path=api_path,
      timeout=timeout,
      max_rows=max_rows,
      paginate_all=True,
    )

  dates = _monthly_survey_dates_ymd(years_back=years_back)
  merged: list[dict[str, Any]] = []
  errors: list[dict[str, Any]] = []
  sum_tc = 0

  for i, ymd in enumerate(dates):
    try:
      items, meta = fetch_price_items(
        service_key=service_key,
        api_path=api_path,
        timeout=timeout,
        max_rows=max_rows,
        override_exmn_ymd=ymd,
        paginate_all=True,
      )
      merged.extend(items)
      tc = meta.get("totalCount")
      if isinstance(tc, int):
        sum_tc += tc
    except Exception as err:
      errors.append({"ymd": ymd, "error": str(err)[:400]})
    if i + 1 < len(dates) and sleep_s > 0:
      time.sleep(sleep_s)

  merged = _dedupe_historical_rows(merged)
  api_meta: dict[str, Any] = {
    "history_merge": True,
    "history_years_back": years_back,
    "sample_dates": dates,
    "sample_count": len(dates),
    "items_merged": len(merged),
    "totalCount_sum_reported": sum_tc,
    "fetch_errors": errors,
    "resultCode": "0",
    "resultMsg": "",
    "totalCount": len(merged),
  }
  return merged, api_meta


def build_agri_supabase_rows_from_items(
  items: list[dict[str, Any]],
  *,
  api_meta: dict[str, Any] | None = None,
  source: str = "data_go_kr",
  meta_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
  """
  원본 item 리스트로 차트·분석 `db_row`·원본 upsert용 `raw_db_row`를 만듭니다.
  여러 조사일이 섞인 이력 원본은 차트·집계에만 최신 exmn_ymd 행을 씁니다(raw `items`는 전량 유지).
  """
  am = dict(api_meta or {})
  distinct_exmn = {_item_exmn_ymd(it) for it in items if _item_exmn_ymd(it)}
  items_for_charts = _latest_exmn_items_only(items) if len(distinct_exmn) > 1 else items

  charts = build_charts_from_items(items_for_charts)
  analytics = build_deep_analytics(items_for_charts, charts=charts)
  meta: dict[str, Any] = {
    "item_count": len(items),
    "analytics_item_count": len(items_for_charts),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "api_path_hint": (os.getenv("AT_PRICE_API_PATH") or "").strip()[:200],
    "api_total_count": am.get("totalCount"),
    "api_result_code": am.get("resultCode"),
  }
  if len(distinct_exmn) > 1:
    meta["analytics_scope"] = "latest_exmn_ymd_only"
    meta["latest_exmn_ymd"] = max(distinct_exmn)
  if am.get("history_merge"):
    meta["history_years_back"] = am.get("history_years_back")
    meta["history_sample_count"] = am.get("sample_count")
  if not items:
    meta["empty_reason"] = (
      "API가 0건을 반환했습니다. 명세의 필수 쿼리(조사일자·품목코드 등)를 AT_PRICE_API_QUERY_JSON 으로 넣어 보세요."
    )
  if meta_extra:
    meta.update(meta_extra)
  if items:
    meta["history_insights"] = build_extended_history_analytics(items)
  db_row = {
    "slug": "latest",
    "region_stats": analytics["region_stats"],
    "overall": analytics["overall"],
    "forecast": analytics["forecast"],
    "distribution": analytics["distribution"],
    "chart_bundle": analytics["charts"],
    "source": source,
    "meta": meta,
  }
  raw_meta: dict[str, Any] = {
    "item_count": len(items),
    "ingested_at": datetime.now(timezone.utc).isoformat(),
    "api_path_hint": (os.getenv("AT_PRICE_API_PATH") or "").strip()[:200],
    "api_total_count": am.get("totalCount"),
    "api_result_code": am.get("resultCode"),
    **({"empty_reason": meta["empty_reason"]} if not items and "empty_reason" in meta else {}),
  }
  if am.get("history_merge"):
    raw_meta["history_merge"] = True
    raw_meta["history_years_back"] = am.get("history_years_back")
    raw_meta["history_sample_dates"] = am.get("sample_dates")
  raw_db_row = {
    "slug": "latest",
    "items": items,
    "api_meta": am,
    "source": source,
    "meta": raw_meta,
  }
  return {"charts": charts, "analytics": analytics, "db_row": db_row, "raw_db_row": raw_db_row}


def ingest_raw_row_from_env() -> dict[str, Any] | None:
  """
  공공 API만 호출해 `agri_price_raw` upsert용 행(dict)만 만듭니다. 키/경로/API 오류 시 None.
  (분석·차트는 계산하지 않습니다.)
  """
  key = (os.getenv("DATA_GO_KR_SERVICE_KEY") or os.getenv("PUBLIC_DATA_SERVICE_KEY") or "").strip()
  path = (os.getenv("AT_PRICE_API_PATH") or "").strip()
  if not key or not path:
    return None
  try:
    items, api_meta = fetch_price_items_history_merged(service_key=key, api_path=path)
  except Exception:
    return None
  meta: dict[str, Any] = {
    "item_count": len(items),
    "ingested_at": datetime.now(timezone.utc).isoformat(),
    "api_path_hint": (os.getenv("AT_PRICE_API_PATH") or "").strip()[:200],
    "api_total_count": api_meta.get("totalCount"),
    "api_result_code": api_meta.get("resultCode"),
  }
  if api_meta.get("history_merge"):
    meta["history_merge"] = True
    meta["history_years_back"] = api_meta.get("history_years_back")
    meta["history_sample_count"] = api_meta.get("sample_count")
    meta["history_fetch_errors"] = api_meta.get("fetch_errors") or []
  if not items:
    meta["empty_reason"] = (
      "API가 0건을 반환했습니다. 명세의 필수 쿼리(조사일자·품목코드 등)를 AT_PRICE_API_QUERY_JSON 으로 넣어 보세요."
    )
  return {
    "slug": "latest",
    "items": items,
    "api_meta": api_meta,
    "source": "data_go_kr",
    "meta": meta,
  }


def fetch_full_agri_from_env() -> dict[str, Any] | None:
  """API 조회 → 차트 + 심층 분석 + Supabase 행. 인증·경로 없음·HTTP 오류 시 None. item 0건이어도 저장용 패키지 생성."""
  key = (os.getenv("DATA_GO_KR_SERVICE_KEY") or os.getenv("PUBLIC_DATA_SERVICE_KEY") or "").strip()
  path = (os.getenv("AT_PRICE_API_PATH") or "").strip()
  if not key or not path:
    return None
  try:
    items, api_meta = fetch_price_items_history_merged(service_key=key, api_path=path)
  except Exception:
    return None
  return build_agri_supabase_rows_from_items(items, api_meta=api_meta, source="data_go_kr")


def load_agri_analysis_from_env() -> dict[str, Any] | None:
  """환경변수가 있으면 차트만(기존 ETL 호환)."""
  full = fetch_full_agri_from_env()
  return full["charts"] if full else None
