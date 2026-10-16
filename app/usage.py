from collections import OrderedDict
from typing import Optional

from app.schemas import Usage

# USD per 1M tokens (input, output). Check https://openai.com/api/pricing for current values.
PRICES_PER_1M = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
}

_MAX_TRACKED = 5000
# response_id -> cumulative usage of the conversation up to that response.
# In-memory only: resets on restart, and is bounded so it can't grow forever.
_totals: "OrderedDict[str, Usage]" = OrderedDict()


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICES_PER_1M.get(model)
    if price is None:
        price = next((p for name, p in PRICES_PER_1M.items() if model.startswith(name)), (0.0, 0.0))
    return round((input_tokens * price[0] + output_tokens * price[1]) / 1_000_000, 6)


def make_usage(model: str, input_tokens: int, output_tokens: int) -> Usage:
    return Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=estimate_cost(model, input_tokens, output_tokens),
    )


def add_to_conversation(response_id: str, previous_id: Optional[str], call: Usage) -> Usage:
    prev = _totals.get(previous_id) if previous_id else None
    total = Usage(
        input_tokens=call.input_tokens + (prev.input_tokens if prev else 0),
        output_tokens=call.output_tokens + (prev.output_tokens if prev else 0),
        cost_usd=round(call.cost_usd + (prev.cost_usd if prev else 0.0), 6),
    )
    _totals[response_id] = total
    while len(_totals) > _MAX_TRACKED:
        _totals.popitem(last=False)
    return total
