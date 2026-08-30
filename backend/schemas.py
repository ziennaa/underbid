"""Public request/response schemas for the UNDERBID Phase 3 API.

Only API-facing fields belong here. Seller private economics are deliberately
absent from these models so FastAPI cannot serialize them through this schema.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class NegotiationCreate(BaseModel):
    product: str = Field(min_length=1)
    budget: Decimal = Field(gt=0)
    max_delivery_days: int = Field(gt=0)
    price_weight: float = Field(ge=0.0, le=1.0)
    delivery_weight: float = Field(ge=0.0, le=1.0)
    warranty_weight: float = Field(ge=0.0, le=1.0)
    randomize_sellers: bool = False
    seed: int | None = None


class NegotiationCreatedResponse(BaseModel):
    negotiation_id: int
    status: Literal["CREATED"]
