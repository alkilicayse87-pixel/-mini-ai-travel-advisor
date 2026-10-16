# Frontend

Plain HTML/CSS/JS chat UI (no build step). It talks to the Render API: `POST /chat` for the conversation and `POST /itinerary` for the structured plan, which it renders as tables. The conversation id (`response_id`) is kept in the browser.

- `config.js`: backend URL (`apiBase`).
- `vercel.json`: security headers for Vercel.
- Model output is rendered with `textContent` only (no `innerHTML`), and a Content-Security-Policy limits which hosts the page can call.

## Run locally

```
# terminal 1 (repo root)
uvicorn app.api:app --reload
# terminal 2
python -m http.server 5500 --directory frontend
```

Open http://127.0.0.1:5500/?api=http://127.0.0.1:8000 (the `?api=` parameter overrides `config.js`).

## Deploy on Vercel

1. vercel.com → **Add New → Project** → import the GitHub repo.
2. **Root Directory:** `frontend`. **Framework Preset:** Other. No build command, no output directory.
3. Deploy. You get `https://<name>.vercel.app`.
4. In Render → service → **Environment**, set `ALLOWED_ORIGINS` to that exact URL (no trailing slash) so only your site can call the API from a browser, then save.
5. If your Render URL ever changes, update `config.js` and the `connect-src` in `index.html`.
