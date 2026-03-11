from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.models.builder import (
  BuilderChatPayload,
  BuilderChatResponse,
  BuilderMetricResponse,
  BuilderSuggestionsResponse,
  SaveBuilderAnalysisPayload,
  SavedBuilderAnalysesResponse,
)
from backend.app.services.builder_service import BuilderService


def build_router(service: BuilderService) -> APIRouter:
  router = APIRouter()

  @router.get("/builder/suggestions", response_model=BuilderSuggestionsResponse)
  def suggestions(keyword: str = Query(default="")):
    return service.suggestions(keyword)

  @router.get("/builder/metric", response_model=BuilderMetricResponse)
  def metric(keyword: str = Query(default=""), metric: str = Query(...)):
    return service.metric(keyword, metric)

  @router.get("/builder/saved", response_model=SavedBuilderAnalysesResponse)
  def saved(user: str = Query(default="")):
    return service.list_saved(user)

  @router.post("/builder/save")
  def save(payload: SaveBuilderAnalysisPayload):
    return service.save(
      user=payload.user,
      title=payload.title,
      keyword=payload.keyword,
      metric=payload.metric,
      metric_label=payload.metric_label,
    )

  @router.post("/builder/chat", response_model=BuilderChatResponse)
  def chat(payload: BuilderChatPayload):
    return service.chat(user=payload.user, keyword=payload.keyword, question=payload.question)

  return router

