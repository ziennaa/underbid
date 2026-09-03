from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlmodel import Session, select

from negotiation.buyer import BuyerRequest
from negotiation.engine import run_negotiation
from negotiation.seller import (
    DeliveryOption,
    Seller,
    SellerConfig,
)

from .database import engine
from .manager import manager
from .models import (
    EventDB,
    NegotiationDB,
    OfferDB,
    SellerPrivateConfigDB,
)
from .agents.strategy import choose_strategy


def _reconstruct_sellers(
    rows: list[SellerPrivateConfigDB],
) -> list[Seller]:
    sellers: list[Seller] = []

    for row in rows:
        delivery_options = [
            DeliveryOption(
                label=option["label"],
                days=int(option["days"]),
                price_delta=Decimal(
                    str(option["price_delta"])
                ),
            )
            for option in row.delivery_options
        ]

        config = SellerConfig(
            name=row.seller_name,
            cost_price=row.cost_price,
            opening_price=row.opening_price,
            floor_price=row.floor_price,
            concession_rate=row.concession_rate,
            delivery_options=delivery_options,
            warranty_options=[
                int(months)
                for months in row.warranty_options
            ],
            addon_costs={
                name: Decimal(str(cost))
                for name, cost
                in row.addon_costs.items()
            },
            strategy=row.strategy,
        )

        sellers.append(Seller(config))

    return sellers


def _public_offer_payload(
    offer,
    utility_score: float | None,
) -> dict:
    return {
        "round_number": offer.round_number,
        "seller_name": offer.seller_name,

        # WebSocket/JSON has no Decimal type,
        # so send exact decimal strings.
        "price": str(offer.price),
        "base_price": str(offer.base_price),

        "delivery_days": offer.delivery_days,
        "warranty_months": offer.warranty_months,
        "addons": list(offer.addons),
        "status": offer.status,
        "utility_score": utility_score,
    }


async def run_and_stream_negotiation(
    negotiation_id: int,
) -> None:

    with Session(engine) as session:

        negotiation = session.get(
            NegotiationDB,
            negotiation_id,
        )

        if negotiation is None:
            raise RuntimeError(
                f"Negotiation {negotiation_id} not found"
            )

        seller_statement = (
            select(SellerPrivateConfigDB)
            .where(
                SellerPrivateConfigDB.negotiation_id
                == negotiation_id
            )
            .order_by(
                SellerPrivateConfigDB.seller_name
            )
        )

        seller_rows = list(
            session.exec(seller_statement).all()
        )

        if len(seller_rows) != 3:
            raise RuntimeError(
                "Negotiation must have exactly 3 sellers"
            )

        buyer = BuyerRequest(
            product=negotiation.product,
            budget=negotiation.budget,
            max_delivery_days=(
                negotiation.max_delivery_days
            ),
            price_weight=negotiation.price_weight,
            delivery_weight=(
                negotiation.delivery_weight
            ),
            warranty_weight=(
                negotiation.warranty_weight
            ),
        )

        sellers = _reconstruct_sellers(
            seller_rows
        )

        # IMPORTANT:
        # The frozen Phase-1 engine is called
        # exactly once.
        seller_tactics: dict[str, str] = {}
        seller_strategy_meta: dict[str, dict] = {}

        for seller in sellers:
            decision = await asyncio.to_thread(
                choose_strategy,
                seller_name=seller.config.name,
                personality=seller.config.strategy,
                price_weight=float(buyer.price_weight),
                delivery_weight=float(buyer.delivery_weight),
                warranty_weight=float(
                    buyer.warranty_weight
                ),
                max_delivery_days=(
                    buyer.max_delivery_days
                ),
            )

            seller_tactics[
                seller.config.name
            ] = decision.action.value

            seller_strategy_meta[
                seller.config.name
            ] = {
                "action": decision.action.value,
                "rationale": decision.rationale,
                "source": decision.source,
            }
        result = run_negotiation(
            buyer,
            sellers,
            seller_tactics=seller_tactics,
        )

        for index, record in enumerate(
            result.rounds
        ):
            round_number = record.round_number

            events_to_broadcast: list[dict] = []

            # -----------------------------
            # ROUND_STARTED
            # -----------------------------

            round_payload = {
                "round_number": round_number,
            }

            session.add(
                EventDB(
                    negotiation_id=negotiation_id,
                    event_type="ROUND_STARTED",
                    payload=round_payload,
                )
            )

            events_to_broadcast.append(
                {
                    "event_type": "ROUND_STARTED",
                    "negotiation_id": (
                        negotiation_id
                    ),
                    **round_payload,
                }
            )

            # -----------------------------
            # OFFERS
            # -----------------------------

            for seller_name in sorted(
                record.offers
            ):
                offer = record.offers[
                    seller_name
                ]

                utility_score = (
                    record.utilities.get(
                        seller_name
                    )
                )

                session.add(
                    OfferDB(
                        negotiation_id=(
                            negotiation_id
                        ),
                        seller_name=(
                            offer.seller_name
                        ),
                        round_number=(
                            offer.round_number
                        ),
                        price=offer.price,
                        base_price=offer.base_price,
                        delivery_days=(
                            offer.delivery_days
                        ),
                        warranty_months=(
                            offer.warranty_months
                        ),
                        addons=list(
                            offer.addons
                        ),
                        status=offer.status,
                        utility_score=(
                            utility_score
                        ),
                    )
                )

                offer_payload = (
                    _public_offer_payload(
                        offer,
                        utility_score,
                    )
                )
                strategy_meta = seller_strategy_meta.get(
                    offer.seller_name
                )

                if strategy_meta:
                    offer_payload[
                        "strategy_action"
                    ] = strategy_meta["action"]

                    offer_payload[
                        "strategy_rationale"
                    ] = strategy_meta["rationale"]

                    offer_payload[
                        "strategy_source"
                    ] = strategy_meta["source"]
                session.add(
                    EventDB(
                        negotiation_id=(
                            negotiation_id
                        ),
                        event_type=(
                            "OFFER_CREATED"
                        ),
                        payload=offer_payload,
                    )
                )

                events_to_broadcast.append(
                    {
                        "event_type": (
                            "OFFER_CREATED"
                        ),
                        "negotiation_id": (
                            negotiation_id
                        ),
                        **offer_payload,
                    }
                )

                if (
                    offer.status
                    == "WALK_AWAY"
                ):
                    walk_payload = {
                        "round_number": (
                            offer.round_number
                        ),
                        "seller_name": (
                            offer.seller_name
                        ),
                    }

                    session.add(
                        EventDB(
                            negotiation_id=(
                                negotiation_id
                            ),
                            event_type=(
                                "SELLER_WALKED"
                            ),
                            payload=(
                                walk_payload
                            ),
                        )
                    )

                    events_to_broadcast.append(
                        {
                            "event_type": (
                                "SELLER_WALKED"
                            ),
                            "negotiation_id": (
                                negotiation_id
                            ),
                            **walk_payload,
                        }
                    )

            # IMPORTANT:
            # Persist FIRST.
            session.commit()

            # Broadcast only after DB commit.
            for event in events_to_broadcast:
                await manager.broadcast(
                    negotiation_id,
                    event,
                )

            # Delay only BETWEEN rounds.
            if index < len(result.rounds) - 1:
                await asyncio.sleep(0.6)

        # =================================
        # FINAL RESULT
        # =================================

        final_round = (
            result.rounds[-1].round_number
        )

        if result.winner is not None:
            negotiation.status = "DEAL_FOUND"
            negotiation.winner_seller_name = (
                result.winner.seller_name
            )
            negotiation.final_price = (
                result.winner.price
            )

            final_payload = {
                "round_number": final_round,
                "seller_name": (
                    result.winner.seller_name
                ),
                "price": str(
                    result.winner.price
                ),
                "utility_score": (
                    result.winning_utility
                ),
            }

            final_event_type = "DEAL_FOUND"

        else:
            negotiation.status = "NO_DEAL"
            negotiation.winner_seller_name = None
            negotiation.final_price = None

            final_payload = {
                "round_number": final_round,
                "reason": result.reason,
            }

            final_event_type = "NO_DEAL"

        session.add(negotiation)

        session.add(
            EventDB(
                negotiation_id=negotiation_id,
                event_type=final_event_type,
                payload=final_payload,
            )
        )

        # Again: persist FIRST.
        session.commit()

        await manager.broadcast(
            negotiation_id,
            {
                "event_type": final_event_type,
                "negotiation_id": negotiation_id,
                **final_payload,
            },
        )