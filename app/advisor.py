from functools import lru_cache
from typing import Optional, Tuple

from openai import OpenAI

from app import usage as usage_tracker
from app.config import ITINERARY_MAX_OUTPUT_TOKENS, MAX_OUTPUT_TOKENS, OPENAI_MODEL, get_api_key
from app.prompts import ITINERARY_PROMPT, SYSTEM_PROMPT
from app.schemas import ItineraryResult, Usage


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(api_key=get_api_key())


def chat(message: str, previous_response_id: Optional[str] = None) -> Tuple[str, str, Usage, Usage]:
    """Send one user message; conversation state is kept by OpenAI via previous_response_id.

    Returns (answer, response_id, call_usage, conversation_usage).
    """
    response = _client().responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,  # not carried over between responses, so sent every call
        input=message,
        previous_response_id=previous_response_id,
        store=True,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    u = response.usage
    call = usage_tracker.make_usage(
        OPENAI_MODEL, getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0
    )
    total = usage_tracker.add_to_conversation(response.id, previous_response_id, call)
    return response.output_text, response.id, call, total


def generate_itinerary(previous_response_id: str) -> Tuple[ItineraryResult, str, Usage, Usage]:
    """Turn an existing conversation into a structured itinerary (or a clarifying question)."""
    response = _client().responses.parse(
        model=OPENAI_MODEL,
        instructions=ITINERARY_PROMPT,
        input="Produce the structured trip plan now.",
        previous_response_id=previous_response_id,
        text_format=ItineraryResult,
        store=True,
        max_output_tokens=ITINERARY_MAX_OUTPUT_TOKENS,
    )
    result = response.output_parsed
    if result is None:
        raise ValueError("Model returned no parsable itinerary.")
    u = response.usage
    call = usage_tracker.make_usage(
        OPENAI_MODEL, getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0
    )
    total = usage_tracker.add_to_conversation(response.id, previous_response_id, call)
    return result, response.id, call, total
