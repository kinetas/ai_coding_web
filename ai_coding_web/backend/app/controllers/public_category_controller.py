from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.models.public_category import PublicCategoryAnalyticsResponse, PublicCategoryRawResponse
from backend.app.models.types import PublicCategory
from backend.app.services.public_category_service import PublicCategoryService


def build_router(service: PublicCategoryService) -> APIRouter:
  router = APIRouter()

  @router.get(
    "/public-category/{category_code}/analytics",
    response_model=PublicCategoryAnalyticsResponse,
  )
  def get_public_analytics(category_code: PublicCategory) -> PublicCategoryAnalyticsResponse:
    row = service.get_analytics(category_code)
    if not row:
      raise HTTPException(
        status_code=404,
        detail="public_category_analytics 에 해당 카테고리 데이터가 없습니다. .env PD_*_API_PATH 설정 후 ETL(crawl)을 실행하세요.",
      )
    return row

  @router.get("/public-category/{category_code}/raw", response_model=PublicCategoryRawResponse)
  def get_public_raw(category_code: PublicCategory) -> PublicCategoryRawResponse:
    row = service.get_raw(category_code)
    if not row:
      raise HTTPException(
        status_code=404,
        detail="public_category_raw 에 해당 카테고리 데이터가 없습니다. .env PD_*_API_PATH 설정 후 ETL(crawl)을 실행하세요.",
      )
    return row

  return router
