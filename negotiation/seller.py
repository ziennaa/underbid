"""Seller economics for UNDERBID Phase 1.

A seller's money decisions are fully formula-driven. There is no random choice
or model-generated pricing inside Seller.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, Field, model_validator

CENT = Decimal("0.01")
MAX_ROUNDS = 5
COMPETITIVE_PRESSURE_CAP = Decimal("0.12")
ROUND_PRESSURE_CAP = Decimal("0.10")
SellerTactic = Literal[
    "HOLD",
    "CONCEDE_PRICE",
    "ADD_VALUE",
    "IMPROVE_TERMS",
]

TACTIC_CONCESSION_BOOST = Decimal("0.08")

def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


class DeliveryOption(BaseModel):
    label: str
    days: int = Field(gt=0)
    price_delta: Decimal = Field(ge=0)


class SellerConfig(BaseModel):
    name: str
    cost_price: Decimal = Field(gt=0)
    opening_price: Decimal = Field(gt=0)
    floor_price: Decimal = Field(gt=0)
    concession_rate: Decimal = Field(gt=0, le=Decimal("0.50"))
    delivery_options: list[DeliveryOption]
    warranty_options: list[int]
    addon_costs: dict[str, Decimal] = Field(default_factory=dict)
    strategy: Literal["aggressive", "accommodating", "value"]

    @model_validator(mode="after")
    def validate_economics(self) -> "SellerConfig":
        if self.floor_price < self.cost_price:
            raise ValueError("floor_price cannot be below cost_price")
        if self.opening_price < self.floor_price:
            raise ValueError("opening_price cannot be below floor_price")
        if not self.delivery_options:
            raise ValueError("at least one delivery option is required")
        if not self.warranty_options:
            raise ValueError("at least one warranty option is required")
        if any(months < 0 for months in self.warranty_options):
            raise ValueError("warranty months cannot be negative")
        if any(cost < 0 for cost in self.addon_costs.values()):
            raise ValueError("addon costs cannot be negative")
        return self


class Offer(BaseModel):
    seller_name: str
    round_number: int
    price: Decimal
    base_price: Decimal
    delivery_days: int
    warranty_months: int
    addons: tuple[str, ...] = ()
    status: Literal["ACTIVE", "WALK_AWAY", "ACCEPTED"] = "ACTIVE"


class Seller:
    """A deterministic seller with a fixed pricing policy."""

    def __init__(self, config: SellerConfig):
        self.config = config

    def _delivery_option(
        self,
        tactic: SellerTactic | None = None,
    ) -> DeliveryOption:
        if tactic == "IMPROVE_TERMS":
            return min(
                self.config.delivery_options,
                key=lambda option: (
                    option.days,
                    option.price_delta,
                    option.label,
                ),
            )

        return min(
            self.config.delivery_options,
            key=lambda option: (
                option.price_delta,
                option.days,
                option.label,
            ),
        )

    def _warranty_months(
        self,
        current_round: int,
        tactic: SellerTactic | None = None,
    ) -> int:
        options = sorted(self.config.warranty_options)

        if tactic in {"ADD_VALUE", "IMPROVE_TERMS"}:
            return options[-1]

        if self.config.strategy == "value":
            index = min(
                (current_round - 1) // 2,
                len(options) - 1,
            )
            return options[index]

        if self.config.strategy == "accommodating":
            index = min(
                (current_round - 1) // 3,
                len(options) - 1,
            )
            return options[index]

        return options[0]

    def _addons(
    self,
    current_round: int,
    base_price: Decimal,
    tactic: SellerTactic | None = None,
) -> tuple[str, ...]:
        wants_addons = (
    self.config.strategy == "value"
    or tactic == "ADD_VALUE"
)

        if not wants_addons or current_round < 2:
            return ()

        # Add-ons are included at no extra buyer price, but only if the seller's
        # current gross margin can economically absorb their configured cost.
        margin = max(Decimal("0"), base_price - self.config.cost_price)
        chosen: list[str] = []
        spent = Decimal("0")
        allowed_count = current_round - 1

        for name, cost in sorted(self.config.addon_costs.items(), key=lambda x: (x[1], x[0])):
            if len(chosen) >= allowed_count:
                break
            if spent + cost <= margin:
                chosen.append(name)
                spent += cost
        return tuple(chosen)

    def _competitive_pressure(
        self,
        last_offer: Offer,
        best_competing_offer: Offer | None,
    ) -> Decimal:
        if best_competing_offer is None or best_competing_offer.status != "ACTIVE":
            return Decimal("0")
        if best_competing_offer.price >= last_offer.price:
            return Decimal("0")

        undercut_fraction = (
            (last_offer.price - best_competing_offer.price) / last_offer.price
        )
        return min(COMPETITIVE_PRESSURE_CAP, undercut_fraction)

    def _round_pressure(self, current_round: int) -> Decimal:
        # Round 1 has zero deadline pressure; round 5 reaches the cap.
        if current_round <= 1:
            return Decimal("0")
        progress = Decimal(current_round - 1) / Decimal(MAX_ROUNDS - 1)
        return ROUND_PRESSURE_CAP * progress

    def compute_next_offer(
        self,
        current_round: int,
        last_offer: Offer | None,
        best_competing_offer: Offer | None,
        tactic: SellerTactic | None = None,
    ) -> Offer:
        if not 1 <= current_round <= MAX_ROUNDS:
            raise ValueError(f"current_round must be in 1..{MAX_ROUNDS}")

        delivery = self._delivery_option(tactic)

        if current_round == 1:
            base_price = money(self.config.opening_price)
        else:
            if last_offer is None:
                raise ValueError("last_offer is required after round 1")
            if last_offer.status == "WALK_AWAY":
                return last_offer.model_copy(update={"round_number": current_round})

            # A seller that already exposed its floor and was not accepted has
            # no legal room left to concede, so it walks away next round.
            if last_offer.base_price <= money(self.config.floor_price):
                return Offer(
                    seller_name=self.config.name,
                    round_number=current_round,
                    price=last_offer.price,
                    base_price=last_offer.base_price,
                    delivery_days=last_offer.delivery_days,
                    warranty_months=last_offer.warranty_months,
                    addons=last_offer.addons,
                    status="WALK_AWAY",
                )

            total_spread = self.config.opening_price - self.config.floor_price
            competitive = self._competitive_pressure(last_offer, best_competing_offer)
            deadline = self._round_pressure(current_round)
            if tactic == "HOLD":
                effective_rate = Decimal("0")
            else:
                effective_rate = (
                    self.config.concession_rate
                    + competitive
                    + deadline
                )  

                if tactic == "CONCEDE_PRICE":
                    effective_rate += TACTIC_CONCESSION_BOOST

            # Concession is a fraction of the ORIGINAL negotiable spread, not
            # a guessed amount. This allows the seller to actually reach floor.
            concession_amount = total_spread * effective_rate
            base_price = money(
                max(self.config.floor_price, last_offer.base_price - concession_amount)
            )

        final_price = money(max(self.config.floor_price, base_price + delivery.price_delta))
        return Offer(
            seller_name=self.config.name,
            round_number=current_round,
            price=final_price,
            base_price=base_price,
            delivery_days=delivery.days,
            warranty_months=self._warranty_months(
                current_round,
                tactic,
            ),
            addons=self._addons(
                current_round,
                base_price,
                tactic,
            ),
            status="ACTIVE",
        )
