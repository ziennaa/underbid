"""100-run invariant validation for UNDERBID Phase 1.

Randomness exists only in generated inputs. Given the same generated inputs,
the negotiation engine itself is deterministic.
"""

from __future__ import annotations

import random
from decimal import Decimal

try:
    from .buyer import BuyerRequest
    from .engine import run_negotiation
    from .seller import DeliveryOption, Seller, SellerConfig, money
except ImportError:  # allows: python negotiation/validate.py
    from buyer import BuyerRequest
    from engine import run_negotiation
    from seller import DeliveryOption, Seller, SellerConfig, money


def _weights(rng: random.Random) -> tuple[float, float, float]:
    raw = [rng.uniform(0.1, 1.0) for _ in range(3)]
    total = sum(raw)
    # Construct the third as the remainder so Pydantic sees a sum of exactly
    # 1.0 to normal floating-point tolerance.
    p = raw[0] / total
    d = raw[1] / total
    w = 1.0 - p - d
    return p, d, w


def _random_sellers(rng: random.Random) -> list[Seller]:
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
        rate = Decimal(str(round(rng.uniform(*rate_range), 4)))

        config = SellerConfig(
            name=name,
            cost_price=money(cost),
            opening_price=money(opening),
            floor_price=money(floor),
            concession_rate=rate,
            delivery_options=[
                DeliveryOption(label="standard", days=days, price_delta=money(0)),
                DeliveryOption(
                    label="express",
                    days=max(1, days - 2),
                    price_delta=money(rng.randint(250, 950)),
                ),
            ],
            warranty_options=warranties,
            addon_costs={
                "setup": money(rng.randint(150, 450)),
                "support": money(rng.randint(250, 700)),
            },
            strategy=strategy,
        )
        sellers.append(Seller(config))
    return sellers


def run_validation(simulations: int = 100, seed: int = 20260828) -> None:
    rng = random.Random(seed)
    outcomes: list[tuple[str, Decimal] | tuple[str, None]] = []
    no_deals = 0

    for index in range(simulations):
        sellers = _random_sellers(rng)
        floors = [seller.config.floor_price for seller in sellers]

        # Randomized budgets deliberately span both feasible and infeasible
        # regions. This tests graceful failure instead of testing only happy paths.
        if rng.random() < 0.22:
            budget = money(rng.randint(12000, int(min(floors)) - 100))
        else:
            low = max(16000, int(min(floors)) - 1000)
            high = int(max(s.config.opening_price for s in sellers)) + 1500
            budget = money(rng.randint(low, high))

        pw, dw, ww = _weights(rng)
        buyer = BuyerRequest(
            product=f"Random Product {index}",
            budget=budget,
            max_delivery_days=rng.randint(3, 6),
            price_weight=pw,
            delivery_weight=dw,
            warranty_weight=ww,
        )

        result = run_negotiation(buyer, sellers)

        # Stronger than the requested accepted-price check: every quoted ACTIVE
        # price in every round must respect that seller's floor.
        for record in result.rounds:
            for seller_name, offer in record.offers.items():
                floor = result.seller_configs[seller_name].floor_price
                if offer.status != "WALK_AWAY":
                    assert offer.price >= floor, (
                        f"simulation {index}: {seller_name} quoted {offer.price} below floor {floor}"
                    )

        if result.winner is None:
            no_deals += 1
            outcomes.append(("NO DEAL", None))
            continue

        winner = result.winner
        config = result.seller_configs[winner.seller_name]

        assert winner.price >= config.floor_price, (
            f"simulation {index}: accepted {winner.price} below floor {config.floor_price}"
        )
        assert winner.price <= buyer.budget, (
            f"simulation {index}: accepted {winner.price} above budget {buyer.budget}"
        )
        assert winner.delivery_days <= buyer.max_delivery_days, (
            f"simulation {index}: accepted delivery violates hard constraint"
        )
        outcomes.append((winner.seller_name, winner.price))

    winner_names = {name for name, price in outcomes if price is not None}
    winning_prices = {price for _, price in outcomes if price is not None}

    assert len(winner_names) >= 2, f"winner did not vary enough: {winner_names}"
    assert len(winning_prices) >= 5, "winning prices did not vary enough"
    assert no_deals > 0, "expected some NO DEAL outcomes"

    print(f"PASS: {simulations} simulations")
    print(f"Distinct winners: {sorted(winner_names)}")
    print(f"Distinct winning prices: {len(winning_prices)}")
    print(f"NO DEAL runs: {no_deals}")


if __name__ == "__main__":
    run_validation()