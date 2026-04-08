from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.auth import get_current_user
from backend.app.models.builder import (
  BuilderCatalogListResponse,
  BuilderChatPayload,
  BuilderChatResponse,
  BuilderMetricResponse,
  BuilderSuggestionsResponse,
  ClassificationsResponse,
  SaveBuilderAnalysisPayload,
  SavedBuilderAnalysesResponse,
)
from backend.app.services.builder_service import BuilderService


def build_router(service: BuilderService) -> APIRouter:
  router = APIRouter()

  @router.get("/builder/classifications", response_model=ClassificationsResponse)
  def classifications():
    return service.list_classifications()

  @router.get("/builder/catalog", response_model=BuilderCatalogListResponse)
  def catalog(
    classification: str | None = Query(default=None, description="비우면 전체 행"),
  ):
    return service.list_catalog_entries(classification)

  @router.get("/builder/suggestions", response_model=BuilderSuggestionsResponse)
  def suggestions(
    keyword: str = Query(default=""),
    category: str | None = Query(default=None, description="농산물 시세·의료·교통·관광·환경"),
  ):
    return service.suggestions(keyword, category_label=category)

  @router.get("/builder/metric", response_model=BuilderMetricResponse)
  def metric(keyword: str = Query(default=""), metric: str = Query(...)):
    return service.metric(keyword, metric)

  @router.get("/builder/saved", response_model=SavedBuilderAnalysesResponse)
  def saved(
    current_user: dict = Depends(get_current_user),
    category: str | None = Query(default=None, description="지정 시 해당 분류만 조회"),
  ):
    return service.list_saved(current_user, category_label=category)

  @router.post("/builder/save")
  def save(payload: SaveBuilderAnalysisPayload, current_user: dict = Depends(get_current_user)):
    return service.save(
      user=current_user,
      title=payload.title,
      keyword=payload.keyword,
      metric=payload.metric,
      metric_label=payload.metric_label,
      category_label=payload.category_label,
    )

  @router.post("/builder/chat", response_model=BuilderChatResponse)
  def chat(payload: BuilderChatPayload, current_user: dict = Depends(get_current_user)):
    return service.chat(user=current_user, keyword=payload.keyword, question=payload.question)

  return router

