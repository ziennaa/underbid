"""Buyer-side hard constraints and utility scoring for UNDERBID Phase 1."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

try:
    from .utility import delivery_score, price_score, warranty_score
except ImportError:  # allows: python negotiation/engine.py
    from utility import delivery_score, price_score, warranty_score

if TYPE_CHECKING:
    try:
        from .seller import Offer
    except ImportError:
        from seller import Offer


class BuyerRequest(BaseModel):
    product: str
    budget: Decimal = Field(gt=0)
    max_delivery_days: int = Field(gt=0)
    price_weight: float = Field(ge=0.0, le=1.0)
    delivery_weight: float = Field(ge=0.0, le=1.0)
    warranty_weight: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "BuyerRequest":
        total = self.price_weight + self.delivery_weight + self.warranty_weight
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"buyer weights must sum to 1.0, got {total}")
        return self

    def violates_hard_constraints(self, offer: "Offer") -> bool:
        return (
            offer.status != "ACTIVE"
            or offer.price > self.budget
            or offer.delivery_days > self.max_delivery_days
        )

    def utility(self, offer: "Offer") -> float | None:
        """Return 0..1 utility, or None when a hard constraint is violated."""
        if self.violates_hard_constraints(offer):
            return None

        p = price_score(offer.price, self.budget)
        d = delivery_score(offer.delivery_days, self.max_delivery_days)
        w = warranty_score(offer.warranty_months)

        score = (
            self.price_weight * p
            + self.delivery_weight * d
            + self.warranty_weight * w
        )
        return max(0.0, min(1.0, score))
