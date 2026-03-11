from __future__ import annotations

from typing import Dict, List, Optional

from backend.app.models.types import Category, Page, Region
from backend.app.models.analysis import Accents
from backend.app.models.wordcloud import Word


class InMemoryStore:
  def __init__(self):
    self._wordcloud: Dict[str, Dict[str, List[Dict[str, float]]]] = default_wordcloud_store()
    self._analysis: Dict[str, Dict] = default_analysis_store()

  def get_wordcloud(self, category: Category, region: Region) -> List[Dict[str, float]]:
    if category == "all":
      return self.merge_all_words(region)
    return self._wordcloud.get(category, {}).get(region, [])

  def set_wordcloud(self, category: Category, region: Region, words: List[Word]) -> int:
    self._wordcloud.setdefault(category, {}).setdefault(region, [])
    self._wordcloud[category][region] = [w.model_dump() for w in words]
    return len(self._wordcloud[category][region])

  def merge_all_words(self, region: Region) -> List[Dict[str, float]]:
    merged: Dict[str, float] = {}
    for _, regions in self._wordcloud.items():
      for w in regions.get(region, []):
        key = str(w.get("text", ""))
        if not key:
          continue
        merged[key] = merged.get(key, 0) + float(w.get("weight", 0))
    words = [{"text": k, "weight": v} for k, v in merged.items()]
    words.sort(key=lambda x: float(x["weight"]), reverse=True)
    return words[:28]

  def get_analysis(self, page: Page) -> Optional[Dict]:
    return self._analysis.get(page)

  def set_analysis(
    self,
    page: Page,
    line: List[float],
    bar: List[float],
    donut: List[float],
    accents: Optional[Accents],
  ) -> None:
    self._analysis[page] = {
      "line": list(line),
      "bar": list(bar),
      "donut": list(donut),
      "accents": (accents.model_dump() if accents else self._analysis.get(page, {}).get("accents") or {"line": "#6AE4FF", "bar": "#B79BFF"}),
    }


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
  }

