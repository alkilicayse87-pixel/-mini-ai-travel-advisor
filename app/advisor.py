from typing import Optional, Tuple

from app import tools
from app import usage as usage_tracker
from app.config import (
    ITINERARY_MAX_OUTPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MAX_TOOL_ROUNDS,
    OPENAI_MODEL,
)
from app.llm import get_client as _client
from app.prompts import ITINERARY_PROMPT, SYSTEM_PROMPT
from app.schemas import ItineraryResult, Usage


def chat(message: str, previous_response_id: Optional[str] = None) -> Tuple[str, str, Usage, Usage]:
    """Send one user message; conversation state is kept by OpenAI via previous_response_id.

    The model may call tools (weather, currency, translation); we run them and feed the results
    back until it produces a final answer. Returns (answer, response_id, call_usage, conversation_usage).
    """
    next_input = message
    prev_id = previous_response_id
    in_tokens = out_tokens = 0
    for round_no in range(MAX_TOOL_ROUNDS + 1):
        response = _client().responses.create(
            model=OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,  # not carried over between responses, so sent every call
            input=next_input,
            previous_response_id=prev_id,
            store=True,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            tools=tools.TOOLS,
            # On the last round force a text answer so a tool loop can never run away.
            tool_choice="none" if round_no == MAX_TOOL_ROUNDS else "auto",
        )
        u = response.usage
        in_tokens += getattr(u, "input_tokens", 0) or 0
        out_tokens += getattr(u, "output_tokens", 0) or 0
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            break
        next_input = [
            {
                "type": "function_call_output",
                "call_id": c.call_id,
                "output": tools.run_tool(c.name, c.arguments),
            }
            for c in calls
        ]
        prev_id = response.id
    call = usage_tracker.make_usage(OPENAI_MODEL, in_tokens, out_tokens)
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
