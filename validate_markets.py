from __future__ import annotations

import inspect
import random
import statistics
from collections import Counter
from decimal import Decimal

from backend.seller_factory import make_sellers
from negotiation.buyer import BuyerRequest
from negotiation.engine import run_negotiation
from negotiation.seller import money


SIMULATIONS = 1000
MASTER_SEED = 20260904

# Known-valid deterministic tactics from the test suite.
# This avoids making thousands of external LLM calls while
# still exercising tactic-aware engine behavior when supported.
FIXED_TACTICS = {
    "SELLER A": "CONCEDE_PRICE",
    "SELLER B": "IMPROVE_TERMS",
    "SELLER C": "ADD_VALUE",
}

WEIGHT_PROFILES = [
    (0.60, 0.25, 0.15),
    (0.43, 0.44, 0.13),
    (0.70, 0.15, 0.15),
    (0.35, 0.25, 0.40),
    (0.50, 0.20, 0.30),
]


def percentile(values: list[int], p: float) -> int:
    ordered = sorted(values)

    index = max(
        0,
        min(
            len(ordered) - 1,
            int((len(ordered) - 1) * p),
        ),
    )

    return ordered[index]


def main() -> None:
    rng = random.Random(MASTER_SEED)

    agreements = 0
    no_deals = 0

    winner_counts: Counter[str] = Counter()
    no_deal_reasons: Counter[str] = Counter()

    winning_prices: set[Decimal] = set()
    terminal_rounds: list[int] = []
    final_price_ratios: list[float] = []

    config_violations = 0
    floor_violations = 0
    budget_violations = 0
    delivery_violations = 0
    invalid_winner_violations = 0
    no_deal_valid_offer_violations = 0
    round_violations = 0

    engine_parameters = inspect.signature(
        run_negotiation
    ).parameters

    tactic_aware = (
        "seller_tactics" in engine_parameters
    )

    for seed in range(SIMULATIONS):
        # Test products across very different price scales.
        reference_price = money(
            rng.randint(10_000, 100_000)
        )

        # Intentionally include impossible, competitive,
        # and easy buyer budgets.
        budget_ratio = Decimal(
            str(
                round(
                    rng.uniform(0.60, 1.20),
                    4,
                )
            )
        )

        budget = money(
            reference_price * budget_ratio
        )

        max_delivery_days = rng.choice(
            [1, 2, 3, 4, 5, 7]
        )

        (
            price_weight,
            delivery_weight,
            warranty_weight,
        ) = WEIGHT_PROFILES[
            seed % len(WEIGHT_PROFILES)
        ]

        buyer = BuyerRequest(
            product=f"Synthetic Product {seed}",
            budget=budget,
            max_delivery_days=max_delivery_days,
            price_weight=price_weight,
            delivery_weight=delivery_weight,
            warranty_weight=warranty_weight,
        )

        sellers = make_sellers(
            randomize_sellers=True,
            reference_price=reference_price,
            seed=seed,
        )

        # ---------------------------------
        # PRIVATE ECONOMIC CONFIG CHECKS
        # ---------------------------------

        for seller in sellers:
            config = seller.config

            if not (
                config.cost_price
                < config.floor_price
                < config.opening_price
            ):
                config_violations += 1

        # ---------------------------------
        # RUN NEGOTIATION
        # ---------------------------------

        run_kwargs = {}

        if tactic_aware:
            run_kwargs["seller_tactics"] = (
                FIXED_TACTICS
            )

        result = run_negotiation(
            buyer,
            sellers,
            **run_kwargs,
        )

        terminal_rounds.append(
            len(result.rounds)
        )

        if not 1 <= len(result.rounds) <= 5:
            round_violations += 1

        # ---------------------------------
        # EVERY OFFER MUST RESPECT FLOOR
        # ---------------------------------

        for record in result.rounds:
            for seller_name, offer in (
                record.offers.items()
            ):
                config = result.seller_configs[
                    seller_name
                ]

                if (
                    offer.base_price
                    < config.floor_price
                ):
                    floor_violations += 1

        # ---------------------------------
        # TERMINAL RESULT CHECKS
        # ---------------------------------

        if result.winner is not None:
            agreements += 1

            winner = result.winner

            winner_counts[
                winner.seller_name
            ] += 1

            winning_prices.add(
                winner.price
            )

            final_price_ratios.append(
                float(
                    winner.price
                    / reference_price
                )
            )

            if winner.price > buyer.budget:
                budget_violations += 1

            if (
                winner.delivery_days
                > buyer.max_delivery_days
            ):
                delivery_violations += 1

            terminal_utility = (
                result.rounds[-1].utilities.get(
                    winner.seller_name
                )
            )
            
            if terminal_utility is None:
                invalid_winner_violations += 1
            
            if result.winning_utility is None:
                invalid_winner_violations += 1
            
            if winner.status != "ACCEPTED":
                invalid_winner_violations += 1

        else:
            no_deals += 1

            no_deal_reasons[
                result.reason
            ] += 1

            # If a valid offer existed, the engine should
            # have accepted a winner in that round.
            valid_offer_existed = any(
                utility is not None
                for record in result.rounds
                for utility in (
                    record.utilities.values()
                )
            )

            if valid_offer_existed:
                no_deal_valid_offer_violations += 1

    # =====================================
    # REPORT
    # =====================================

    total_violations = sum(
        [
            config_violations,
            floor_violations,
            budget_violations,
            delivery_violations,
            invalid_winner_violations,
            no_deal_valid_offer_violations,
            round_violations,
        ]
    )

    print()
    print("=" * 58)
    print("UNDERBID — 1,000 MARKET VALIDATION")
    print("=" * 58)

    print()
    print("SIMULATION COVERAGE")
    print(f"Markets tested:             {SIMULATIONS}")
    print(f"Agreements:                 {agreements}")
    print(f"No-deal outcomes:           {no_deals}")
    print(
        f"Deal rate:                  "
        f"{agreements / SIMULATIONS * 100:.1f}%"
    )
    print(
        f"No-deal rate:               "
        f"{no_deals / SIMULATIONS * 100:.1f}%"
    )

    print()
    print("WINNER DIVERSITY")

    for seller_name in [
        "SELLER A",
        "SELLER B",
        "SELLER C",
    ]:
        wins = winner_counts[seller_name]

        share = (
            wins / agreements * 100
            if agreements
            else 0
        )

        print(
            f"{seller_name}:"
            f"{wins:>8} wins "
            f"({share:.1f}% of deals)"
        )

    print(
        f"Seller win coverage:        "
        f"{len(winner_counts)}/3"
    )

    print(
        f"Distinct winning prices:    "
        f"{len(winning_prices)}"
    )

    print()
    print("NEGOTIATION DEPTH")

    print(
        f"Average terminal round:     "
        f"{statistics.mean(terminal_rounds):.2f}"
    )

    print(
        f"Median terminal round:      "
        f"{statistics.median(terminal_rounds):.1f}"
    )

    print(
        f"P95 terminal round:         "
        f"{percentile(terminal_rounds, 0.95)}"
    )

    if final_price_ratios:
        print()
        print("MARKET-ANCHOR BEHAVIOR")

        print(
            f"Median final/reference:     "
            f"{statistics.median(final_price_ratios) * 100:.1f}%"
        )

    print()
    print("NO-DEAL REASONS")

    if no_deal_reasons:
        for reason, count in sorted(
            no_deal_reasons.items()
        ):
            print(
                f"{reason:<26}{count}"
            )
    else:
        print("None")

    print()
    print("ECONOMIC INVARIANTS")

    print(
        f"Invalid seller configs:     "
        f"{config_violations}"
    )

    print(
        f"Seller-floor violations:    "
        f"{floor_violations}"
    )

    print(
        f"Buyer-budget violations:    "
        f"{budget_violations}"
    )

    print(
        f"Delivery violations:        "
        f"{delivery_violations}"
    )

    print(
        f"Invalid winner states:      "
        f"{invalid_winner_violations}"
    )

    print(
        f"No-deal w/ valid offer:     "
        f"{no_deal_valid_offer_violations}"
    )

    print(
        f"Round-bound violations:     "
        f"{round_violations}"
    )

    print("------------------------------------------")
    print(
        f"TOTAL INVARIANT VIOLATIONS: "
        f"{total_violations}"
    )

    print()
    print(
        "Tactic-aware engine:        "
        + ("YES" if tactic_aware else "NO")
    )

    print()

    if total_violations == 0:
        print(
            "VALIDATION RESULT: PASS ✅"
        )
    else:
        print(
            "VALIDATION RESULT: FAIL ❌"
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()