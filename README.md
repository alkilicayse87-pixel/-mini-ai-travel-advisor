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
- `POST /chat` `{"message": "...", "previous_response_id": "resp_..."}` → `{"answer", "response_id"}`

State is client-managed: send back the `response_id` to continue a conversation.

## Tests

`pip install -r requirements-dev.txt` then `pytest`

## Deploy

Docker: `docker build -f deployment/Dockerfile -t travel-advisor .` then
`docker run -p 8000:8000 --env-file .env travel-advisor`.
Render: push to GitHub, create a Blueprint from `deployment/render.yaml`, set `OPENAI_API_KEY` in the dashboard.
