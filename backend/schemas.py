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
    reference_price: Decimal = Field(gt=0)
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

from datetime import datetime

class OfferPublic(BaseModel):
    seller_name: str
    price: Decimal
    base_price: Decimal
    delivery_days: int
    warranty_months: int
    addons: list[str]
    status: str
    utility_score: float | None


class RoundPublic(BaseModel):
    round_number: int
    offers: list[OfferPublic]


class NegotiationPublic(BaseModel):
    id: int

    product: str
    budget: Decimal
    max_delivery_days: int

    price_weight: float
    delivery_weight: float
    warranty_weight: float

    status: str

    winner_seller_name: str | None
    final_price: Decimal | None

    created_at: datetime

    rounds: list[RoundPublic]

class NegotiationStartResponse(BaseModel):
    negotiation_id: int
    status: Literal["RUNNING"]