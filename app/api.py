import logging

import openai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import advisor
from app.config import ALLOWED_ORIGINS
from app.schemas import ChatRequest, ChatResponse

logger = logging.getLogger("travel-advisor")

app = FastAPI(title="AI Travel Advisor", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        answer, response_id = advisor.chat(req.message, req.previous_response_id)
    except openai.NotFoundError:
        raise HTTPException(status_code=400, detail="Unknown previous_response_id.")
    except openai.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited, try again shortly.")
    except Exception:
        logger.exception("chat failed")
        raise HTTPException(status_code=502, detail="Upstream AI service error.")
    return ChatResponse(answer=answer, response_id=response_id)
