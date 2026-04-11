from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CreateAlertPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    item_name: str = Field(min_length=1, max_length=80)
    condition: str = Field(pattern="^(above|below)$")
    threshold: float = Field(gt=0)


class AlertItem(BaseModel):
    id: int
    name: str
    item_name: str
    condition: str
    threshold: float
    active: bool
    created_at: str
    current_price: Optional[float] = None
    triggered: Optional[bool] = None


class AlertListResponse(BaseModel):
    items: List[AlertItem]


class AlertCheckResponse(BaseModel):
    items: List[AlertItem]
    survey_date: str = ""
