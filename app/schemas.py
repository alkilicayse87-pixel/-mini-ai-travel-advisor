from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.config import MAX_MESSAGE_CHARS


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_CHARS)
    previous_response_id: Optional[str] = Field(
        default=None, max_length=200, description="ID returned by the previous /chat call."
    )


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    response_id: str
    usage: Usage = Field(description="Tokens and estimated cost of this call.")
    conversation_usage: Usage = Field(
        description="Running total for this conversation (since the last server restart)."
    )


# ---- Structured itinerary (used with OpenAI structured outputs) ----
# Strict mode: every field is required; optional values are nullable, no defaults.
class Activity(BaseModel):
    time_of_day: Literal["morning", "afternoon", "evening"]
    title: str
    description: str
    estimated_cost: float = Field(description="Estimated cost per person in the budget currency.")


class DayPlan(BaseModel):
    day: int
    theme: str
    activities: list[Activity]


class BudgetItem(BaseModel):
    category: str
    amount: float


class Budget(BaseModel):
    currency: str = Field(description="ISO code, e.g. EUR")
    items: list[BudgetItem]
    total: float


class Itinerary(BaseModel):
    title: str
    destination: str
    duration_days: int
    summary: str
    days: list[DayPlan]
    tips: list[str]
    budget: Budget


class ItineraryResult(BaseModel):
    """Model output: either a complete itinerary or what is still missing/ambiguous."""

    ready: bool = Field(description="True only if destination, duration and interests are known and consistent.")
    clarification: Optional[str] = Field(description="Question to ask the user when ready is false.")
    itinerary: Optional[Itinerary] = Field(description="The plan when ready is true, otherwise null.")


class ItineraryRequest(BaseModel):
    previous_response_id: str = Field(..., max_length=200, description="ID of the conversation so far.")


class ItineraryResponse(BaseModel):
    ready: bool
    clarification: Optional[str] = None
    itinerary: Optional[Itinerary] = None
    response_id: str
    usage: Usage
    conversation_usage: Usage
