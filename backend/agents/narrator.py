from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


SELLER_PERSONAS = {
    "SELLER A": (
        "You are a firm seller who protects value "
        "and concedes cautiously."
    ),
    "SELLER B": (
        "You are a flexible seller who competes "
        "through stronger concessions."
    ),
    "SELLER C": (
        "You are a value-focused seller who competes "
        "through service and overall terms."
    ),
}


FALLBACK_NARRATIONS = {
    "SELLER A": (
        "I'm holding a firm position while keeping "
        "this offer competitive."
    ),
    "SELLER B": (
        "I'm making a stronger concession to keep "
        "this deal competitive."
    ),
    "SELLER C": (
        "I'm strengthening the overall package while "
        "keeping this offer competitive."
    ),
}


FORBIDDEN_WORDS = {
    "floor",
    "cost",
    "margin",
    "target",
    "private",
    "profit",
}


def llm_enabled() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def narrate_offer(
    *,
    seller_name: str,
    round_number: int,
    price: str,
    delivery_days: int,
    warranty_months: int,
    addons: list[str],
    status: str,
) -> str:
    fallback = FALLBACK_NARRATIONS.get(
        seller_name,
        "I'm keeping this offer competitive while protecting its value.",
    )

    if status == "ACCEPTED":
        fallback = "I can close the deal on these terms."

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return fallback

    persona = SELLER_PERSONAS.get(
        seller_name,
        "You are a professional marketplace seller.",
    )

    addon_text = ", ".join(addons) if addons else "none"

    system_prompt = """
You generate one short seller negotiation sentence for UNDERBID.

The economic engine has already made every economic decision.
You are only a language layer.

You MUST NOT:
- change or invent price
- change or invent delivery
- change or invent warranty
- change or invent addons
- reveal private seller economics
- mention floors, costs, margins, targets, or profit

Your output cannot alter the structured offer.
""".strip()

    user_prompt = f"""
Seller persona:
{persona}

Structured public offer:
seller_name: {seller_name}
round_number: {round_number}
price: {price}
delivery_days: {delivery_days}
warranty_months: {warranty_months}
addons: {addon_text}
status: {status}

Write exactly one natural sentence.

Rules:
- first person as the seller
- maximum 18 words
- no numbers
- no currency symbols
- no markdown
- do not invent facts
- do not reveal private economics
- only claim the deal is closed if status is ACCEPTED
""".strip()

    try:
        client = Groq(api_key=api_key)

        completion = client.chat.completions.create(
    model=os.getenv(
        "GROQ_MODEL",
        "qwen/qwen3.6-27b",
    ),
    messages=[
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ],
    reasoning_effort="none",
    reasoning_format="hidden",
    temperature=0.5,
    max_completion_tokens=50,
)

        narration = (
            completion.choices[0].message.content or ""
        ).strip()

        narration = " ".join(narration.split())

        if not narration:
            return fallback

        if not _safe_narration(narration):
            return fallback

        return narration

    except Exception as exc:
        print(
            "[narrator] Groq unavailable; "
            f"using fallback: {exc}"
        )
        return fallback


def _safe_narration(text: str) -> bool:
    lowered = text.lower()

    if len(text.split()) > 18:
        return False

    if re.search(r"\d", text):
        return False

    if any(
        symbol in text
        for symbol in ("₹", "$", "€", "£", "%")
    ):
        return False

    if any(
        word in lowered
        for word in FORBIDDEN_WORDS
    ):
        return False

    return True