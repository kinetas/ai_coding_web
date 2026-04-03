from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from backend.app.models.analysis import Accents
from backend.app.models.types import Category, Page, Region
from backend.app.models.wordcloud import Word


class ContentAccess(Protocol):
  """ContentStore · SupabaseContentStore 공통 인터페이스."""

  def get_wordcloud(self, category: Category, region: Region) -> List[Dict[str, float]]: ...

  def set_wordcloud(self, category: Category, region: Region, words: List[Word]) -> int: ...

  def get_analysis(self, page: Page) -> Optional[Dict[str, Any]]: ...

  def set_analysis(
    self,
    page: Page,
    line: List[float],
    bar: List[float],
    donut: List[float],
    accents: Optional[Accents],
  ) -> None: ...

  def seed_defaults(self) -> None: ...

  def record_etl_run(self, source: str, status: str, details: str = "") -> None: ...
