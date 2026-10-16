from typing import Optional

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
