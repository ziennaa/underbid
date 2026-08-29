"""SQLModel persistence models for UNDERBID Phase 3.

These classes describe database rows only. Public API schemas are intentionally
kept out of this module and will be added in a later checkpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Column, JSON, Numeric
from sqlmodel import Field, SQLModel


MONEY_TYPE = Numeric(18, 2, asdecimal=True)
RATE_TYPE = Numeric(10, 6, asdecimal=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NegotiationDB(SQLModel, table=True):
    __tablename__ = "negotiations"

    id: int | None = Field(default=None, primary_key=True)
    product: str
    budget: Decimal = Field(sa_column=Column(MONEY_TYPE, nullable=False))
    max_delivery_days: int
    price_weight: float
    delivery_weight: float
    warranty_weight: float
    status: str = Field(default="CREATED", index=True)
    winner_seller_name: str | None = None
    final_price: Decimal | None = Field(
        default=None,
        sa_column=Column(MONEY_TYPE, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class SellerPrivateConfigDB(SQLModel, table=True):
    __tablename__ = "seller_private_configs"

    id: int | None = Field(default=None, primary_key=True)
    negotiation_id: int = Field(foreign_key="negotiations.id", index=True)
    seller_name: str = Field(index=True)
    cost_price: Decimal = Field(sa_column=Column(MONEY_TYPE, nullable=False))
    opening_price: Decimal = Field(sa_column=Column(MONEY_TYPE, nullable=False))
    floor_price: Decimal = Field(sa_column=Column(MONEY_TYPE, nullable=False))
    concession_rate: Decimal = Field(sa_column=Column(RATE_TYPE, nullable=False))
    strategy: str


class OfferDB(SQLModel, table=True):
    __tablename__ = "offers"

    id: int | None = Field(default=None, primary_key=True)
    negotiation_id: int = Field(foreign_key="negotiations.id", index=True)
    seller_name: str = Field(index=True)
    round_number: int = Field(index=True)
    price: Decimal = Field(sa_column=Column(MONEY_TYPE, nullable=False))
    base_price: Decimal = Field(sa_column=Column(MONEY_TYPE, nullable=False))
    delivery_days: int
    warranty_months: int
    addons: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    status: str
    utility_score: float | None = None
    timestamp: datetime = Field(default_factory=utc_now, nullable=False)


class EventDB(SQLModel, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    negotiation_id: int = Field(foreign_key="negotiations.id", index=True)
    event_type: str = Field(index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    timestamp: datetime = Field(default_factory=utc_now, nullable=False)
