from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.auth import require_etl_token
from backend.app.models.types import Page
from backend.app.models.analysis import AnalysisResponse, IngestAnalysisPayload
from backend.app.services.analysis_service import AnalysisService


def build_router(service: AnalysisService) -> APIRouter:
  router = APIRouter()

  @router.get("/analysis", response_model=AnalysisResponse)
  def get_analysis(page: Page = Query(...)):
    return service.get_analysis(page)

  @router.post("/ingest/analysis")
  def ingest_analysis(payload: IngestAnalysisPayload, _: None = Depends(require_etl_token)):
    return service.ingest(
      page=payload.page,
      line=payload.line,
      bar=payload.bar,
      donut=payload.donut,
      accents=payload.accents,
    )

  return router

