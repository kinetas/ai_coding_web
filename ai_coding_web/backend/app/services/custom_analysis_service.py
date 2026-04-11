"""맞춤 분석 서비스 — 카테고리 선택 → 하위 카테고리 → 연도 → 분석방식 → 차트 데이터."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.db_models import AgriPriceHistory, AgriPriceRaw, PublicCategoryAnalytics


CATEGORY_LABELS: dict[str, str] = {
    "agri": "농산물",
    "health": "보건",
    "traffic": "교통",
    "tour": "관광",
    "env": "환경",
}

PUBLIC_CATEGORIES = {"health", "traffic", "tour", "env"}

TOP_CATEGORIES = [
    {"code": "agri", "label": "농산물"},
    {"code": "health", "label": "보건"},
    {"code": "traffic", "label": "교통"},
    {"code": "tour", "label": "관광"},
    {"code": "env", "label": "환경"},
]

ANALYSIS_METHODS = [
    {"code": "trend", "label": "추이 분석", "chart_type": "line", "desc": "월별 평균 변화"},
    {"code": "compare", "label": "항목 비교", "chart_type": "bar", "desc": "품목/항목 간 비교"},
    {"code": "distribution", "label": "비중 분석", "chart_type": "donut", "desc": "구성 비율"},
    {"code": "movers", "label": "등락 분석", "chart_type": "bar", "desc": "전주 대비 변동"},
]


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _get_price(p: dict[str, Any]) -> float | None:
    unit = str(p.get("unit") or "").strip()
    if unit in {"kg", "g"}:
        v = p.get("exmn_dd_cnvs_avg_prc") or p.get("조사일kg환산평균가격") or p.get("exmn_dd_avg_prc")
    else:
        v = p.get("exmn_dd_avg_prc") or p.get("조사일평균가격")
    return _to_float(v)


def _parse_payload(p: Any) -> dict[str, Any]:
    if isinstance(p, dict):
        return p
    if isinstance(p, str):
        try:
            return json.loads(p)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


class CustomAnalysisService:
    def __init__(self, session_factory=None):
        self._sf = session_factory or SessionLocal

    # ── 메타 ────────────────────────────────────────────────────────────────

    def get_meta(self) -> dict:
        return {"categories": TOP_CATEGORIES, "methods": ANALYSIS_METHODS}

    # ── 서브카테고리 ─────────────────────────────────────────────────────────

    def get_subcategories(self, category: str) -> dict:
        if category == "agri":
            return self._agri_subcategories()
        if category in PUBLIC_CATEGORIES:
            return self._public_subcategories(category)
        return {"category": category, "subcategories": []}

    def _agri_subcategories(self) -> dict:
        with self._sf() as db:
            row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
        if not row:
            return {"category": "agri", "subcategories": []}
        items: list[dict] = row.items or []
        seen: set[str] = set()
        subs: list[dict] = []
        for it in items:
            ctgry = str(it.get("ctgry_nm") or "").strip()
            if ctgry and ctgry not in seen:
                seen.add(ctgry)
                subs.append({"code": ctgry, "label": ctgry})
        return {"category": "agri", "subcategories": sorted(subs, key=lambda x: x["label"])}

    def _public_subcategories(self, category_code: str) -> dict:
        with self._sf() as db:
            row = db.scalar(
                select(PublicCategoryAnalytics)
                .where(PublicCategoryAnalytics.category_code == category_code)
                .where(PublicCategoryAnalytics.slug == "latest")
            )
        if not row:
            return {"category": category_code, "subcategories": [{"code": "all", "label": "전체"}]}
        dist = row.distribution or {}
        subs: list[dict] = []
        for k in dist.keys():
            if k not in ("labels", "series", "note") and isinstance(dist[k], (int, float)):
                subs.append({"code": k, "label": k})
        if not subs:
            subs = [{"code": "all", "label": "전체"}]
        return {"category": category_code, "subcategories": subs}

    # ── 품목 ─────────────────────────────────────────────────────────────────

    def get_items(self, category: str, subcategory: str) -> dict:
        if category == "agri":
            return self._agri_items(subcategory)
        return {"category": category, "subcategory": subcategory, "items": []}

    def _agri_items(self, subcategory: str) -> dict:
        with self._sf() as db:
            row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
        if not row:
            return {"subcategory": subcategory, "items": []}
        raw_items: list[dict] = row.items or []
        seen: set[str] = set()
        items: list[dict] = []
        for it in raw_items:
            ctgry = str(it.get("ctgry_nm") or "").strip()
            if subcategory != "all" and ctgry != subcategory:
                continue
            nm = str(it.get("item_nm") or "").strip()
            if nm and nm not in seen:
                seen.add(nm)
                items.append({"code": nm, "label": nm})
        return {"subcategory": subcategory, "items": sorted(items, key=lambda x: x["label"])}

    # ── 차트 데이터 ──────────────────────────────────────────────────────────

    def get_data(self, category: str, subcategory: str, item: str, year_from: int, year_to: int, method: str) -> dict:
        if category == "agri":
            return self._agri_data(subcategory, item, year_from, year_to, method)
        if category in PUBLIC_CATEGORIES:
            return self._public_data(category, subcategory, year_from, year_to, method)
        return self._empty(category, subcategory, year_from, method, "line", "알 수 없는 카테고리")

    # ── 농산물 ───────────────────────────────────────────────────────────────

    def _agri_data(self, subcategory: str, item: str, year_from: int, year_to: int, method: str) -> dict:
        if method == "movers":
            return self._agri_movers(subcategory, item)

        with self._sf() as db:
            rows = db.scalars(
                select(AgriPriceHistory)
                .where(AgriPriceHistory.exmn_ymd >= f"{year_from}0101")
                .where(AgriPriceHistory.exmn_ymd <= f"{year_to}1231")
                .order_by(AgriPriceHistory.exmn_ymd.asc())
            ).all()

        filtered: list[tuple[AgriPriceHistory, dict]] = []
        for r in rows:
            p = _parse_payload(r.payload)
            ctgry = str(p.get("ctgry_nm") or "").strip()
            nm = str(p.get("item_nm") or p.get("품목명") or "").strip()
            if subcategory != "all" and ctgry != subcategory:
                continue
            if item != "all" and nm != item:
                continue
            filtered.append((r, p))

        period_label = f"{year_from}" if year_from == year_to else f"{year_from}~{year_to}"
        sub_label = item if item != "all" else subcategory

        if not filtered:
            return self._empty(
                "agri", subcategory, year_from, method, "line",
                f"{period_label}년 {sub_label} 데이터가 없습니다. ETL을 실행해 데이터를 수집하세요."
            )

        if method == "trend":
            return self._agri_trend(sub_label, year_from, year_to, filtered)
        if method == "compare":
            return self._agri_compare(sub_label, year_from, year_to, filtered)
        if method == "distribution":
            return self._agri_distribution(sub_label, year_from, year_to, filtered)
        return self._empty("agri", subcategory, year_from, method, "bar", "지원하지 않는 분석 방식")

    def _agri_trend(self, label: str, year_from: int, year_to: int, filtered: list) -> dict:
        multi_year = year_from != year_to
        bucket: dict[str, list[float]] = defaultdict(list)
        months_kr = ["1월", "2월", "3월", "4월", "5월", "6월",
                     "7월", "8월", "9월", "10월", "11월", "12월"]

        for r, p in filtered:
            ymd = r.exmn_ymd or ""
            if len(ymd) == 8:
                year_str = ymd[:4]
                month = ymd[4:6]
                key = f"{year_str}-{month}" if multi_year else month
                price = _get_price(p)
                if price and price > 0:
                    bucket[key].append(price)

        sorted_keys = sorted(bucket.keys())
        labels: list[str] = []
        series: list[float] = []
        for k in sorted_keys:
            if multi_year:
                y, m = k.split("-")
                mi = int(m) - 1
                labels.append(f"{y}/{months_kr[mi] if 0 <= mi < 12 else m + '월'}")
            else:
                mi = int(k) - 1
                labels.append(months_kr[mi] if 0 <= mi < 12 else f"{k}월")
            vals = bucket[k]
            series.append(round(sum(vals) / len(vals), 1))

        period_label = f"{year_from}" if year_from == year_to else f"{year_from}~{year_to}"
        return {
            "category": "agri", "subcategory": label, "year": year_from, "method": "trend",
            "chart_type": "line",
            "labels": labels, "series": series,
            "title": f"{label} 월별 평균 가격 추이 ({period_label})",
            "unit": "원/kg환산",
        }

    def _agri_compare(self, label: str, year_from: int, year_to: int, filtered: list) -> dict:
        item_prices: dict[str, list[float]] = defaultdict(list)
        for r, p in filtered:
            nm = str(p.get("item_nm") or p.get("품목명") or "").strip()
            price = _get_price(p)
            if nm and price and price > 0:
                item_prices[nm].append(price)

        items_sorted = sorted(
            [(nm, round(sum(ps) / len(ps), 1)) for nm, ps in item_prices.items()],
            key=lambda x: -x[1],
        )[:15]

        period_label = f"{year_from}" if year_from == year_to else f"{year_from}~{year_to}"
        return {
            "category": "agri", "subcategory": label, "year": year_from, "method": "compare",
            "chart_type": "bar",
            "labels": [x[0] for x in items_sorted],
            "series": [x[1] for x in items_sorted],
            "title": f"{label} 품목별 평균 가격 비교 ({period_label})",
            "unit": "원/kg환산",
        }

    def _agri_distribution(self, label: str, year_from: int, year_to: int, filtered: list) -> dict:
        item_prices: dict[str, list[float]] = defaultdict(list)
        for r, p in filtered:
            nm = str(p.get("item_nm") or p.get("품목명") or "").strip()
            price = _get_price(p)
            if nm and price and price > 0:
                item_prices[nm].append(price)

        items_sorted = sorted(
            [(nm, round(sum(ps) / len(ps), 1)) for nm, ps in item_prices.items()],
            key=lambda x: -x[1],
        )[:8]

        period_label = f"{year_from}" if year_from == year_to else f"{year_from}~{year_to}"
        return {
            "category": "agri", "subcategory": label, "year": year_from, "method": "distribution",
            "chart_type": "donut",
            "labels": [x[0] for x in items_sorted],
            "series": [x[1] for x in items_sorted],
            "title": f"{label} 가격 비중 ({period_label})",
            "unit": "원/kg환산",
        }

    def _agri_movers(self, subcategory: str, item: str = "all") -> dict:
        with self._sf() as db:
            row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))
        if not row:
            return self._empty("agri", subcategory, 0, "movers", "bar", "원본 데이터가 없습니다.")

        items: list[dict] = row.items or []
        survey_date = str(items[0].get("exmn_ymd") or "") if items else ""

        movers: list[tuple[str, float]] = []
        for it in items:
            ctgry = str(it.get("ctgry_nm") or "").strip()
            if subcategory != "all" and ctgry != subcategory:
                continue
            nm = str(it.get("item_nm") or "").strip()
            if item != "all" and nm != item:
                continue
            unit = str(it.get("unit") or "").strip()
            if unit in {"kg", "g"}:
                cur = _to_float(it.get("exmn_dd_cnvs_avg_prc") or it.get("조사일kg환산평균가격"))
                prev = _to_float(it.get("ww1_bfr_cnvs_avg_prc") or it.get("1주일전kg환산평균가격"))
            else:
                cur = _to_float(it.get("exmn_dd_avg_prc") or it.get("조사일평균가격"))
                prev = _to_float(it.get("ww1_bfr_avg_prc") or it.get("1주일전평균가격"))

            if cur is not None and prev is not None and prev > 0 and nm:
                wow_pct = round((cur - prev) / prev * 100, 1)
                movers.append((nm, wow_pct))

        movers.sort(key=lambda x: -abs(x[1]))
        top = movers[:14]

        note = f"최신 조사일 기준 ({survey_date})" if survey_date else "최신 데이터 기준"
        return {
            "category": "agri", "subcategory": subcategory, "year": 0, "method": "movers",
            "chart_type": "bar",
            "labels": [x[0] for x in top],
            "series": [x[1] for x in top],
            "title": f"{subcategory} 전주 대비 등락률",
            "unit": "%",
            "note": note,
        }

    # ── 공공 카테고리 ─────────────────────────────────────────────────────────

    def _public_data(self, category_code: str, subcategory: str, year_from: int, year_to: int, method: str) -> dict:
        label = CATEGORY_LABELS.get(category_code, category_code)
        with self._sf() as db:
            row = db.scalar(
                select(PublicCategoryAnalytics)
                .where(PublicCategoryAnalytics.category_code == category_code)
                .where(PublicCategoryAnalytics.slug == "latest")
            )
        if not row:
            return self._empty(
                category_code, subcategory, year_from, method, "line",
                f"{label} 데이터가 없습니다. ETL을 실행해 데이터를 수집하세요."
            )

        bundle = row.chart_bundle or {}
        dist = row.distribution or {}
        summary = row.summary or {}
        updated_at = row.updated_at.isoformat() if row.updated_at else ""
        note = f"갱신: {updated_at[:10] if updated_at else '알 수 없음'} (최신 데이터 기준)"

        if method == "trend":
            line = bundle.get("line") or []
            x_labels = bundle.get("labels") or bundle.get("x_labels") or [str(i + 1) for i in range(len(line))]
            return {
                "category": category_code, "subcategory": subcategory, "year": year_from, "method": "trend",
                "chart_type": "line",
                "labels": x_labels, "series": line,
                "title": f"{label} 추이 (최신 데이터)",
                "note": note,
            }

        if method == "compare":
            bar = bundle.get("bar") or []
            x_labels = bundle.get("labels") or [str(i + 1) for i in range(len(bar))]
            return {
                "category": category_code, "subcategory": subcategory, "year": year_from, "method": "compare",
                "chart_type": "bar",
                "labels": x_labels, "series": bar,
                "title": f"{label} 항목 비교 (최신 데이터)",
                "note": note,
            }

        if method == "distribution":
            # dist의 숫자 값들을 도넛으로
            numeric_items = [(k, v) for k, v in dist.items() if isinstance(v, (int, float))]
            if numeric_items:
                numeric_items.sort(key=lambda x: -x[1])
                top8 = numeric_items[:8]
                return {
                    "category": category_code, "subcategory": subcategory, "year": year_from, "method": "distribution",
                    "chart_type": "donut",
                    "labels": [x[0] for x in top8],
                    "series": [x[1] for x in top8],
                    "title": f"{label} 비중 분포 (최신 데이터)",
                    "note": note,
                }
            donut = bundle.get("donut") or []
            return {
                "category": category_code, "subcategory": subcategory, "year": year_from, "method": "distribution",
                "chart_type": "donut",
                "labels": [], "series": donut,
                "title": f"{label} 비중 분포 (최신 데이터)",
                "note": note,
            }

        if method == "movers":
            # summary의 숫자 항목을 바차트로
            numeric_items = [(k, v) for k, v in summary.items() if isinstance(v, (int, float))]
            numeric_items.sort(key=lambda x: -x[1])
            top12 = numeric_items[:12]
            return {
                "category": category_code, "subcategory": subcategory, "year": year_from, "method": "movers",
                "chart_type": "bar",
                "labels": [x[0] for x in top12],
                "series": [x[1] for x in top12],
                "title": f"{label} 주요 수치 (최신 데이터)",
                "note": note,
            }

        return self._empty(category_code, subcategory, year_from, method, "line", "지원하지 않는 분석 방식")

    # ── 공통 헬퍼 ────────────────────────────────────────────────────────────

    @staticmethod
    def _empty(category: str, subcategory: str, year: int, method: str, chart_type: str, note: str) -> dict:
        return {
            "category": category, "subcategory": subcategory, "year": year, "method": method,
            "chart_type": chart_type,
            "labels": [], "series": [],
            "title": f"{CATEGORY_LABELS.get(category, category)} 분석",
            "note": note,
        }
