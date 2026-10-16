# Security notes

## Risks and mitigations

| Risk | Mitigation (status) |
|---|---|
| API key leak | Key only in `.env` (git-ignored) / Render secret env var; never in code or Postman (done) |
| Cost abuse / DoS | Per-IP limit (10/min), global cap (200/hour), message length cap, `max_output_tokens` (done). Also set a spend limit in the OpenAI dashboard |
| Prompt injection / off-topic use | System prompt restricts to travel planning and treats user text as data (partial; the model can still be tricked) |
| Tool-calling misuse | No tools are exposed yet. When added: allow-list, validate arguments, no side effects |
| Info leakage | Upstream errors logged server-side only; generic messages to clients (done) |
| Browser attacks | Security headers (`nosniff`, `no-referrer`, `no-store`); CORS configurable via `ALLOWED_ORIGINS` (done) |
| Forged `previous_response_id` | OpenAI rejects unknown IDs (400); IDs are not guessable |

## Known limitations

- Rate limiter is in-memory and per-process; behind a proxy the client IP can be spoofed via `X-Forwarded-For`, which is why the global hourly cap exists. Use Redis or an API gateway if scaling out.
- Public endpoint has no authentication. Add an API key / login before a real launch.

## TODO

- Restrict `ALLOWED_ORIGINS` to the frontend URL once it exists.
- Moderate user input/output; log and alert on abuse.
