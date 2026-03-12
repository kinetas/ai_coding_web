from __future__ import annotations

from fastapi import HTTPException

from backend.app.core.time import utc_now_iso
from backend.app.models.types import Page
from backend.app.repositories.memory_store import ContentStore


class AnalysisService:
  def __init__(self, store: ContentStore):
    self._store = store

  def get_analysis(self, page: Page):
    cfg = self._store.get_analysis(page)
    if not cfg:
      raise HTTPException(status_code=404, detail="unknown page")
    return {
      "page": page,
      "generated_at": utc_now_iso(),
      "line": cfg["line"],
      "bar": cfg["bar"],
      "donut": cfg["donut"],
      "accents": cfg.get("accents") or {"line": "#6AE4FF", "bar": "#B79BFF"},
    }

  def ingest(self, page: Page, line, bar, donut, accents):
    self._store.set_analysis(page, line=line, bar=bar, donut=donut, accents=accents)
    self._store.record_etl_run(source="analysis_ingest", status="success", details=f"page={page}")
    return {"ok": True, "page": page, "ts": utc_now_iso()}

