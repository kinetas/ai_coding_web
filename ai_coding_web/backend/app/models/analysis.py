from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from backend.app.models.types import Page


class Accents(BaseModel):
  line: str = Field(default="#6AE4FF")
  bar: str = Field(default="#B79BFF")


class AnalysisResponse(BaseModel):
  page: Page
  generated_at: str
  line: List[float]
  bar: List[float]
  donut: List[float]
  accents: Accents


class IngestAnalysisPayload(BaseModel):
  page: Page
  line: List[float]
  bar: List[float]
  donut: List[float]
  accents: Optional[Accents] = None

