"""공공 카테고리 분석 서비스 — 로컬 DB(SQLAlchemy) 기반."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.config import Settings
from backend.app.db import SessionLocal
from backend.app.db_models import PublicCategoryAnalytics, PublicCategoryRaw
from backend.app.models.public_category import PublicCategoryAnalyticsResponse, PublicCategoryRawResponse
from backend.app.models.types import PublicCategory


class PublicCategoryService:
  """로컬 DB(SQLite/PostgreSQL)에서 공공 카테고리 분석 데이터 조회."""

  def __init__(self, settings: Settings, session_factory: sessionmaker | None = None):
    self._session_factory: sessionmaker = session_factory or SessionLocal

  def get_analytics(self, category_code: PublicCategory) -> PublicCategoryAnalyticsResponse | None:
    with self._session_factory() as db:
      row = db.scalar(
        select(PublicCategoryAnalytics)
        .where(PublicCategoryAnalytics.category_code == category_code)
        .where(PublicCategoryAnalytics.slug == "latest")
      )
    if not row:
      return None
    updated_at = row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat()
    return PublicCategoryAnalyticsResponse(
      category_code=category_code,
      slug=row.slug,
      updated_at=updated_at,
      source=row.source,
      meta=row.meta or {},
      chart_bundle=row.chart_bundle or {},
      summary=row.summary or {},
      distribution=row.distribution or {},
    )

  def get_raw(self, category_code: PublicCategory) -> PublicCategoryRawResponse | None:
    with self._session_factory() as db:
      row = db.scalar(
        select(PublicCategoryRaw)
        .where(PublicCategoryRaw.category_code == category_code)
        .where(PublicCategoryRaw.slug == "latest")
      )
    if not row:
      return None
    updated_at = row.updated_at.isoformat() if row.updated_at else datetime.now(timezone.utc).isoformat()
    return PublicCategoryRawResponse(
      category_code=category_code,
      slug=row.slug,
      updated_at=updated_at,
      source=row.source,
      meta=row.meta or {},
      api_meta=row.api_meta or {},
      items=row.items or [],
    )
