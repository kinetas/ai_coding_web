from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgriAnalyticsResponse(BaseModel):
  slug: str = "latest"
  updated_at: str
  source: str = "data_go_kr"
  meta: dict[str, Any] = Field(default_factory=dict)
  region_stats: list[Any] = Field(default_factory=list)
  overall: dict[str, Any] = Field(default_factory=dict)
  forecast: dict[str, Any] = Field(default_factory=dict)
  distribution: dict[str, Any] = Field(default_factory=dict)
  chart_bundle: dict[str, Any] = Field(default_factory=dict)


class AgriPriceRawResponse(BaseModel):
  """공공데이터 API에서 파싱한 원본 item[] (가공 전)."""

  slug: str = "latest"
  updated_at: str
  source: str = "data_go_kr"
  meta: dict[str, Any] = Field(default_factory=dict)
  api_meta: dict[str, Any] = Field(default_factory=dict)
  items: list[dict[str, Any]] = Field(default_factory=list)


class AgriItemSeriesPoint(BaseModel):
  """agri_price_history 기준 조사일별 스냅샷(품목·가격 요약)."""

  exmn_ymd: str
  item_nm: str = ""
  price: float | None = None
  price_raw: float | None = None


class AgriItemSeriesResponse(BaseModel):
  item_cd: str
  vrty_cd: str | None = None
  points: list[AgriItemSeriesPoint] = Field(default_factory=list)
  meta: dict[str, Any] = Field(default_factory=dict)


# ── 카테고리별 통계 ──────────────────────────────────────────────────────────

class AgriCategoryItem(BaseModel):
  """카테고리 내 최저/최고 품목 요약."""
  item_nm: str
  price: float | None = None


class AgriCategoryStats(BaseModel):
  ctgry_nm: str
  count: int
  min_price: float | None = None
  max_price: float | None = None
  avg_price: float | None = None
  cheapest: AgriCategoryItem | None = None
  most_expensive: AgriCategoryItem | None = None


class AgriCategoryStatsResponse(BaseModel):
  updated_at: str
  categories: list[AgriCategoryStats] = Field(default_factory=list)
  meta: dict[str, Any] = Field(default_factory=dict)


# ── 쌀 주차별 시계열 + 예측 ──────────────────────────────────────────────────

class AgriWeeklyPoint(BaseModel):
  week_label: str   # "YYYY-WNN"
  avg_price: float


class AgriRiceSeriesResponse(BaseModel):
  item_nm: str = "쌀"
  item_cd: str | None = None
  weekly_series: list[AgriWeeklyPoint] = Field(default_factory=list)
  forecast: dict[str, Any] = Field(default_factory=dict)
  meta: dict[str, Any] = Field(default_factory=dict)
