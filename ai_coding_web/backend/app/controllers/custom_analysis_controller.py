from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.services.custom_analysis_service import CustomAnalysisService


def build_router(service: CustomAnalysisService) -> APIRouter:
    router = APIRouter()

    @router.get("/custom-analysis/meta")
    def get_meta() -> dict:
        return service.get_meta()

    @router.get("/custom-analysis/subcategories")
    def get_subcategories(
        category: str = Query(..., description="카테고리 코드 (agri/health/traffic/tour/env)"),
    ) -> dict:
        return service.get_subcategories(category)

    @router.get("/custom-analysis/data")
    def get_data(
        category: str = Query(..., description="카테고리 코드"),
        subcategory: str = Query(default="all", description="하위 카테고리 코드"),
        year: int = Query(default=2024, ge=2018, le=2030, description="분석 연도"),
        method: str = Query(default="trend", description="trend/compare/distribution/movers"),
    ) -> dict:
        return service.get_data(category, subcategory, year, method)

    return router
