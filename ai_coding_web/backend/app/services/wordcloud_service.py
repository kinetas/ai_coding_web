from __future__ import annotations

from backend.app.core.time import utc_now_iso
from backend.app.models.types import Category, Region
from backend.app.repositories.content_access import ContentAccess


class WordcloudService:
  def __init__(self, store: ContentAccess):
    self._store = store

  def get_wordcloud(self, category: Category, region: Region):
    words = self._store.get_wordcloud(category, region)
    updated_at = None
    if hasattr(self._store, "get_wordcloud_updated_at"):
      updated_at = self._store.get_wordcloud_updated_at(category, region)
    return {
      "category": category,
      "region": region,
      "updated_at": updated_at or utc_now_iso(),
      "words": words,
    }

  def ingest(self, category: Category, region: Region, words):
    count = self._store.set_wordcloud(category, region, words)
    self._store.record_etl_run(source="wordcloud_ingest", status="success", details=f"category={category},region={region},count={count}")
    return {"ok": True, "category": category, "region": region, "count": count, "ts": utc_now_iso()}

