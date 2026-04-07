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
        merged: Dict[str, float] = {}
        for row in rows:
          merged[row.text] = merged.get(row.text, 0) + float(row.weight)
        words = [{"text": key, "weight": value} for key, value in merged.items()]
        words.sort(key=lambda item: float(item["weight"]), reverse=True)
        return words[:28]

      rows = db.scalars(
        select(WordcloudTerm)
        .where(WordcloudTerm.category == category)
        .where(WordcloudTerm.region == region)
        .order_by(WordcloudTerm.weight.desc())
      ).all()
      return [{"text": row.text, "weight": float(row.weight)} for row in rows[:28]]

  def set_wordcloud(self, category: Category, region: Region, words: List[Word], min_words: int = 15) -> int:
    """새 단어 목록이 min_words 미만이면 기존 데이터를 유지하고 0을 반환합니다."""
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
      return {
        "line": list(row.line or []),
        "bar": list(row.bar or []),
        "donut": list(row.donut or []),
        "accents": dict(row.accents or {"line": "#6AE4FF", "bar": "#B79BFF"}),
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
        {"text": "사과", "weight": 86},
        {"text": "배추", "weight": 72},
        {"text": "양파", "weight": 66},
        {"text": "쌀값", "weight": 64},
        {"text": "도매가격", "weight": 58},
        {"text": "기상", "weight": 52},
        {"text": "산지", "weight": 50},
        {"text": "수급", "weight": 46},
        {"text": "물가", "weight": 44},
      ],
      "global": [
        {"text": "food prices", "weight": 80},
        {"text": "drought", "weight": 62},
        {"text": "fertilizer", "weight": 58},
        {"text": "supply chain", "weight": 56},
        {"text": "coffee", "weight": 54},
        {"text": "wheat", "weight": 52},
        {"text": "crop yield", "weight": 50},
      ],
    },
    "health": {
      "kr": [
        {"text": "독감", "weight": 82},
        {"text": "응급실", "weight": 60},
        {"text": "진료예약", "weight": 58},
        {"text": "비대면", "weight": 54},
        {"text": "건강검진", "weight": 52},
        {"text": "약국", "weight": 48},
        {"text": "감염", "weight": 46},
      ],
      "global": [
        {"text": "flu", "weight": 70},
        {"text": "telehealth", "weight": 62},
        {"text": "vaccination", "weight": 56},
        {"text": "mental health", "weight": 54},
        {"text": "AI in healthcare", "weight": 52},
        {"text": "outbreak", "weight": 50},
      ],
    },
    "traffic": {
      "kr": [
        {"text": "지하철 지연", "weight": 74},
        {"text": "버스", "weight": 58},
        {"text": "출근길", "weight": 56},
        {"text": "택시", "weight": 50},
        {"text": "전기차 충전", "weight": 48},
        {"text": "혼잡", "weight": 46},
        {"text": "사고", "weight": 44},
      ],
      "global": [
        {"text": "EV charging", "weight": 66},
        {"text": "public transit", "weight": 58},
        {"text": "traffic congestion", "weight": 56},
        {"text": "autonomous", "weight": 52},
        {"text": "micro-mobility", "weight": 50},
      ],
    },
    "tour": {
      "kr": [
        {"text": "벚꽃", "weight": 78},
        {"text": "축제", "weight": 62},
        {"text": "맛집", "weight": 60},
        {"text": "여행코스", "weight": 54},
        {"text": "숙박", "weight": 50},
        {"text": "항공권", "weight": 48},
      ],
      "global": [
        {"text": "cherry blossom", "weight": 64},
        {"text": "budget travel", "weight": 58},
        {"text": "visa", "weight": 54},
        {"text": "travel deals", "weight": 52},
        {"text": "city break", "weight": 50},
      ],
    },
    "env": {
      "kr": [
        {"text": "미세먼지", "weight": 84},
        {"text": "폭염", "weight": 60},
        {"text": "탄소중립", "weight": 56},
        {"text": "재활용", "weight": 52},
        {"text": "기후", "weight": 48},
        {"text": "홍수", "weight": 44},
      ],
      "global": [
        {"text": "climate", "weight": 70},
        {"text": "heatwave", "weight": 62},
        {"text": "wildfire", "weight": 58},
        {"text": "renewables", "weight": 54},
        {"text": "carbon", "weight": 52},
      ],
    },
  }


def default_analysis_store() -> Dict[str, Dict]:
  return {
    "analysis-1": {
      "line": [38, 41, 45, 44, 52, 58, 55, 61, 66, 64, 70, 76],
      "bar": [12, 18, 10, 22, 16],
      "donut": [44, 26, 18, 12],
      "accents": {"line": "#6AE4FF", "bar": "#B79BFF"},
    },
    "analysis-2": {
      "line": [22, 26, 30, 28, 34, 40, 48, 52, 46, 50, 58, 62],
      "bar": [8, 14, 20, 16, 12],
      "donut": [36, 24, 20, 20],
      "accents": {"line": "#9AF7D0", "bar": "#6AE4FF"},
    },
    "analysis-3": {
      "line": [18, 24, 29, 33, 38, 44, 40, 48, 56, 52, 60, 66],
      "bar": [10, 16, 26, 18, 14],
      "donut": [40, 28, 20, 12],
      "accents": {"line": "#FFD36A", "bar": "#FF7AD9"},
    },
    "analysis-4": {
      "line": [14, 16, 20, 18, 24, 28, 34, 30, 36, 40, 44, 48],
      "bar": [6, 12, 14, 10, 8],
      "donut": [34, 22, 24, 20],
      "accents": {"line": "#B79BFF", "bar": "#9AF7D0"},
    },
    "analysis-5": {
      "line": [20, 22, 26, 28, 32, 36, 40, 38, 44, 48, 52, 56],
      "bar": [8, 14, 12, 16, 10],
      "donut": [38, 26, 20, 16],
      "accents": {"line": "#7CFCA0", "bar": "#5BC0EB"},
    },
  }

