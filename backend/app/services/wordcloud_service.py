from __future__ import annotations

from backend.app.core.time import utc_now_iso
from backend.app.models.types import Category, Region
from backend.app.repositories.memory_store import ContentStore


class WordcloudService:
  def __init__(self, store: ContentStore):
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
    self._store.record_etl_run(source="wordcloud_ingest", status="success", details=f"category={category},region={region},count={count}")
    return {"ok": True, "category": category, "region": region, "count": count, "ts": utc_now_iso()}

