from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.app.auth import get_current_user
from backend.app.services.custom_analysis_service import CustomAnalysisService


class SaveCustomAnalysisPayload(BaseModel):
    title: str = Field(..., max_length=80)
    category: str = Field(..., max_length=32)
    subcategory: str = Field(..., max_length=80)
    item: str = Field(default="all", max_length=80)
    year_from: int = Field(..., ge=2018, le=2030)
    year_to: int = Field(..., ge=2018, le=2030)
    method: str = Field(..., max_length=40)


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

    @router.get("/custom-analysis/items")
    def get_items(
        category: str = Query(..., description="카테고리 코드"),
        subcategory: str = Query(default="all", description="하위 카테고리 코드"),
    ) -> dict:
        return service.get_items(category, subcategory)

    @router.get("/custom-analysis/data")
    def get_data(
        category: str = Query(..., description="카테고리 코드"),
        subcategory: str = Query(default="all", description="하위 카테고리 코드"),
        item: str = Query(default="all", description="품목 코드 (all=전체)"),
        year_from: int = Query(default=2024, ge=2018, le=2030, description="시작 연도"),
        year_to: int = Query(default=2024, ge=2018, le=2030, description="종료 연도"),
        method: str = Query(default="trend", description="trend/compare/distribution/movers"),
        breakdown: str = Query(default="auto", description="비교 세분화 기준 (auto/item_nm/vrty_nm/se_nm/grd_nm)"),
    ) -> dict:
        return service.get_data(category, subcategory, item, year_from, year_to, method, breakdown)

    @router.get("/custom-analysis/saved")
    def list_saved(current_user: dict = Depends(get_current_user)) -> dict:
        items = service.list_saved(int(current_user["id"]))
        return {"items": items}

    @router.post("/custom-analysis/save", status_code=201)
    def save(
        payload: SaveCustomAnalysisPayload,
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        return service.save(
            user_id=int(current_user["id"]),
            title=payload.title,
            category=payload.category,
            subcategory=payload.subcategory,
            item=payload.item,
            year_from=payload.year_from,
            year_to=payload.year_to,
            method=payload.method,
        )

    return router
