from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


class User(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
  # data.md 기준: 화면 표시용 닉네임
  nickname: Mapped[str] = mapped_column(String(80))
  password_hash: Mapped[str] = mapped_column(String(255))
  # data.md 기준: active/inactive/deleted
  status: Mapped[str] = mapped_column(String(20), server_default="active", index=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuthSession(Base):
  __tablename__ = "auth_sessions"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
  expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

  user: Mapped[User] = relationship()


class AnalysisSnapshot(Base):
  __tablename__ = "analysis_snapshots"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  page: Mapped[str] = mapped_column(String(32), unique=True, index=True)
  line: Mapped[list[float]] = mapped_column(JSON)
  bar: Mapped[list[float]] = mapped_column(JSON)
  donut: Mapped[list[float]] = mapped_column(JSON)
  accents: Mapped[dict[str, str]] = mapped_column(JSON)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WordcloudTerm(Base):
  __tablename__ = "wordcloud_terms"
  __table_args__ = (
    UniqueConstraint("category", "region", "text", name="uq_wordcloud_term_scope"),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  category: Mapped[str] = mapped_column(String(32), index=True)
  region: Mapped[str] = mapped_column(String(32), index=True)
  text: Mapped[str] = mapped_column(String(64))
  weight: Mapped[float] = mapped_column(Float)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SavedBuilderAnalysis(Base):
  __tablename__ = "saved_builder_analyses"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  # 공개 페이지 카테고리와 동일한 분류명 (예: 농산물 시세, 의료)
  category_label: Mapped[str] = mapped_column(String(80), server_default="", index=True)
  title: Mapped[str] = mapped_column(String(80))
  keyword: Mapped[str] = mapped_column(String(80), index=True)
  metric: Mapped[str] = mapped_column(String(40))
  metric_label: Mapped[str] = mapped_column(String(80))
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

  user: Mapped[User] = relationship()


class BuilderKeywordCatalog(Base):
  """빌더 선택용 목록. DB 컬럼 `분류`(id 직후), keyword_key, keyword_value."""

  __tablename__ = "builder_keyword_catalog"
  __table_args__ = (
    UniqueConstraint("classification", "keyword_key", name="uq_builder_keyword_catalog_class_key"),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  classification: Mapped[str] = mapped_column("분류", String(80), nullable=False, index=True)
  keyword_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
  keyword_value: Mapped[str] = mapped_column(String(200), nullable=False)


class EtlRun(Base):
  __tablename__ = "etl_runs"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  source: Mapped[str] = mapped_column(String(80), index=True)
  status: Mapped[str] = mapped_column(String(20), index=True)
  details: Mapped[str] = mapped_column(Text, default="")
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class AgriPriceAnalytics(Base):
  """농산물 가격 분석 패키지 (slug='latest' 로 최신 1건 유지)."""
  __tablename__ = "agri_price_analytics"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  slug: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="latest")
  source: Mapped[str] = mapped_column(String(80), default="data_go_kr")
  meta: Mapped[dict] = mapped_column(JSON, default=dict)
  region_stats: Mapped[list] = mapped_column(JSON, default=list)
  overall: Mapped[dict] = mapped_column(JSON, default=dict)
  forecast: Mapped[dict] = mapped_column(JSON, default=dict)
  distribution: Mapped[dict] = mapped_column(JSON, default=dict)
  chart_bundle: Mapped[dict] = mapped_column(JSON, default=dict)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgriPriceRaw(Base):
  """농산물 가격 원본 데이터 스냅샷 (slug='latest' 로 최신 1건 유지)."""
  __tablename__ = "agri_price_raw"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  slug: Mapped[str] = mapped_column(String(32), unique=True, index=True, default="latest")
  source: Mapped[str] = mapped_column(String(80), default="data_go_kr")
  meta: Mapped[dict] = mapped_column(JSON, default=dict)
  api_meta: Mapped[dict] = mapped_column(JSON, default=dict)
  items: Mapped[list] = mapped_column(JSON, default=list)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgriPriceHistory(Base):
  """농산물 품목별 조사일 시계열 이력."""
  __tablename__ = "agri_price_history"
  __table_args__ = (
    UniqueConstraint("item_cd", "vrty_cd", "exmn_ymd", name="uq_agri_history_key"),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  item_cd: Mapped[str] = mapped_column(String(32), index=True)
  vrty_cd: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
  exmn_ymd: Mapped[str] = mapped_column(String(8), index=True)  # YYYYMMDD
  payload: Mapped[dict] = mapped_column(JSON, default=dict)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicCategoryAnalytics(Base):
  """공공 카테고리별 분석 패키지 (category_code + slug='latest' 로 최신 1건 유지)."""
  __tablename__ = "public_category_analytics"
  __table_args__ = (
    UniqueConstraint("category_code", "slug", name="uq_pub_cat_analytics_key"),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  category_code: Mapped[str] = mapped_column(String(32), index=True)
  slug: Mapped[str] = mapped_column(String(32), default="latest")
  source: Mapped[str] = mapped_column(String(80), default="data_go_kr")
  meta: Mapped[dict] = mapped_column(JSON, default=dict)
  chart_bundle: Mapped[dict] = mapped_column(JSON, default=dict)
  summary: Mapped[dict] = mapped_column(JSON, default=dict)
  distribution: Mapped[dict] = mapped_column(JSON, default=dict)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PublicCategoryRaw(Base):
  """공공 카테고리별 원본 데이터 스냅샷."""
  __tablename__ = "public_category_raw"
  __table_args__ = (
    UniqueConstraint("category_code", "slug", name="uq_pub_cat_raw_key"),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  category_code: Mapped[str] = mapped_column(String(32), index=True)
  slug: Mapped[str] = mapped_column(String(32), default="latest")
  source: Mapped[str] = mapped_column(String(80), default="data_go_kr")
  meta: Mapped[dict] = mapped_column(JSON, default=dict)
  api_meta: Mapped[dict] = mapped_column(JSON, default=dict)
  items: Mapped[list] = mapped_column(JSON, default=list)
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
