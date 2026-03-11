from __future__ import annotations

from backend.app.core.time import utc_now_iso
from backend.app.models.types import Category, Region
from backend.app.repositories.memory_store import InMemoryStore


class WordcloudService:
  def __init__(self, store: InMemoryStore):
    self._store = store

  def get_wordcloud(self, category: Category, region: Region):
    return {
      "category": category,
      "region": region,
      "generated_at": utc_now_iso(),
      "words": self._store.get_wordcloud(category, region),
    }

  def ingest(self, category: Category, region: Region, words):
    count = self._store.set_wordcloud(category, region, words)
    return {"ok": True, "category": category, "region": region, "count": count, "ts": utc_now_iso()}

