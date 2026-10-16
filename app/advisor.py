from functools import lru_cache
from typing import Optional, Tuple

from openai import OpenAI

from app import usage as usage_tracker
from app.config import MAX_OUTPUT_TOKENS, OPENAI_MODEL, get_api_key
from app.prompts import SYSTEM_PROMPT
from app.schemas import Usage


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
