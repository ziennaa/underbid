"""Pure scoring functions for UNDERBID Phase 1.

These functions know nothing about sellers, rounds, or negotiation state.
They only turn offer attributes into normalized [0, 1] scores.
"""

from __future__ import annotations

from decimal import Decimal

WARRANTY_BENCHMARK_MONTHS = 24


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def price_score(price: Decimal, budget: Decimal) -> float:
    """Score affordability from 0 to 1 for a price already known to be valid.

    A free offer scores 1.0; an offer exactly at the hard budget scores 0.0.
    Offers above budget are treated as invalid by buyer.py and should not be
    rescued by this soft score.
    """
    if budget <= 0:
        raise ValueError("budget must be positive")
    return _clamp01(1.0 - float(price / budget))


def delivery_score(delivery_days: int, max_delivery_days: int) -> float:
    """Score faster delivery from 0 to 1 inside the allowed delivery window.

    One-day delivery scores 1.0. Delivery exactly at the buyer's maximum
    scores 0.0. The max=1 case is handled explicitly to avoid division by zero.
    """
    if delivery_days <= 0 or max_delivery_days <= 0:
        raise ValueError("delivery days must be positive")
    if max_delivery_days == 1:
        return 1.0 if delivery_days == 1 else 0.0
    return _clamp01(
        1.0 - (delivery_days - 1) / (max_delivery_days - 1)
    )


def warranty_score(
    warranty_months: int,
    benchmark_months: int = WARRANTY_BENCHMARK_MONTHS,
) -> float:
    """Score warranty length against a fixed benchmark.

    0 months -> 0.0, benchmark_months or more -> 1.0. A fixed benchmark keeps
    scores comparable across sellers and simulations.
    """
    if warranty_months < 0:
        raise ValueError("warranty_months cannot be negative")
    if benchmark_months <= 0:
        raise ValueError("benchmark_months must be positive")
    return _clamp01(warranty_months / benchmark_months)
