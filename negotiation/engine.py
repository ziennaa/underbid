"""Negotiation loop and terminal demo for UNDERBID Phase 1."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

try:
    from .buyer import BuyerRequest
    from .seller import DeliveryOption, MAX_ROUNDS, Offer, Seller, SellerConfig, money
except ImportError:  # allows: python negotiation/engine.py
    from buyer import BuyerRequest
    from seller import DeliveryOption, MAX_ROUNDS, Offer, Seller, SellerConfig, money


@dataclass(frozen=True)
class RoundRecord:
    round_number: int
    offers: dict[str, Offer]
    utilities: dict[str, float | None]


@dataclass(frozen=True)
class NegotiationResult:
    buyer: BuyerRequest
    rounds: list[RoundRecord]
    seller_configs: dict[str, SellerConfig]
    winner: Offer | None
    winning_utility: float | None
    reason: str


def _best_competitor_for(
    seller_name: str,
    previous_offers: dict[str, Offer],
) -> Offer | None:
    candidates = [
        offer
        for name, offer in previous_offers.items()
        if name != seller_name and offer.status == "ACTIVE"
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda offer: (offer.price, offer.seller_name))


def _pick_best_valid_offer(
    buyer: BuyerRequest,
    offers: dict[str, Offer],
) -> tuple[Offer | None, float | None, dict[str, float | None]]:
    utilities = {name: buyer.utility(offer) for name, offer in offers.items()}
    valid = [
        (offer, utilities[name])
        for name, offer in offers.items()
        if utilities[name] is not None
    ]
    if not valid:
        return None, None, utilities

    # Deterministic tie-break order:
    # 1) higher weighted utility, 2) lower price, 3) faster delivery,
    # 4) longer warranty, 5) seller name.
    winner, score = sorted(
        valid,
        key=lambda item: (
            -item[1],
            item[0].price,
            item[0].delivery_days,
            -item[0].warranty_months,
            item[0].seller_name,
        ),
    )[0]
    return winner, score, utilities


def run_negotiation(
    buyer: BuyerRequest,
    sellers: list[Seller],
    max_rounds: int = MAX_ROUNDS,
) -> NegotiationResult:
    if not sellers:
        raise ValueError("at least one seller is required")
    if not 1 <= max_rounds <= MAX_ROUNDS:
        raise ValueError(f"max_rounds must be in 1..{MAX_ROUNDS}")

    previous_offers: dict[str, Offer] = {}
    records: list[RoundRecord] = []
    configs = {seller.config.name: seller.config for seller in sellers}

    for round_number in range(1, max_rounds + 1):
        current_offers: dict[str, Offer] = {}

        # Simultaneous round: each seller sees only the completed prior round.
        for seller in sellers:
            last_offer = previous_offers.get(seller.config.name)
            competitor = _best_competitor_for(seller.config.name, previous_offers)
            current_offers[seller.config.name] = seller.compute_next_offer(
                current_round=round_number,
                last_offer=last_offer,
                best_competing_offer=competitor,
            )

        winner, winning_utility, utilities = _pick_best_valid_offer(buyer, current_offers)

        if winner is not None:
            accepted = winner.model_copy(update={"status": "ACCEPTED"})
            current_offers[winner.seller_name] = accepted
            records.append(RoundRecord(round_number, current_offers, utilities))
            return NegotiationResult(
                buyer=buyer,
                rounds=records,
                seller_configs=configs,
                winner=accepted,
                winning_utility=winning_utility,
                reason="ACCEPT",
            )

        records.append(RoundRecord(round_number, current_offers, utilities))

        if all(offer.status == "WALK_AWAY" for offer in current_offers.values()):
            return NegotiationResult(
                buyer=buyer,
                rounds=records,
                seller_configs=configs,
                winner=None,
                winning_utility=None,
                reason="ALL_WALKED_AWAY",
            )

        previous_offers = current_offers

    return NegotiationResult(
        buyer=buyer,
        rounds=records,
        seller_configs=configs,
        winner=None,
        winning_utility=None,
        reason="ROUND_LIMIT",
    )


def _format_cell(offer: Offer) -> str:
    if offer.status == "WALK_AWAY":
        return "WALKED"
    suffix = " ACCEPTED" if offer.status == "ACCEPTED" else ""
    return f"₹{offer.price:,.2f}{suffix}"


def print_result(result: NegotiationResult) -> None:
    seller_names = list(result.seller_configs)
    widths = {name: max(22, len(name) + 2) for name in seller_names}

    header = f"{'ROUND':<7}" + "".join(f"{name:>{widths[name]}}" for name in seller_names)
    print(header)
    print("-" * len(header))

    for record in result.rounds:
        row = f"{record.round_number:<7}"
        for name in seller_names:
            row += f"{_format_cell(record.offers[name]):>{widths[name]}}"
        print(row)

    print()
    if result.winner is None:
        print("NO DEAL")
    else:
        print(f"WINNER: {result.winner.seller_name} PRICE: ₹{result.winner.price:,.2f}")


def default_sellers() -> list[Seller]:
    """Fallback defaults because the prompt did not include the literal A/B/C spec."""
    configs = [
        SellerConfig(
            name="SELLER A",
            cost_price=money(18000),
            opening_price=money(26000),
            floor_price=money(21500),
            concession_rate=Decimal("0.06"),
            delivery_options=[
                DeliveryOption(label="standard", days=4, price_delta=money(0)),
                DeliveryOption(label="express", days=2, price_delta=money(700)),
            ],
            warranty_options=[6, 12],
            addon_costs={"setup": money(250)},
            strategy="aggressive",
        ),
        SellerConfig(
            name="SELLER B",
            cost_price=money(17500),
            opening_price=money(27500),
            floor_price=money(20500),
            concession_rate=Decimal("0.14"),
            delivery_options=[
                DeliveryOption(label="standard", days=5, price_delta=money(0)),
                DeliveryOption(label="express", days=3, price_delta=money(450)),
            ],
            warranty_options=[6, 12, 18],
            addon_costs={"setup": money(200), "support": money(400)},
            strategy="accommodating",
        ),
        SellerConfig(
            name="SELLER C",
            cost_price=money(18500),
            opening_price=money(26800),
            floor_price=money(22000),
            concession_rate=Decimal("0.04"),
            delivery_options=[
                DeliveryOption(label="standard", days=3, price_delta=money(0)),
                DeliveryOption(label="priority", days=2, price_delta=money(850)),
            ],
            warranty_options=[12, 18, 24],
            addon_costs={
                "installation": money(300),
                "priority_support": money(500),
                "accessory_pack": money(650),
            },
            strategy="value",
        ),
    ]
    return [Seller(config) for config in configs]


def demo() -> None:
    buyer = BuyerRequest(
        product="Demo Product",
        budget=money(23000),
        max_delivery_days=5,
        price_weight=0.60,
        delivery_weight=0.20,
        warranty_weight=0.20,
    )
    result = run_negotiation(buyer, default_sellers())
    print_result(result)


if __name__ == "__main__":
    demo()
