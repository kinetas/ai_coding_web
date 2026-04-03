from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.app.models.types import PublicCategory


class PublicCategoryAnalyticsResponse(BaseModel):
  category_code: PublicCategory
  slug: str = "latest"
  updated_at: str
  source: str = "data_go_kr"
  meta: dict[str, Any] = Field(default_factory=dict)
  chart_bundle: dict[str, Any] = Field(default_factory=dict)
  summary: dict[str, Any] = Field(default_factory=dict)
  distribution: dict[str, Any] = Field(default_factory=dict)


class PublicCategoryRawResponse(BaseModel):
  category_code: PublicCategory
  slug: str = "latest"
  updated_at: str
  source: str = "data_go_kr"
  meta: dict[str, Any] = Field(default_factory=dict)
  api_meta: dict[str, Any] = Field(default_factory=dict)
  items: list[dict[str, Any]] = Field(default_factory=list)
