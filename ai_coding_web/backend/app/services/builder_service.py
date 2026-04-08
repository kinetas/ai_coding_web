from __future__ import annotations

from typing import List

from fastapi import HTTPException, status

from backend.app.models.builder import BuilderSuggestion
from backend.app.repositories.builder_store import BuilderStore


class BuilderService:
  def __init__(self, store: BuilderStore):
    self._store = store

  @staticmethod
  def _normalize_category(label: str) -> str:
    return (label or "").strip()

  def _require_valid_category(self, category_label: str) -> str:
    cat = self._normalize_category(category_label)
    allowed = self._store.list_distinct_classifications()
    if not allowed:
      raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="키워드 분류 목록이 아직 준비되지 않았습니다. 관리자에게 문의하세요.",
      )
    if cat not in allowed:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="등록되지 않은 분류입니다. 목록에 있는 분류만 선택할 수 있습니다.",
      )
    return cat

  def list_classifications(self) -> dict:
    return {"classifications": self._store.list_distinct_classifications()}

  def list_catalog_entries(self, classification: str | None) -> dict:
    raw = self._normalize_category(classification or "")
    if raw:
      self._require_valid_category(classification or "")
    items = self._store.list_catalog(classification=raw if raw else None)
    return {"items": items}

  def suggestions(self, keyword: str, category_label: str | None = None):
    if category_label is not None and self._normalize_category(category_label):
      self._require_valid_category(category_label)

    kw = (keyword or "").strip()
    cat_raw = self._normalize_category(category_label or "")

    if cat_raw:
      cat = self._require_valid_category(category_label or "")
      rows = self._store.list_catalog(classification=cat)
      out: List[BuilderSuggestion] = []
      for r in rows:
        if kw:
          blob = f"{r['keyword_value']} {r['keyword_key']}"
          if kw.lower() not in blob.lower():
            continue
        label = r["keyword_value"]
        if len(label) > 40:
          label = label[:37] + "..."
        out.append(
          BuilderSuggestion(
            id=r["keyword_key"],
            label=label,
            description="",
          )
        )
      return {
        "keyword": kw,
        "category_label": cat,
        "suggestions": [s.model_dump() for s in out],
      }

    if not kw:
      return {"keyword": "", "category_label": "", "suggestions": []}

    lowered = kw.lower()
    rich = ("게임" in kw) or ("game" in lowered)

    base: List[BuilderSuggestion] = [
      BuilderSuggestion(id="user_count", label="유저 수", description="기간별 유저 수(또는 관심도) 추이"),
      BuilderSuggestion(id="price_avg", label="가격 평균", description="기간별 평균 가격 추이"),
    ]
    if rich:
      base.extend(
        [
          BuilderSuggestion(id="revenue", label="매출(추정)", description="기간별 매출(또는 소비) 추이"),
          BuilderSuggestion(id="sentiment", label="긍/부정", description="키워드 관련 긍·부정 비중(예시)"),
        ]
      )

    seen = set()
    out: List[BuilderSuggestion] = []
    for s in base:
      if s.id in seen:
        continue
      seen.add(s.id)
      out.append(s)

    return {
      "keyword": kw,
      "category_label": "",
      "suggestions": [s.model_dump() for s in out],
    }

  def metric(self, keyword: str, metric: str):
    kw = (keyword or "").strip()
    if not kw:
      kw = "일반"
    m = (metric or "").strip()
    metric_label = m
    if m == "user_count":
      metric_label = "유저 수"
    elif m == "price_avg":
      metric_label = "가격 평균"
    elif m == "revenue":
      metric_label = "매출(추정)"
    elif m == "sentiment":
      metric_label = "긍/부정"

    data = self._store.build_metric(kw, m)
    return {
      "keyword": kw,
      "metric": m,
      "metric_label": metric_label,
      "line": data["line"],
      "bar": data["bar"],
      "accents": data.get("accents") or {},
    }

  def save(self, user: dict, title: str, keyword: str, metric: str, metric_label: str, category_label: str):
    cat = self._require_valid_category(category_label)
    item = self._store.save(
      user_id=int(user["id"]),
      title=title,
      keyword=keyword,
      metric=metric,
      metric_label=metric_label,
      category_label=cat,
    )
    return item

  def list_saved(self, user: dict, category_label: str | None = None):
    cat: str | None = None
    if category_label is not None:
      raw = self._normalize_category(category_label)
      if raw:
        cat = self._require_valid_category(raw)
    items = self._store.list_saved(int(user["id"]), category_label=cat)
    return {"user": user["email"], "items": items}

  def chat(self, user: dict, keyword: str, question: str):
    kw = (keyword or "").strip()
    q = (question or "").strip()
    if not kw:
      answer = "키워드를 먼저 입력해 주세요. (예: 게임)"
    else:
      name = user.get("nickname") or user.get("email") or "사용자"
      answer = f"{name}님의 질문을 받았습니다. '{kw}' 관련 '{q}' 요청은 현재 데모 응답으로 제공되며, 추천 지표를 선택하면 바로 그래프를 확인할 수 있습니다."
    return {"answer": answer}
