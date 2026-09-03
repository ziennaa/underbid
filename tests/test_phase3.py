from __future__ import annotations
from backend.agents.strategy import StrategyDecision
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import backend.main as main_module
import backend.service as service_module

from backend.database import get_session
from backend.main import app
from backend.seller_factory import make_sellers

from negotiation.buyer import BuyerRequest
from negotiation.engine import run_negotiation

FORBIDDEN_FIELDS = {
    "cost_price",
    "floor_price",
    "opening_price",
    "concession_rate",
}


@pytest.fixture
def client(monkeypatch):
    # Separate in-memory SQLite DB just for this test.
    # StaticPool ensures every thread sees the same DB.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(test_engine)

    def get_test_session():
        with Session(test_engine) as session:
            yield session

    # HTTP routes use the test DB.
    app.dependency_overrides[get_session] = get_test_session

    # service.py opens its own Session(engine),
    # so point that engine at the same test DB too.
    monkeypatch.setattr(
        service_module,
        "engine",
        test_engine,
    )

    # Prevent the lifespan from creating/touching underbid.db.
    monkeypatch.setattr(
        main_module,
        "create_db_and_tables",
        lambda: SQLModel.metadata.create_all(test_engine),
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def assert_no_private_fields(value):
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in FORBIDDEN_FIELDS
            assert_no_private_fields(child)

    elif isinstance(value, list):
        for child in value:
            assert_no_private_fields(child)


def expected_rounds(result):
    rounds = []

    for record in result.rounds:
        offers = []

        for seller_name in sorted(record.offers):
            offer = record.offers[seller_name]

            offers.append(
                {
                    "seller_name": offer.seller_name,
                    "round_number": offer.round_number,
                    "price": str(offer.price),
                    "base_price": str(offer.base_price),
                    "delivery_days": offer.delivery_days,
                    "warranty_months": offer.warranty_months,
                    "addons": list(offer.addons),
                    "status": offer.status,
                    "utility_score": record.utilities.get(
                        seller_name
                    ),
                }
            )

        rounds.append(
            {
                "round_number": record.round_number,
                "offers": offers,
            }
        )

    return rounds


def websocket_rounds(events):
    grouped = {}

    for event in events:
        if event["event_type"] != "OFFER_CREATED":
            continue

        round_number = event["round_number"]

        grouped.setdefault(
            round_number,
            [],
        ).append(
            {
                "seller_name": event["seller_name"],
                "round_number": event["round_number"],
                "price": event["price"],
                "base_price": event["base_price"],
                "delivery_days": event["delivery_days"],
                "warranty_months": event["warranty_months"],
                "addons": event["addons"],
                "status": event["status"],
                "utility_score": event["utility_score"],
            }
        )

    return [
        {
            "round_number": round_number,
            "offers": sorted(
                offers,
                key=lambda x: x["seller_name"],
            ),
        }
        for round_number, offers
        in sorted(grouped.items())
    ]


def get_rounds(response_json):
    rounds = []

    for record in response_json["rounds"]:
        rounds.append(
            {
                "round_number": record["round_number"],
                "offers": sorted(
                    [
                        {
                            "seller_name": offer["seller_name"],
                            "round_number": record[
                                "round_number"
                            ],
                            "price": str(
                                Decimal(
                                    str(offer["price"])
                                )
                            ),
                            "base_price": str(
                                Decimal(
                                    str(offer["base_price"])
                                )
                            ),
                            "delivery_days": offer[
                                "delivery_days"
                            ],
                            "warranty_months": offer[
                                "warranty_months"
                            ],
                            "addons": offer["addons"],
                            "status": offer["status"],
                            "utility_score": offer[
                                "utility_score"
                            ],
                        }
                        for offer in record["offers"]
                    ],
                    key=lambda x: x["seller_name"],
                ),
            }
        )

    return rounds


def compare_rounds(actual, expected):
    assert len(actual) == len(expected)

    for actual_round, expected_round in zip(
        actual,
        expected,
    ):
        assert (
            actual_round["round_number"]
            == expected_round["round_number"]
        )

        assert len(
            actual_round["offers"]
        ) == len(expected_round["offers"])

        for actual_offer, expected_offer in zip(
            actual_round["offers"],
            expected_round["offers"],
        ):
            assert (
                actual_offer["seller_name"]
                == expected_offer["seller_name"]
            )

            assert (
                actual_offer["round_number"]
                == expected_offer["round_number"]
            )

            assert (
                Decimal(actual_offer["price"])
                == Decimal(expected_offer["price"])
            )

            assert (
                Decimal(actual_offer["base_price"])
                == Decimal(
                    expected_offer["base_price"]
                )
            )

            assert (
                actual_offer["delivery_days"]
                == expected_offer["delivery_days"]
            )

            assert (
                actual_offer["warranty_months"]
                == expected_offer[
                    "warranty_months"
                ]
            )

            assert (
                actual_offer["addons"]
                == expected_offer["addons"]
            )

            assert (
                actual_offer["status"]
                == expected_offer["status"]
            )

            actual_utility = actual_offer[
                "utility_score"
            ]
            expected_utility = expected_offer[
                "utility_score"
            ]

            if expected_utility is None:
                assert actual_utility is None
            else:
                assert actual_utility == pytest.approx(
                    expected_utility
                )


def test_phase3_engine_parity_and_privacy(client, monkeypatch):
    seed = 42
    fixed_tactics = {
        "SELLER A": "CONCEDE_PRICE",
        "SELLER B": "IMPROVE_TERMS",
        "SELLER C": "ADD_VALUE",
    }


    def fake_choose_strategy(
        *,
        seller_name,
        **kwargs,
    ):
        return StrategyDecision(
            action=fixed_tactics[seller_name],
            rationale="Deterministic test strategy.",
            source="TEST",
        )


    monkeypatch.setattr(
        "backend.service.choose_strategy",
        fake_choose_strategy,
    )
    payload = {
        "product": "Sony XM5",
        "reference_price": 26000,
        "budget": 24000,
        "max_delivery_days": 5,
        "price_weight": 0.6,
        "delivery_weight": 0.2,
        "warranty_weight": 0.2,
        "randomize_sellers": True,
        "seed": seed,
    }

    # ---------------------------------
    # DIRECT PHASE-1 RESULT
    # ---------------------------------

    buyer = BuyerRequest(
        product=payload["product"],
        budget=Decimal(str(payload["budget"])),
        max_delivery_days=payload[
            "max_delivery_days"
        ],
        price_weight=payload["price_weight"],
        delivery_weight=payload[
            "delivery_weight"
        ],
        warranty_weight=payload[
            "warranty_weight"
        ],
    )

    direct_sellers = make_sellers(
    randomize_sellers=True,
    reference_price=Decimal(
        str(payload["reference_price"])
    ),
    seed=seed,
)

    direct_result = run_negotiation(
        buyer,
        direct_sellers,
        seller_tactics=fixed_tactics,
    )

    expected = expected_rounds(
        direct_result
    )

    # ---------------------------------
    # CREATE THROUGH API
    # ---------------------------------

    create_response = client.post(
        "/api/negotiations",
        json=payload,
    )

    assert create_response.status_code == 201

    negotiation_id = create_response.json()[
        "negotiation_id"
    ]

    # ---------------------------------
    # CONNECT WEBSOCKET BEFORE START
    # ---------------------------------

    events = []

    with client.websocket_connect(
        f"/ws/negotiations/{negotiation_id}"
    ) as websocket:

        start_response = client.post(
            f"/api/negotiations/"
            f"{negotiation_id}/start"
        )

        assert start_response.status_code == 202

        while True:
            event = websocket.receive_json()

            events.append(event)

            if event["event_type"] in {
                "DEAL_FOUND",
                "NO_DEAL",
            }:
                break

    # ---------------------------------
    # A) EVENT ROUND ORDER
    # ---------------------------------

    round_numbers = [
        event["round_number"]
        for event in events
        if "round_number" in event
    ]

    assert round_numbers == sorted(
        round_numbers
    )

    # ---------------------------------
    # B) FULL ENGINE PARITY
    # ---------------------------------

    ws_rounds = websocket_rounds(events)

    compare_rounds(
        ws_rounds,
        expected,
    )

    final_event = events[-1]

    if direct_result.winner is None:
        assert (
            final_event["event_type"]
            == "NO_DEAL"
        )

        assert (
            final_event["reason"]
            == direct_result.reason
        )

    else:
        assert (
            final_event["event_type"]
            == "DEAL_FOUND"
        )

        assert (
            final_event["seller_name"]
            == direct_result.winner.seller_name
        )

        assert (
            Decimal(final_event["price"])
            == direct_result.winner.price
        )

    # ---------------------------------
    # C) PRIVATE FIELDS NEVER LEAK
    # ---------------------------------

    for event in events:
        assert_no_private_fields(event)

    get_response = client.get(
        f"/api/negotiations/{negotiation_id}"
    )

    assert get_response.status_code == 200

    get_json = get_response.json()

    assert_no_private_fields(get_json)

    # Extra check against serialized form.
    serialized = json.dumps(get_json)

    for field in FORBIDDEN_FIELDS:
        assert field not in serialized

    # ---------------------------------
    # D) GET == WEBSOCKET ROUNDS
    # ---------------------------------

    stored_rounds = get_rounds(
        get_json
    )

    compare_rounds(
        stored_rounds,
        ws_rounds,
    )