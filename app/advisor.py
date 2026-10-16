from functools import lru_cache
from typing import Optional, Tuple

from openai import OpenAI

from app.config import OPENAI_MODEL, get_api_key
from app.prompts import SYSTEM_PROMPT


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(api_key=get_api_key())


def chat(message: str, previous_response_id: Optional[str] = None) -> Tuple[str, str]:
    """Send one user message; conversation state is kept by OpenAI via previous_response_id."""
    response = _client().responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,  # not carried over between responses, so sent every call
        input=message,
        previous_response_id=previous_response_id,
        store=True,
    )
    return response.output_text, response.id
