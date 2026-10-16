from typing import Optional

from pydantic import BaseModel, Field

from app.config import MAX_MESSAGE_CHARS


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_CHARS)
    previous_response_id: Optional[str] = Field(
        default=None, max_length=200, description="ID returned by the previous /chat call."
    )


class ChatResponse(BaseModel):
    answer: str
    response_id: str
