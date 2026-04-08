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
        detail="Keyword catalog is empty. Ask an admin to insert rows into builder_keyword_catalog.",
      )
    if cat not in allowed:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unknown classification. Pick one from GET /api/builder/classifications.",
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
    rich = "game" in lowered

    base: List[BuilderSuggestion] = [
      BuilderSuggestion(id="user_count", label="Active users", description="Trend of active users or interest"),
      BuilderSuggestion(id="price_avg", label="Average price", description="Average price over time"),
    ]
    if rich:
      base.extend(
        [
          BuilderSuggestion(id="revenue", label="Revenue (est.)", description="Revenue or spend trend"),
          BuilderSuggestion(id="sentiment", label="Sentiment", description="Positive / negative share (demo)"),
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
      kw = "general"
    m = (metric or "").strip()
    metric_label = m
    if m == "user_count":
      metric_label = "Active users"
    elif m == "price_avg":
      metric_label = "Average price"
    elif m == "revenue":
      metric_label = "Revenue (est.)"
    elif m == "sentiment":
      metric_label = "Sentiment"

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
      answer = "Enter a keyword first (e.g. game)."
    else:
      name = user.get("nickname") or user.get("email") or "User"
      answer = (
        f"{name}, received your question about '{kw}' — '{q}'. "
        "This is a demo reply; pick a metric below to see a chart."
      )
    return {"answer": answer}
