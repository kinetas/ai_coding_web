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
        detail="agri_price_analytics 에 데이터가 없습니다. .env 에 DATA_GO_KR_SERVICE_KEY·AT_PRICE_API_PATH 설정 후 python etl.py --agri 또는 --all 을 실행하세요.",
      )
    return row

  @router.get("/agri-analytics/raw", response_model=AgriPriceRawResponse)
  def get_agri_price_raw() -> AgriPriceRawResponse:
    row = service.get_raw_latest()
    if not row:
      raise HTTPException(
        status_code=404,
        detail="agri_price_raw 에 데이터가 없습니다. python etl.py --agri 또는 --all 실행 후 다시 시도하세요.",
      )
    return row

  @router.get("/agri-analytics/category-stats", response_model=AgriCategoryStatsResponse)
  def get_agri_category_stats() -> AgriCategoryStatsResponse:
    row = service.get_category_stats()
    if not row:
      raise HTTPException(
        status_code=404,
        detail="agri_price_raw 에 데이터가 없습니다. python etl.py --agri 또는 --all 을 실행하세요.",
      )
    return row

  @router.get("/agri-analytics/rice-series", response_model=AgriRiceSeriesResponse)
  def get_agri_rice_series() -> AgriRiceSeriesResponse:
    row = service.get_rice_weekly_series()
    if row is None:
      raise HTTPException(status_code=503, detail="쌀 가격 시계열 조회에 실패했습니다.")
    return row

  @router.get("/agri-analytics/item-series", response_model=AgriItemSeriesResponse)
  def get_agri_item_series(
    item_cd: str = Query(..., min_length=1, description="품목코드 (agri_price_history.item_cd)"),
    vrty_cd: str | None = Query(default=None, description="선택: 품종코드로 좁히기"),
  ) -> AgriItemSeriesResponse:
    row = service.get_item_price_series(item_cd, vrty_cd)
    if row is None:
      raise HTTPException(
        status_code=503,
        detail="agri_price_history 조회에 실패했습니다. ETL을 실행했는지 확인하세요.",
      )
    return row

  return router
