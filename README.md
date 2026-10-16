# Mini AI Travel Advisor

Chatbot that plans personalized trips with the OpenAI API (FastAPI + Pydantic).

## Structure (one folder per main step)

| Folder | Step |
|---|---|
| `app/` | Core: `config`, `prompts`, `schemas` (Pydantic), `advisor` (OpenAI), `main` (CLI), `api` (FastAPI) |
| `tests/` | pytest tests (OpenAI mocked) |
| `postman/` | Postman collection for manual API testing |
| `deployment/` | Dockerfile + Render blueprint |
| `docs/` | Security analysis |
| `frontend/` | Placeholder for the later UI |

## Live demo

- API docs: https://ai-travel-advisor-ot90.onrender.com/docs
- Health: https://ai-travel-advisor-ot90.onrender.com/health

(Free plan: the first request after idle can take ~1 minute.)

## Setup

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then add OPENAI_API_KEY
```

Never commit `.env`.

## Run

CLI: `python -m app.main`
API: `uvicorn app.api:app --reload` → http://127.0.0.1:8000/docs

- `GET /health`
- `POST /chat` `{"message": "...", "previous_response_id": "resp_..."}` → `{"answer", "response_id", "usage", "conversation_usage"}`
- `POST /itinerary` `{"previous_response_id": "resp_..."}` → structured JSON itinerary built from the conversation (see below)

### Structured itinerary

Chat with `/chat` until the advisor has enough info, then call `/itinerary` with the latest `response_id`:

```
{
  "ready": true,
  "clarification": null,
  "itinerary": {
    "title": "...", "destination": "...", "duration_days": 2, "summary": "...",
    "days": [{"day": 1, "theme": "...", "activities": [
      {"time_of_day": "morning", "title": "...", "description": "...", "estimated_cost": 12.0}]}],
    "tips": ["..."],
    "budget": {"currency": "EUR", "items": [{"category": "Food", "amount": 80.0}], "total": 212.0}
  },
  "response_id": "resp_...", "usage": {...}, "conversation_usage": {...}
}
```

If required info is missing or contradictory, `ready` is `false`, `itinerary` is `null` and `clarification` holds the question to ask the user. The JSON schema is defined with Pydantic in `app/schemas.py` and enforced via OpenAI structured outputs.

To see the plan as tables in the terminal (uses only the standard library):

```
python scripts/get_itinerary.py resp_xxx                              # live API
python scripts/get_itinerary.py resp_xxx --url http://127.0.0.1:8000  # local API
python scripts/get_itinerary.py resp_xxx --json                       # raw JSON
```

`usage` is the input/output tokens and estimated USD cost of the call; `conversation_usage` is the running total for the conversation (kept in server memory, resets on restart). Prices live in `app/usage.py`; unknown models report cost 0. The CLI prints the running total after each answer.

State is client-managed: send back the `response_id` to continue a conversation.

## Tests

`pip install -r requirements-dev.txt` then `pytest`

## Deploy

Docker: `docker build -f deployment/Dockerfile -t travel-advisor .` then
`docker run -p 8000:8000 --env-file .env travel-advisor`.
Render: push to GitHub, create a Blueprint from `deployment/render.yaml`, set `OPENAI_API_KEY` in the dashboard.
