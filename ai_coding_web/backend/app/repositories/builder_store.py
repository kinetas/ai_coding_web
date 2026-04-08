from __future__ import annotations

import random
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.db_models import BuilderKeywordCatalog, SavedBuilderAnalysis, User

_CATALOG_SEED: list[tuple[str, str, str]] = [
  ("농산물 시세", "price_avg", "가격 평균"),
  ("농산물 시세", "user_count", "유통·관심도"),
  ("의료", "price_avg", "의료비 추세"),
  ("의료", "user_count", "이용 건수"),
  ("교통", "price_avg", "통행·요금 지표"),
  ("교통", "user_count", "이용량"),
  ("관광", "revenue", "소비·매출 추정"),
  ("관광", "user_count", "방문 관심도"),
  ("환경", "sentiment", "이슈 긍·부정"),
  ("환경", "price_avg", "지표 평균"),
]


class BuilderStore:
  def __init__(self, session_factory: sessionmaker):
    self._session_factory = session_factory

  def seed_catalog_if_empty(self) -> None:
    with self._session_factory() as db:
      exists = db.scalar(select(BuilderKeywordCatalog.id).limit(1))
      if exists:
        return
      for classification, keyword_key, keyword_value in _CATALOG_SEED:
        db.add(
          BuilderKeywordCatalog(
            classification=classification,
            keyword_key=keyword_key,
            keyword_value=keyword_value,
          )
        )
      db.commit()

  def list_distinct_classifications(self) -> List[str]:
    with self._session_factory() as db:
      rows = db.scalars(
        select(BuilderKeywordCatalog.classification).distinct().order_by(BuilderKeywordCatalog.classification)
      ).all()
      return [str(r) for r in rows if r]

  def list_catalog(self, classification: str | None = None) -> List[dict]:
    with self._session_factory() as db:
      q = select(BuilderKeywordCatalog).order_by(
        BuilderKeywordCatalog.classification, BuilderKeywordCatalog.keyword_key
      )
      cat = (classification or "").strip()
      if cat:
        q = q.where(BuilderKeywordCatalog.classification == cat)
      rows = db.scalars(q).all()
      return [
        {
          "id": row.id,
          "classification": row.classification,
          "keyword_key": row.keyword_key,
          "keyword_value": row.keyword_value,
        }
        for row in rows
      ]

  def list_saved(self, user_id: int, category_label: str | None = None) -> List[dict]:
    with self._session_factory() as db:
      q = select(SavedBuilderAnalysis).where(SavedBuilderAnalysis.user_id == user_id)
      cat = (category_label or "").strip()
      if cat:
        q = q.where(SavedBuilderAnalysis.category_label == cat)
      q = q.order_by(SavedBuilderAnalysis.created_at.desc())
      rows = db.scalars(q).all()
      return [self._to_item(row, row.user) for row in rows]

  def save(
    self,
    user_id: int,
    title: str,
    keyword: str,
    metric: str,
    metric_label: str,
    category_label: str,
  ) -> dict:
    with self._session_factory() as db:
      row = SavedBuilderAnalysis(
        user_id=user_id,
        category_label=category_label,
        title=title,
        keyword=keyword,
        metric=metric,
        metric_label=metric_label,
      )
      db.add(row)
      db.commit()
      db.refresh(row)
      user = db.get(User, user_id)
      return self._to_item(row, user)

  def build_metric(self, keyword: str, metric: str) -> dict:
    seed = abs(hash((keyword or "", metric or ""))) % 10_000
    rnd = random.Random(seed)

    line = [rnd.randint(14, 78) for _ in range(12)]
    bar = [rnd.randint(6, 28) for _ in range(5)]

    accents = {"line": "#6AE4FF", "bar": "#B79BFF"}
    if metric == "user_count":
      accents = {"line": "#9AF7D0", "bar": "#6AE4FF"}
    elif metric == "price_avg":
      accents = {"line": "#6AE4FF", "bar": "#B79BFF"}
    elif metric == "revenue":
      accents = {"line": "#FFD36A", "bar": "#FF7AD9"}

    return {"line": line, "bar": bar, "accents": accents}

  @staticmethod
  def _to_item(row: SavedBuilderAnalysis, user: User | None) -> dict:
    return {
      "id": str(row.id),
      "user": user.email if user else "",
      "category_label": row.category_label or "",
      "title": row.title,
      "keyword": row.keyword,
      "metric": row.metric,
      "metric_label": row.metric_label,
      "saved_at": row.created_at.isoformat() if row.created_at else "",
    }

