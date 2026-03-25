from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


class User(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  supabase_uid: Mapped[str | None] = mapped_column(String(36), unique=True, index=True, nullable=True)
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
  title: Mapped[str] = mapped_column(String(80))
  keyword: Mapped[str] = mapped_column(String(80), index=True)
  metric: Mapped[str] = mapped_column(String(40))
  metric_label: Mapped[str] = mapped_column(String(80))
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

  user: Mapped[User] = relationship()


class EtlRun(Base):
  __tablename__ = "etl_runs"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  source: Mapped[str] = mapped_column(String(80), index=True)
  status: Mapped[str] = mapped_column(String(20), index=True)
  details: Mapped[str] = mapped_column(Text, default="")
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
