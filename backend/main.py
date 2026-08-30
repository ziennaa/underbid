from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from .manager import manager
from pydantic import ValidationError
from sqlmodel import Session, select

from negotiation.buyer import BuyerRequest

from .database import create_db_and_tables, get_session
from .models import NegotiationDB, OfferDB, SellerPrivateConfigDB
from .schemas import (
    NegotiationCreate,
    NegotiationCreatedResponse,
    NegotiationPublic,
    NegotiationStartResponse,
    OfferPublic,
    RoundPublic,
)
from .service import run_and_stream_negotiation
from .seller_factory import make_sellers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    yield


app = FastAPI(
    title="UNDERBID API",
    lifespan=lifespan,
)


@app.post(
    "/api/negotiations",
    response_model=NegotiationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_negotiation(
    request: NegotiationCreate,
    session: Session = Depends(get_session),
) -> NegotiationCreatedResponse:

    try:
        buyer = BuyerRequest(
            product=request.product,
            budget=request.budget,
            max_delivery_days=request.max_delivery_days,
            price_weight=request.price_weight,
            delivery_weight=request.delivery_weight,
            warranty_weight=request.warranty_weight,
        )

    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=json.loads(exc.json()),
        ) from exc

    sellers = make_sellers(
        randomize_sellers=request.randomize_sellers,
        seed=request.seed,
    )

    negotiation = NegotiationDB(
        product=buyer.product,
        budget=buyer.budget,
        max_delivery_days=buyer.max_delivery_days,
        price_weight=buyer.price_weight,
        delivery_weight=buyer.delivery_weight,
        warranty_weight=buyer.warranty_weight,
        status="CREATED",
    )

    session.add(negotiation)
    session.flush()

    if negotiation.id is None:
        raise RuntimeError("Database failed to assign negotiation id")

    for seller in sellers:
        config = seller.config

        private_config = SellerPrivateConfigDB(
            negotiation_id=negotiation.id,
            seller_name=config.name,
            cost_price=config.cost_price,
            opening_price=config.opening_price,
            floor_price=config.floor_price,
            concession_rate=config.concession_rate,
            delivery_options=[
                {
                    "label": option.label,
                    "days": option.days,
                    "price_delta": str(option.price_delta),
                }
                for option in config.delivery_options
            ],
            warranty_options=list(config.warranty_options),
            addon_costs={
                name: str(cost)
                for name, cost in config.addon_costs.items()
            },
            strategy=config.strategy,
        )

        session.add(private_config)

    session.commit()

    return NegotiationCreatedResponse(
        negotiation_id=negotiation.id,
        status="CREATED",
    )


@app.get(
    "/api/negotiations/{negotiation_id}",
    response_model=NegotiationPublic,
)
def get_negotiation(
    negotiation_id: int,
    session: Session = Depends(get_session),
) -> NegotiationPublic:

    negotiation = session.get(
        NegotiationDB,
        negotiation_id,
    )

    if negotiation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Negotiation not found",
        )

    statement = (
        select(OfferDB)
        .where(
            OfferDB.negotiation_id == negotiation_id
        )
        .order_by(
            OfferDB.round_number,
            OfferDB.seller_name,
        )
    )

    stored_offers = list(
        session.exec(statement).all()
    )

    rounds_by_number: dict[int, list[OfferPublic]] = {}

    for offer in stored_offers:
        public_offer = OfferPublic(
            seller_name=offer.seller_name,
            price=offer.price,
            base_price=offer.base_price,
            delivery_days=offer.delivery_days,
            warranty_months=offer.warranty_months,
            addons=list(offer.addons),
            status=offer.status,
            utility_score=offer.utility_score,
        )

        rounds_by_number.setdefault(
            offer.round_number,
            [],
        ).append(public_offer)

    rounds = [
        RoundPublic(
            round_number=round_number,
            offers=offers,
        )
        for round_number, offers
        in sorted(rounds_by_number.items())
    ]

    if negotiation.id is None:
        raise RuntimeError(
            "Stored negotiation has no id"
        )

    return NegotiationPublic(
        id=negotiation.id,
        product=negotiation.product,
        budget=negotiation.budget,
        max_delivery_days=negotiation.max_delivery_days,
        price_weight=negotiation.price_weight,
        delivery_weight=negotiation.delivery_weight,
        warranty_weight=negotiation.warranty_weight,
        status=negotiation.status,
        winner_seller_name=negotiation.winner_seller_name,
        final_price=negotiation.final_price,
        created_at=negotiation.created_at,
        rounds=rounds,
    )
@app.post(
    "/api/negotiations/{negotiation_id}/start",
    response_model=NegotiationStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_negotiation(
    negotiation_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> NegotiationStartResponse:

    negotiation = session.get(
        NegotiationDB,
        negotiation_id,
    )

    if negotiation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Negotiation not found",
        )

    if negotiation.status != "CREATED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Negotiation has already been started"
            ),
        )

    negotiation.status = "RUNNING"

    session.add(negotiation)
    session.commit()

    background_tasks.add_task(
        run_and_stream_negotiation,
        negotiation_id,
    )

    return NegotiationStartResponse(
        negotiation_id=negotiation_id,
        status="RUNNING",
    )


@app.websocket(
    "/ws/negotiations/{negotiation_id}"
)
async def negotiation_websocket(
    websocket: WebSocket,
    negotiation_id: int,
) -> None:

    await websocket.accept()

    manager.connect(
        negotiation_id,
        websocket,
    )

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(
            negotiation_id,
            websocket,
        )