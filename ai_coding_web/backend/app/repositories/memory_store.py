from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from backend.app.db_models import AnalysisSnapshot, EtlRun, WordcloudTerm
from backend.app.models.analysis import Accents
from backend.app.models.types import Category, Page, Region
from backend.app.models.wordcloud import Word


class ContentStore:
  def __init__(self, session_factory: sessionmaker):
    self._session_factory = session_factory

  def get_wordcloud(self, category: Category, region: Region) -> List[Dict[str, float]]:
    with self._session_factory() as db:
      if category == "all":
        rows = db.scalars(select(WordcloudTerm).where(WordcloudTerm.region == region)).all()
        # 카테고리별로 최대 weight 기준 정규화 후 최댓값으로 병합
        # (합산 시 범용 단어가 여러 카테고리에 걸쳐 과다 노출되는 문제 방지)
        from collections import defaultdict
        cat_groups: Dict[str, List] = defaultdict(list)
        for row in rows:
          cat_groups[row.category].append((row.text, float(row.weight)))
        merged: Dict[str, float] = {}
        for cat_words in cat_groups.values():
          if not cat_words:
            continue
          max_w = max(w for _, w in cat_words) or 1.0
          for text, weight in cat_words:
            norm_w = weight / max_w * 100.0
            merged[text] = max(merged.get(text, 0.0), norm_w)
        words = [{"text": k, "weight": round(v, 2)} for k, v in merged.items()]
        words.sort(key=lambda item: float(item["weight"]), reverse=True)
        return words[:28]

      rows = db.scalars(
        select(WordcloudTerm)
        .where(WordcloudTerm.category == category)
        .where(WordcloudTerm.region == region)
        .order_by(WordcloudTerm.weight.desc())
      ).all()
      return [{"text": row.text, "weight": float(row.weight)} for row in rows[:28]]

  def get_wordcloud_updated_at(self, category: Category, region: Region) -> Optional[str]:
    """해당 카테고리·지역 워드클라우드의 DB 마지막 갱신 시각(ISO 8601)을 반환합니다."""
    with self._session_factory() as db:
      if category == "all":
        row = db.scalar(
          select(WordcloudTerm)
          .where(WordcloudTerm.region == region)
          .order_by(WordcloudTerm.updated_at.desc())
          .limit(1)
        )
      else:
        row = db.scalar(
          select(WordcloudTerm)
          .where(WordcloudTerm.category == category)
          .where(WordcloudTerm.region == region)
          .order_by(WordcloudTerm.updated_at.desc())
          .limit(1)
        )
      if row is None or row.updated_at is None:
        return None
      dt = row.updated_at
      if dt.tzinfo is None:
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)
      return dt.isoformat()

  def set_wordcloud(self, category: Category, region: Region, words: List[Word], min_words: int = 15) -> int:
    """If fewer than min_words, keep existing data and return 0."""
    if len(words) < min_words:
      return 0
    with self._session_factory() as db:
      db.execute(delete(WordcloudTerm).where(WordcloudTerm.category == category).where(WordcloudTerm.region == region))
      for word in words:
        payload = word.model_dump() if hasattr(word, "model_dump") else dict(word)
        db.add(
          WordcloudTerm(
            category=category,
            region=region,
            text=str(payload["text"]),
            weight=float(payload["weight"]),
          )
        )
      db.commit()
    return len(words)

  def get_analysis(self, page: Page) -> Optional[Dict]:
    with self._session_factory() as db:
      row = db.scalar(select(AnalysisSnapshot).where(AnalysisSnapshot.page == page))
      if not row:
        return None
      updated_at = None
      if row.updated_at is not None:
        dt = row.updated_at
        if dt.tzinfo is None:
          from datetime import timezone
          dt = dt.replace(tzinfo=timezone.utc)
        updated_at = dt.isoformat()
      return {
        "line": list(row.line or []),
        "bar": list(row.bar or []),
        "donut": list(row.donut or []),
        "accents": dict(row.accents or {"line": "#6AE4FF", "bar": "#B79BFF"}),
        "updated_at": updated_at,
      }

  def set_analysis(
    self,
    page: Page,
    line: List[float],
    bar: List[float],
    donut: List[float],
    accents: Optional[Accents],
  ) -> None:
    with self._session_factory() as db:
      row = db.scalar(select(AnalysisSnapshot).where(AnalysisSnapshot.page == page))
      payload = (accents.model_dump() if hasattr(accents, "model_dump") else dict(accents)) if accents else None
      if row:
        row.line = list(line)
        row.bar = list(bar)
        row.donut = list(donut)
        row.accents = payload or row.accents or {"line": "#6AE4FF", "bar": "#B79BFF"}
      else:
        db.add(
          AnalysisSnapshot(
            page=page,
            line=list(line),
            bar=list(bar),
            donut=list(donut),
            accents=payload or {"line": "#6AE4FF", "bar": "#B79BFF"},
          )
        )
      db.commit()

  def seed_defaults(self) -> None:
    with self._session_factory() as db:
      has_wordcloud = db.scalar(select(WordcloudTerm.id).limit(1))
      has_analysis = db.scalar(select(AnalysisSnapshot.id).limit(1))

      if not has_wordcloud:
        for category, regions in default_wordcloud_store().items():
          for region, words in regions.items():
            for word in words:
              db.add(
                WordcloudTerm(
                  category=category,
                  region=region,
                  text=str(word["text"]),
                  weight=float(word["weight"]),
                )
              )

      if not has_analysis:
        for page, payload in default_analysis_store().items():
          db.add(
            AnalysisSnapshot(
              page=page,
              line=list(payload["line"]),
              bar=list(payload["bar"]),
              donut=list(payload["donut"]),
              accents=dict(payload["accents"]),
            )
          )

      db.commit()

  def record_etl_run(self, source: str, status: str, details: str = "") -> None:
    with self._session_factory() as db:
      db.add(EtlRun(source=source, status=status, details=details))
      db.commit()


def default_wordcloud_store() -> Dict[str, Dict[str, List[Dict[str, float]]]]:
  return {
    "agri": {
      "kr": [
        {"text": "배추", "weight": 86},
        {"text": "사과", "weight": 78},
        {"text": "양파", "weight": 72},
        {"text": "대파", "weight": 68},
        {"text": "감자", "weight": 64},
        {"text": "작황", "weight": 58},
        {"text": "수급", "weight": 54},
        {"text": "도매가", "weight": 50},
        {"text": "출하량", "weight": 46},
        {"text": "이상기온", "weight": 44},
        {"text": "산지", "weight": 42},
        {"text": "폭등", "weight": 40},
        {"text": "소비자가", "weight": 38},
        {"text": "가락시장", "weight": 36},
        {"text": "수입산", "weight": 34},
      ],
      "global": [
        {"text": "food prices", "weight": 80},
        {"text": "drought", "weight": 62},
        {"text": "fertilizer", "weight": 58},
        {"text": "supply chain", "weight": 56},
        {"text": "crop yield", "weight": 52},
        {"text": "harvest", "weight": 50},
        {"text": "wholesale", "weight": 46},
      ],
    },
  }


def default_analysis_store() -> Dict[str, Dict]:
  return {
    "analysis-1": {
      "line": [38, 41, 45, 44, 52, 58, 55, 61, 66, 64, 70, 76],
      "bar": [22, 18, 16, 14, 10],
      "donut": [44, 26, 18, 12],
      "accents": {"line": "#9AF7D0", "bar": "#6AE4FF"},
    },
  }

