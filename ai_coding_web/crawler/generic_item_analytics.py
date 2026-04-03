"""
임의의 dict item[]에서 line/bar/donut·요약·분포를 생성 (스키마가 바뀌어도 동작하도록 단순 휴리스틱).
"""
from __future__ import annotations

import re
from collections import Counter
from statistics import mean
from typing import Any


def _to_float(v: Any) -> float | None:
  if v is None or v == "":
    return None
  s = str(v).strip().replace(",", "")
  if not s:
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


def _pick_numeric_columns(items: list[dict[str, Any]], *, min_frac: float = 0.2) -> list[str]:
  if not items:
    return []
  n = len(items)
  keys: set[str] = set()
  for it in items[: min(200, n)]:
    keys.update(str(k) for k in it.keys())
  scored: list[tuple[str, float]] = []
  for k in keys:
    ok = 0
    for it in items:
      if _to_float(it.get(k)) is not None:
        ok += 1
    frac = ok / n if n else 0
    if frac >= min_frac:
      scored.append((k, frac))
  scored.sort(key=lambda x: (-x[1], x[0]))
  return [k for k, _ in scored[:6]]


def _scale(vals: list[float], *, lo: float = 6.0, hi: float = 88.0) -> list[float]:
  if not vals:
    return [lo] * len(vals)
  vmin, vmax = min(vals), max(vals)
  if vmax <= vmin:
    return [round((lo + hi) / 2, 2)] * len(vals)
  return [round(lo + (x - vmin) / (vmax - vmin) * (hi - lo), 2) for x in vals]


def build_generic_public_charts(
  items: list[dict[str, Any]],
  *,
  category: str,
) -> dict[str, Any]:
  """분석 스냅샷용 line(12)·bar(5)·donut(4)·accents."""
  accents_map = {
    "health": {"line": "#9AF7D0", "bar": "#6AE4FF"},
    "traffic": {"line": "#FFD36A", "bar": "#FF7AD9"},
    "tour": {"line": "#FFD36A", "bar": "#FF7AD9"},
    "env": {"line": "#7CFCA0", "bar": "#5BC0EB"},
  }
  accents = accents_map.get(category, {"line": "#6AE4FF", "bar": "#B79BFF"})

  empty_line = [12, 14, 13, 15, 16, 18, 17, 19, 20, 21, 22, 24]
  empty_bar = [10.0, 14.0, 12.0, 16.0, 13.0]
  empty_donut = [35.0, 28.0, 22.0, 15.0]

  if len(items) < 1:
    return {"line": empty_line, "bar": empty_bar, "donut": empty_donut, "accents": accents}

  nums = _pick_numeric_columns(items)
  if nums:
    key0 = nums[0]
    n = len(items)
    bucket_means: list[float] = []
    for i in range(12):
      lo = int(n * i / 12)
      hi = int(n * (i + 1) / 12) if i < 11 else n
      chunk = items[lo:hi] if hi > lo else []
      vs = [_to_float(it.get(key0)) for it in chunk]
      vs = [v for v in vs if v is not None]
      bucket_means.append(float(mean(vs)) if vs else 0.0)
    line = _scale(bucket_means)

    bar_avgs: list[tuple[str, float]] = []
    for k in nums[:5]:
      vs = [_to_float(it.get(k)) for it in items]
      vs = [v for v in vs if v is not None]
      if vs:
        bar_avgs.append((k[:12], float(mean(vs))))
    bar_avgs.sort(key=lambda x: -x[1])
    if not bar_avgs:
      bar = empty_bar
    else:
      mx = bar_avgs[0][1] or 1.0
      bar = [max(6.0, round(28.0 * (v / mx), 2)) for _, v in bar_avgs[:5]]
      while len(bar) < 5:
        bar.append(8.0)
  else:
    n = max(1, len(items))
    line = _scale([float((i + 1) / 12 * n) for i in range(12)])
    cnt = Counter()
    for it in items:
      for k in list(it.keys())[:4]:
        v = it.get(k)
        if v is not None and str(v).strip():
          cnt[str(k)[:16]] += 1
    top = cnt.most_common(5)
    if not top:
      bar = empty_bar
    else:
      mx = top[0][1] or 1
      bar = [max(6.0, round(28.0 * c / mx, 2)) for _, c in top]
      while len(bar) < 5:
        bar.append(8.0)

  cat_key = None
  for cand in ("ctgry_nm", "guNm", "sidoNm", "signguNm", "lineNm", "routeNm", "stationNm", "prdtNm"):
    if any(cand in it for it in items[:30]):
      cat_key = cand
      break
  if cat_key:
    vc = Counter(str(it.get(cat_key, "")).strip()[:24] for it in items if it.get(cat_key))
    top4 = [(k, c) for k, c in vc.most_common(4) if k]
    if len(top4) >= 2:
      tsum = sum(c for _, c in top4) or 1
      donut = [max(8.0, round(100.0 * c / tsum, 2)) for _, c in top4]
      while len(donut) < 4:
        donut.append(12.0)
    else:
      donut = empty_donut
  else:
    donut = empty_donut

  return {"line": line, "bar": bar[:5], "donut": donut[:4], "accents": accents}


def build_summary_and_distribution(items: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
  nums = _pick_numeric_columns(items, min_frac=0.15)
  summary: dict[str, Any] = {"row_count": len(items), "numeric_columns": nums}
  for k in nums[:3]:
    vs = [v for v in (_to_float(it.get(k)) for it in items) if v is not None]
    if vs:
      summary[k] = {"min": round(min(vs), 4), "max": round(max(vs), 4), "avg": round(mean(vs), 4), "n": len(vs)}
  dist: dict[str, Any] = {"bins": [], "note": "첫 번째 수치 컬럼 기준 균등 구간(있을 때)"}
  if nums:
    k0 = nums[0]
    vs = sorted(v for v in (_to_float(it.get(k0)) for it in items) if v is not None)
    if len(vs) >= 2:
      lo, hi = vs[0], vs[-1]
      if hi > lo:
        for i in range(5):
          a = lo + (hi - lo) * i / 5
          b = lo + (hi - lo) * (i + 1) / 5
          if i < 4:
            c = sum(1 for x in vs if a <= x < b)
          else:
            c = sum(1 for x in vs if x >= a)
          dist["bins"].append({"lo": round(a, 4), "hi": round(b, 4), "count": c})
  return summary, dist
