"""Public request/response schemas for the UNDERBID Phase 3 API.

Only API-facing fields belong here. Seller private economics are deliberately
absent from these models so FastAPI cannot serialize them through this schema.
"""

from __future__ import annotations

import random
from decimal import Decimal

from negotiation.engine import default_sellers
from negotiation.seller import DeliveryOption, Seller, SellerConfig, money


def randomized_sellers(seed: int | None = None) -> list[Seller]:
    rng = random.Random(seed)

    sellers: list[Seller] = []

    personalities = [
        ("SELLER A", "aggressive", (0.04, 0.09), 4, [6, 12]),
        ("SELLER B", "accommodating", (0.10, 0.19), 5, [6, 12, 18]),
        ("SELLER C", "value", (0.025, 0.07), 3, [12, 18, 24]),
    ]

    for name, strategy, rate_range, days, warranties in personalities:
        cost = rng.randint(15000, 22000)
        floor = cost + rng.randint(700, 4500)
        opening = floor + rng.randint(1800, 9000)

        rate = Decimal(
            str(round(rng.uniform(*rate_range), 4))
        )

        config = SellerConfig(
            name=name,
            cost_price=money(cost),
            opening_price=money(opening),
            floor_price=money(floor),
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
                    price_delta=money(
                        rng.randint(250, 950)
                    ),
                ),
            ],

            warranty_options=list(warranties),

            addon_costs={
                "setup": money(
                    rng.randint(150, 450)
                ),
                "support": money(
                    rng.randint(250, 700)
                ),
            },

            strategy=strategy,
        )

        sellers.append(Seller(config))

    return sellers


def make_sellers(
    randomize_sellers: bool,
    seed: int | None = None,
) -> list[Seller]:

    if randomize_sellers:
        return randomized_sellers(seed)

    return default_sellers()