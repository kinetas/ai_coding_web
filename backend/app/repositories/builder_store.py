from __future__ import annotations

import random
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.db_models import SavedBuilderAnalysis, User


class BuilderStore:
  def __init__(self, session_factory: sessionmaker):
    self._session_factory = session_factory

  def list_saved(self, user_id: int) -> List[dict]:
    with self._session_factory() as db:
      rows = db.scalars(
        select(SavedBuilderAnalysis)
        .where(SavedBuilderAnalysis.user_id == user_id)
        .order_by(SavedBuilderAnalysis.created_at.desc())
      ).all()
      return [self._to_item(row, row.user) for row in rows]

  def save(self, user_id: int, title: str, keyword: str, metric: str, metric_label: str) -> dict:
    with self._session_factory() as db:
      row = SavedBuilderAnalysis(
        user_id=user_id,
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
      "title": row.title,
      "keyword": row.keyword,
      "metric": row.metric,
      "metric_label": row.metric_label,
      "saved_at": row.created_at.isoformat() if row.created_at else "",
    }

