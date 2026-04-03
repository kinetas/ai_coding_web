from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from backend.app.models.types import Category, Region


class Word(BaseModel):
  text: str = Field(min_length=1, max_length=64)
  weight: float = Field(ge=0)


class WordcloudResponse(BaseModel):
  category: Category
  region: Region
  generated_at: str
  words: List[Word]


class IngestWordcloudPayload(BaseModel):
  category: Category
  region: Region
  words: List[Word]

