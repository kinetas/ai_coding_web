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
  unit_label: str = ""          # 예: "원/kg환산", "원/개"


class AgriUnitFamilyStats(BaseModel):
  """단위군별 세부 통계 (가이드 6번 실무 규칙)."""
  unit_family: str              # weight / count / pack / volume / special
  price_label: str              # "원/kg환산" or "원/{unit}"
  count: int
  avg_price: float | None = None
  min_price: float | None = None
  max_price: float | None = None
  cheapest: AgriCategoryItem | None = None
  most_expensive: AgriCategoryItem | None = None


class AgriCategoryStats(BaseModel):
  ctgry_nm: str
  count: int                    # 전체 건수(단위군 합산)
  # weight 계열 대표 통계(cnvs 가격 기준, 단위군 중 가장 많은 경우가 많음)
  min_price: float | None = None
  max_price: float | None = None
  avg_price: float | None = None
  price_label: str = "원"       # 대표 가격 단위 설명
  cheapest: AgriCategoryItem | None = None
  most_expensive: AgriCategoryItem | None = None
  # 단위군별 세분화 (가이드: 단위가 다른 경우 별도 시계열로 볼 것)
  unit_breakdown: list[AgriUnitFamilyStats] = Field(default_factory=list)


class AgriCategoryStatsResponse(BaseModel):
  updated_at: str
  survey_date: str = ""   # 집계 기준 최신 조사일 YYYYMMDD
  categories: list[AgriCategoryStats] = Field(default_factory=list)
  meta: dict[str, Any] = Field(default_factory=dict)


# ── 가격 등락 품목 (WoW / 4주) ───────────────────────────────────────────────

class AgriPriceMover(BaseModel):
  """전주 대비 등락 품목 요약."""
  item_nm: str
  vrty_nm: str = ""
  grd_nm: str = ""
  se_nm: str = ""
  ctgry_nm: str = ""
  unit_label: str = ""          # "100g", "1kg", "10개" 등
  price_cur: float | None = None   # 조사일 가격
  price_prev: float | None = None  # 1주 전 가격
  wow_pct: float | None = None     # 전주 대비 %
  w4_pct: float | None = None      # 4주 대비 %


class AgriPriceMoversResponse(BaseModel):
  updated_at: str
  survey_date: str = ""
  top_risers: list[AgriPriceMover] = Field(default_factory=list)
  top_fallers: list[AgriPriceMover] = Field(default_factory=list)
  meta: dict[str, Any] = Field(default_factory=dict)


# ── 쌀 주차별 시계열 + 예측 ──────────────────────────────────────────────────

class AgriWeeklyPoint(BaseModel):
  week_label: str   # "YYYY-WNN"
  date_label: str = ""  # 해당 주 월요일 날짜 "YYYY-MM-DD"
  avg_price: float


class AgriRiceSeriesResponse(BaseModel):
  item_nm: str = "쌀"
  item_cd: str | None = None
  weekly_series: list[AgriWeeklyPoint] = Field(default_factory=list)
  forecast: dict[str, Any] = Field(default_factory=dict)
  meta: dict[str, Any] = Field(default_factory=dict)
