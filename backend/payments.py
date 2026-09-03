from __future__ import annotations

import os
from decimal import Decimal, ROUND_HALF_UP

import razorpay
from dotenv import load_dotenv


load_dotenv()


def _credentials() -> tuple[str, str]:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise RuntimeError(
            "Razorpay credentials are not configured"
        )

    return key_id, key_secret


def get_razorpay_key_id() -> str:
    key_id, _ = _credentials()
    return key_id


def create_razorpay_order(
    *,
    negotiation_id: int,
    amount_rupees: Decimal,
    seller_name: str,
) -> dict:
    if amount_rupees <= 0:
        raise ValueError(
            "Payment amount must be positive"
        )

    key_id, key_secret = _credentials()

    amount_paise = int(
        (amount_rupees * Decimal("100")).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )

    client = razorpay.Client(
        auth=(key_id, key_secret)
    )

    order = client.order.create(
        data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"underbid_{negotiation_id}",
            "notes": {
                "negotiation_id": str(
                    negotiation_id
                ),
                "seller_name": seller_name,
            },
        }
    )

    return order

def verify_razorpay_payment(
    *,
    order_id: str,
    payment_id: str,
    signature: str,
) -> None:
    key_id, key_secret = _credentials()

    client = razorpay.Client(
        auth=(key_id, key_secret)
    )

    client.utility.verify_payment_signature(
        {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
    )