from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.db_models import AgriPriceRaw, PriceAlert


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


class AlertService:
    def __init__(self, session_factory=None):
        self._sf = session_factory or SessionLocal

    # ── 목록 ──────────────────────────────────────────────────────────────────

    def list_alerts(self, user: dict) -> dict:
        user_id = user["id"]
        with self._sf() as db:
            rows = db.scalars(
                select(PriceAlert)
                .where(PriceAlert.user_id == user_id)
                .where(PriceAlert.active == True)
                .order_by(PriceAlert.created_at.desc())
            ).all()
        return {"items": [self._row_to_dict(r) for r in rows]}

    # ── 생성 ──────────────────────────────────────────────────────────────────

    def create_alert(self, user: dict, name: str, item_name: str, condition: str, threshold: float) -> dict:
        user_id = user["id"]
        with self._sf() as db:
            row = PriceAlert(
                user_id=user_id,
                name=name,
                item_name=item_name,
                condition=condition,
                threshold=threshold,
                active=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return self._row_to_dict(row)

    # ── 삭제 (비활성화) ───────────────────────────────────────────────────────

    def delete_alert(self, user: dict, alert_id: int) -> dict:
        user_id = user["id"]
        with self._sf() as db:
            row = db.scalar(
                select(PriceAlert)
                .where(PriceAlert.id == alert_id)
                .where(PriceAlert.user_id == user_id)
            )
            if not row:
                return {"ok": False, "error": "알림을 찾을 수 없습니다."}
            db.delete(row)
            db.commit()
        return {"ok": True}

    # ── 체크 ──────────────────────────────────────────────────────────────────

    def check_alerts(self, user: dict) -> dict:
        user_id = user["id"]
        with self._sf() as db:
            alerts = db.scalars(
                select(PriceAlert)
                .where(PriceAlert.user_id == user_id)
                .where(PriceAlert.active == True)
                .order_by(PriceAlert.created_at.desc())
            ).all()
            raw_row = db.scalar(select(AgriPriceRaw).where(AgriPriceRaw.slug == "latest"))

        # 최신 가격 맵 구성 (품목명 → 가격)
        price_map: dict[str, float] = {}
        survey_date = ""
        if raw_row:
            items: list[dict] = raw_row.items or []
            if items:
                survey_date = str(items[0].get("exmn_ymd") or "")
            for it in items:
                nm = str(it.get("item_nm") or "").strip()
                if not nm:
                    continue
                price = _get_price(it)
                if price and price > 0:
                    # 같은 품목이 여러 등급으로 존재할 수 있으므로 평균
                    if nm in price_map:
                        price_map[nm] = (price_map[nm] + price) / 2
                    else:
                        price_map[nm] = price

        result = []
        for row in alerts:
            current = price_map.get(row.item_name)
            if current is None:
                triggered = None
            elif row.condition == "above":
                triggered = current > row.threshold
            else:
                triggered = current < row.threshold
            d = self._row_to_dict(row)
            d["current_price"] = round(current, 1) if current is not None else None
            d["triggered"] = triggered
            result.append(d)

        return {"items": result, "survey_date": survey_date}

    # ── 헬퍼 ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: PriceAlert) -> dict:
        return {
            "id": row.id,
            "name": row.name,
            "item_name": row.item_name,
            "condition": row.condition,
            "threshold": row.threshold,
            "active": row.active,
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "current_price": None,
            "triggered": None,
        }
