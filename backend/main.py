from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import ValidationError
from sqlmodel import Session

from negotiation.buyer import BuyerRequest

from .database import create_db_and_tables, get_session
from .models import NegotiationDB, SellerPrivateConfigDB
from .schemas import NegotiationCreate, NegotiationCreatedResponse
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