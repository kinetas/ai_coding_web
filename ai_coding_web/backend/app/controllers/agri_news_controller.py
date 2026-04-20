from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query


def build_router() -> APIRouter:
  router = APIRouter()

  @router.get("/agri/news")
  def get_agri_news(
    crop: Optional[str] = Query(default=None, description="품목명 (배추/무/사과/대파/양파/감자/고추/쌀/토마토/오이)"),
    limit: int = Query(default=30, ge=1, le=100),
  ):
    from crawler.news_pipeline import fetch_agri_news
    return fetch_agri_news(crop=crop, limit=limit)

  return router
