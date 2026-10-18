import threading
from collections import OrderedDict
from datetime import datetime, timezone
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


_spend_lock = threading.Lock()
_daily = {"day": "", "spent": 0.0}


def spent_today() -> float:
    today = datetime.now(timezone.utc).date().isoformat()
    with _spend_lock:
        if _daily["day"] != today:
            _daily.update(day=today, spent=0.0)
        return _daily["spent"]


def record_spend(cost_usd: float) -> None:
    spent_today()  # rolls the day over if needed
    with _spend_lock:
        _daily["spent"] += cost_usd


def reset_daily() -> None:
    with _spend_lock:
        _daily.update(day="", spent=0.0)


def conversation_cost(response_id: Optional[str]) -> float:
    total = _totals.get(response_id) if response_id else None
    return total.cost_usd if total else 0.0


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
