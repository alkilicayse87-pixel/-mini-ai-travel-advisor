# Security notes

- API key lives only in `.env` (git-ignored) or the host's secret store; never in code, Postman exports, or chats.
- Prompt injection / scope abuse: system prompt restricts to travel planning and treats user text as data. Not bulletproof; add output checks later.
- Input limits: message length capped (`MAX_MESSAGE_CHARS`) to limit cost abuse.
- Errors: upstream details are logged server-side, not returned to clients.
- TODO before public launch: rate limiting per IP, restrict `ALLOWED_ORIGINS` to the frontend, API auth, spend limit on the OpenAI key.
