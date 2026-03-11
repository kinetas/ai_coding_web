from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.models.types import Category, Region
from backend.app.models.wordcloud import IngestWordcloudPayload, WordcloudResponse
from backend.app.services.wordcloud_service import WordcloudService


def build_router(service: WordcloudService) -> APIRouter:
  router = APIRouter()

  @router.get("/wordcloud", response_model=WordcloudResponse)
  def get_wordcloud(
    category: Category = Query(default="all"),
    region: Region = Query(default="kr"),
  ):
    return service.get_wordcloud(category, region)

  @router.post("/ingest/wordcloud")
  def ingest_wordcloud(payload: IngestWordcloudPayload):
    return service.ingest(payload.category, payload.region, payload.words)

  return router

