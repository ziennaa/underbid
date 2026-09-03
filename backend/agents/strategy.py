from __future__ import annotations

import json
import os
from enum import Enum

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field


load_dotenv()


class SellerTactic(str, Enum):
    HOLD = "HOLD"
    CONCEDE_PRICE = "CONCEDE_PRICE"
    ADD_VALUE = "ADD_VALUE"
    IMPROVE_TERMS = "IMPROVE_TERMS"


class StrategyDecision(BaseModel):
    action: SellerTactic
    rationale: str = Field(max_length=180)
    source: str = "LLM"


FALLBACK_BY_PERSONALITY = {
    "aggressive": SellerTactic.CONCEDE_PRICE,
    "accommodating": SellerTactic.IMPROVE_TERMS,
    "value": SellerTactic.ADD_VALUE,
}


def choose_strategy(
    *,
    seller_name: str,
    personality: str,
    price_weight: float,
    delivery_weight: float,
    warranty_weight: float,
    max_delivery_days: int,
) -> StrategyDecision:
    fallback_action = FALLBACK_BY_PERSONALITY.get(
        personality,
        SellerTactic.HOLD,
    )

    fallback = StrategyDecision(
        action=fallback_action,
        rationale=(
            f"Using deterministic {personality} seller policy."
        ),
        source="DETERMINISTIC_FALLBACK",
    )

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return fallback

    prompt = f"""
You are choosing a negotiation STRATEGY for one seller in UNDERBID.

You DO NOT control money.
You DO NOT choose prices.
Python will calculate all economic results.

Seller:
{seller_name}

Seller personality:
{personality}

Buyer priorities:
price_weight: {price_weight}
delivery_weight: {delivery_weight}
warranty_weight: {warranty_weight}

Buyer maximum delivery:
{max_delivery_days} days

Choose exactly ONE action:

HOLD
CONCEDE_PRICE
ADD_VALUE
IMPROVE_TERMS

Meanings:

HOLD:
Protect price and avoid aggressive concession.

CONCEDE_PRICE:
Compete more aggressively on price.

ADD_VALUE:
Prefer warranty and add-ons rather than deeper price cuts.

IMPROVE_TERMS:
Prefer faster delivery / stronger non-price terms.
The rationale must be at most 20 words.
Return ONLY valid JSON:

{{
  "action": "ONE_ACTION",
  "rationale": "one short reason"
}}

Do not include prices.
Do not include currency.
Do not invent seller economics.
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
                    "role": "user",
                    "content": prompt,
                }
            ],
            reasoning_effort="none",
            reasoning_format="hidden",
            temperature=0.3,
            max_completion_tokens=100,
        )

        raw = (
            completion.choices[0].message.content or ""
        ).strip()

        parsed = json.loads(raw)

        rationale = " ".join(
            str(parsed["rationale"]).split()
        )
        
        if not rationale:
            raise ValueError("empty rationale")
        
        decision = StrategyDecision(
            action=SellerTactic(parsed["action"]),
            rationale=rationale[:180],
            source="LLM",
        )
        
        return decision

    except Exception as exc:
        print(
            "[strategy] Groq unavailable; "
            f"using deterministic fallback: {exc}"
        )

        return fallback