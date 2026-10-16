import logging

import openai
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app import advisor
from app.config import ALLOWED_ORIGINS
from app.schemas import ChatRequest, ChatResponse
from app.security import enforce_rate_limit

logger = logging.getLogger("travel-advisor")

app = FastAPI(title="AI Travel Advisor", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(enforce_rate_limit)])
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
