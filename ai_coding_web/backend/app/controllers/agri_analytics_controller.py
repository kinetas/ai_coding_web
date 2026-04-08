from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.agri_analytics import (
  AgriAnalyticsResponse,
  AgriCategoryStatsResponse,
  AgriItemSeriesResponse,
  AgriPriceRawResponse,
  AgriRiceSeriesResponse,
)
from backend.app.services.agri_analytics_service import AgriAnalyticsService


def build_router(service: AgriAnalyticsService) -> APIRouter:
  router = APIRouter()

  @router.get("/agri-analytics", response_model=AgriAnalyticsResponse)
  def get_agri_analytics() -> AgriAnalyticsResponse:
    row = service.get_latest()
    if not row:
      raise HTTPException(
        status_code=404,
        detail="No agri_price_analytics data. Set DATA_GO_KR_SERVICE_KEY and AT_PRICE_API_PATH in .env, then run: python etl.py --agri or --all",
      )
    return row

  @router.get("/agri-analytics/raw", response_model=AgriPriceRawResponse)
  def get_agri_price_raw() -> AgriPriceRawResponse:
    row = service.get_raw_latest()
    if not row:
      raise HTTPException(
        status_code=404,
        detail="No agri_price_raw data. Run: python etl.py --agri or --all, then retry.",
      )
    return row

  @router.get("/agri-analytics/category-stats", response_model=AgriCategoryStatsResponse)
  def get_agri_category_stats() -> AgriCategoryStatsResponse:
    row = service.get_category_stats()
    if not row:
      raise HTTPException(
        status_code=404,
        detail="No agri_price_raw data. Run: python etl.py --agri or --all.",
      )
    return row

  @router.get("/agri-analytics/rice-series", response_model=AgriRiceSeriesResponse)
  def get_agri_rice_series() -> AgriRiceSeriesResponse:
    row = service.get_rice_weekly_series()
    if row is None:
      raise HTTPException(status_code=503, detail="Failed to load rice price time series.")
    return row

  @router.get("/agri-analytics/item-series", response_model=AgriItemSeriesResponse)
  def get_agri_item_series(
    item_cd: str = Query(..., min_length=1, description="Item code (agri_price_history.item_cd)"),
    vrty_cd: str | None = Query(default=None, description="Optional variety code filter"),
  ) -> AgriItemSeriesResponse:
    row = service.get_item_price_series(item_cd, vrty_cd)
    if row is None:
      raise HTTPException(
        status_code=503,
        detail="agri_price_history query failed. Ensure ETL has run.",
      )
    return row

  return router
