from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BuilderSuggestion(BaseModel):
  id: str = Field(min_length=1, max_length=40)
  label: str = Field(min_length=1, max_length=40)
  description: str = Field(default="")


class BuilderSuggestionsResponse(BaseModel):
  keyword: str
  suggestions: List[BuilderSuggestion]


class BuilderMetricResponse(BaseModel):
  keyword: str
  metric: str
  metric_label: str
  line: List[float]
  bar: List[float]
  accents: dict = Field(default_factory=dict)


class BuilderChatPayload(BaseModel):
  keyword: str = Field(default="")
  question: str = Field(min_length=1, max_length=400)


class BuilderChatResponse(BaseModel):
  answer: str


class SaveBuilderAnalysisPayload(BaseModel):
  title: str = Field(min_length=1, max_length=80)
  keyword: str = Field(min_length=1, max_length=80)
  metric: str = Field(min_length=1, max_length=40)
  metric_label: str = Field(default="")


class SavedBuilderAnalysis(BaseModel):
  id: str
  user: str
  title: str
  keyword: str
  metric: str
  metric_label: str
  saved_at: str


class SavedBuilderAnalysesResponse(BaseModel):
  user: str
  items: List[SavedBuilderAnalysis]

