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
        detail="No public_category_analytics row for this category. Set PD_*_API_PATH in .env and run ETL.",
      )
    return row

  @router.get("/public-category/{category_code}/raw", response_model=PublicCategoryRawResponse)
  def get_public_raw(category_code: PublicCategory) -> PublicCategoryRawResponse:
    row = service.get_raw(category_code)
    if not row:
      raise HTTPException(
        status_code=404,
        detail="No public_category_raw row for this category. Set PD_*_API_PATH in .env and run ETL.",
      )
    return row

  return router
