from __future__ import annotations

from typing import List

from backend.app.models.builder import BuilderSuggestion
from backend.app.repositories.builder_store import BuilderStore


class BuilderService:
  def __init__(self, store: BuilderStore):
    self._store = store

  def suggestions(self, keyword: str):
    kw = (keyword or "").strip()
    if not kw:
      return {"keyword": "", "suggestions": []}

    # 데모 규칙: 특정 키워드는 더 풍부한 추천 제공
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

    # 중복 제거
    seen = set()
    out: List[BuilderSuggestion] = []
    for s in base:
      if s.id in seen:
        continue
      seen.add(s.id)
      out.append(s)

    return {"keyword": kw, "suggestions": [s.model_dump() for s in out]}

  def metric(self, keyword: str, metric: str):
    kw = (keyword or "").strip()
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

  def save(self, user: dict, title: str, keyword: str, metric: str, metric_label: str):
    item = self._store.save(
      user_id=int(user["id"]),
      title=title,
      keyword=keyword,
      metric=metric,
      metric_label=metric_label,
    )
    return item

  def list_saved(self, user: dict):
    items = self._store.list_saved(int(user["id"]))
    return {"user": user["email"], "items": items}

  def chat(self, user: dict, keyword: str, question: str):
    # 데모 응답: 실제 구현 시 LLM + metric 매핑/쿼리 생성으로 교체
    kw = (keyword or "").strip()
    q = (question or "").strip()
    if not kw:
      answer = "키워드를 먼저 입력해 주세요. (예: 게임)"
    else:
      name = user.get("name") or user.get("email") or "사용자"
      answer = f"{name}님의 질문을 받았습니다. '{kw}' 관련 '{q}' 요청은 현재 데모 응답으로 제공되며, 추천 지표를 선택하면 바로 그래프를 확인할 수 있습니다."
    return {"answer": answer}

