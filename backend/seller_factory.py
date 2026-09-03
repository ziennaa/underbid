"""Generate private synthetic seller economics for UNDERBID.

Seller economics are anchored to the buyer-provided typical retail price.
They are deliberately NOT derived from the buyer's hard budget.
"""

from __future__ import annotations

import random
from decimal import Decimal

from negotiation.seller import (
    DeliveryOption,
    Seller,
    SellerConfig,
    money,
)


DEFAULT_MARKET_SEED = 2026


def _ratio(
    rng: random.Random,
    low: float,
    high: float,
) -> Decimal:
    return Decimal(
        str(round(rng.uniform(low, high), 4))
    )


def _scaled(
    reference_price: Decimal,
    ratio: Decimal,
) -> Decimal:
    return money(reference_price * ratio)


def randomized_sellers(
    reference_price: Decimal,
    seed: int | None = None,
) -> list[Seller]:
    if reference_price <= 0:
        raise ValueError(
            "reference_price must be positive"
        )

    rng = random.Random(seed)

    sellers: list[Seller] = []

    # Each personality gets a different economic profile.
    #
    # Ratios are relative to the typical retail price,
    # NOT the buyer's maximum budget.
    personalities = [
        {
            "name": "SELLER A",
            "strategy": "aggressive",
            "cost_range": (0.68, 0.76),
            "floor_range": (0.80, 0.88),
            "opening_range": (0.98, 1.08),
            "rate_range": (0.04, 0.09),
            "days": 4,
            "warranties": [6, 12],
        },
        {
            "name": "SELLER B",
            "strategy": "accommodating",
            "cost_range": (0.70, 0.79),
            "floor_range": (0.82, 0.90),
            "opening_range": (0.99, 1.10),
            "rate_range": (0.10, 0.19),
            "days": 5,
            "warranties": [6, 12, 18],
        },
        {
            "name": "SELLER C",
            "strategy": "value",
            "cost_range": (0.72, 0.81),
            "floor_range": (0.85, 0.93),
            "opening_range": (1.01, 1.14),
            "rate_range": (0.025, 0.07),
            "days": 3,
            "warranties": [12, 18, 24],
        },
    ]

    for personality in personalities:
        cost_ratio = _ratio(
            rng,
            *personality["cost_range"],
        )

        floor_ratio = _ratio(
            rng,
            *personality["floor_range"],
        )

        # Defensive invariant:
        # floor must remain above seller cost.
        floor_ratio = max(
            floor_ratio,
            cost_ratio + Decimal("0.04"),
        )

        opening_ratio = _ratio(
            rng,
            *personality["opening_range"],
        )

        # Opening price must stay meaningfully
        # above the private floor.
        opening_ratio = max(
            opening_ratio,
            floor_ratio + Decimal("0.05"),
        )

        cost = _scaled(
            reference_price,
            cost_ratio,
        )

        floor = _scaled(
            reference_price,
            floor_ratio,
        )

        opening = _scaled(
            reference_price,
            opening_ratio,
        )

        rate = _ratio(
            rng,
            *personality["rate_range"],
        )

        express_delta = _scaled(
            reference_price,
            _ratio(rng, 0.005, 0.018),
        )

        setup_cost = _scaled(
            reference_price,
            _ratio(rng, 0.003, 0.009),
        )

        support_cost = _scaled(
            reference_price,
            _ratio(rng, 0.005, 0.014),
        )

        days = personality["days"]

        config = SellerConfig(
            name=personality["name"],
            cost_price=cost,
            opening_price=opening,
            floor_price=floor,
            concession_rate=rate,
            delivery_options=[
                DeliveryOption(
                    label="standard",
                    days=days,
                    price_delta=money(0),
                ),
                DeliveryOption(
                    label="express",
                    days=max(1, days - 2),
                    price_delta=express_delta,
                ),
            ],
            warranty_options=list(
                personality["warranties"]
            ),
            addon_costs={
                "setup": setup_cost,
                "support": support_cost,
            },
            strategy=personality["strategy"],
        )

        sellers.append(Seller(config))

    return sellers


def make_sellers(
    randomize_sellers: bool,
    reference_price: Decimal,
    seed: int | None = None,
) -> list[Seller]:
    effective_seed = (
        seed
        if randomize_sellers
        else DEFAULT_MARKET_SEED
    )

    return randomized_sellers(
        reference_price=reference_price,
        seed=effective_seed,
    )