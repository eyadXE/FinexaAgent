# Running FinexaAgent locally (Windows)

This build uses **local JSON storage instead of Google Sheets** (no Google
Cloud service account needed) and **Groq** as the LLM provider. A real
Telegram bot token is already configured — one manual step (ngrok) is all
that's left to wire up real Telegram chat.

## 1. Setup

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

`.env` is already present in this folder with:
- `TELEGRAM_BOT_TOKEN` — a real bot token (already registered with @BotFather)
- `LLM_PROVIDER=groq` + `GROQ_API_KEY` — a real Groq key
- `GOOGLE_SHEET_ID` — intentionally blank (this build doesn't use Google Sheets)

Demo data (21 transactions across Rent/Food/Internet/Transportation/Marketing/
Shopping/Salary/Freelance, spanning the last ~3 months) and budget limits are
already seeded into `data/`. To reset/reseed:

```
.venv\Scripts\python seed_demo_data.py --reset
```

## 2. Run the server

```
.venv\Scripts\uvicorn main:app --port 8000
```

Open:
- **Dashboard UI:** http://localhost:8000/ui
- **Landing page:** http://localhost:8000/
- **API docs:** http://localhost:8000/docs

## 3. Demo the agent via `/chat` (no Telegram needed)

This is the simplest way to demo the AI pipeline for a recording — POST to
`/chat`, no bot/webhook setup required:

```
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" ^
  -d "{\"user_id\":\"demo\",\"message\":\"paid 200 EGP for internet by card\"}"
```

Scripted walkthrough (all verified working):

1. **Log an expense (Arabic):** `دفعت 1500 إيجار النهارده` → records a Rent expense, shows the COA account code, status Pending.
2. **Log income (Arabic):** `استلمت 5000 من عميل` → records Income, category inferred from context.
   - ⚠️ If testing via `curl` from a Windows terminal, don't pass Arabic text as an inline `-d '...'` argument — Git Bash mangles the encoding. Either use a UTF-8 JSON file with `curl --data-binary @file.json`, or test through `/docs` (Swagger UI) / the Telegram bot / the browser instead. This is a terminal quirk, not an app bug.
3. **Financial summary:** `how much did I spend this month` → real totals computed from local data.
4. **Budget check:** `am I overspending?` → flags Food, Internet, and Shopping as over 80% of their monthly limits (seeded data deliberately demonstrates this).
5. **Query history:** `show last 5 transactions` → lists real records.
6. **Off-topic:** `hello, what can you do?` → agent explains its capabilities instead of guessing.

Also try:
- `GET /dashboard` — full KPI/chart JSON (what the `/ui` page renders).
- `POST /ai-summary` with `{"period":"this month"}` — real Groq-generated financial narrative grounded in your local data.

## 4. Finishing the real Telegram bot (one manual step)

The bot token is real and already registers commands with Telegram on
startup. To get actual Telegram chat working (text/voice/photo, Confirm/Edit
buttons), you need a public HTTPS tunnel to your local server — this
requires exposing a local port to the internet, which is intentionally a
manual step you run yourself, not something done automatically for you:

**ngrok is already installed** (via winget) and **already has your ngrok
authtoken configured** from a previous session — you don't need to sign up
again. Just run:

```
ngrok http 8000
```

Copy the `https://...ngrok-free.app` URL it prints, then either:
- Add it to `.env` as `TELEGRAM_WEBHOOK_URL=https://your-url.ngrok-free.app` and restart `uvicorn`, **or**
- The next `uvicorn` restart will read it from `.env` automatically once set.

Once set, message your bot on Telegram directly — send a receipt-style
message, tap Confirm/Edit, try `/report`, `/history`, `/budget`.

> Note: `ngrok` gives a new URL every restart on the free tier — update
> `TELEGRAM_WEBHOOK_URL` and restart the server each time you restart ngrok.

## 5. Known limitations (real, not code bugs)

- **Photo/receipt scanning** (`GROQ_VISION_MODEL`) currently has no working
  model on this Groq account — the vision model previously documented
  (`meta-llama/llama-4-scout-17b-16e-instruct`) is no longer available via
  the Groq API as of this setup. Text and voice-note logging both work
  fully. If you want photo receipts working for the recording, check
  `https://console.groq.com/docs/models` for a current vision-capable model
  and update `GROQ_VISION_MODEL` in `.env`.
- **`GROQ_MODEL`** was updated from the README's `llama-3.3-70b-versatile`
  (also deprecated/removed from Groq) to `openai/gpt-oss-120b`, which is
  currently available and tested working for intent classification, tool
  dispatch, and the AI financial narrative.
- **Local storage is single-process, no locking** — fine for a local demo,
  not for concurrent production use. To go back to live Google Sheets later,
  reimplement the functions in `sheets.py` against `gspread` using
  `GOOGLE_CREDENTIALS_PATH`/`GOOGLE_SHEET_ID` — `tools.py`, `dashboard.py`,
  `agent.py`, and `telegram_bot.py` all call `sheets.py` by function name
  only and need no changes either way.
- **`/login`, `/diagnose`, `/debug-transactions`, `/fix-account-codes`** in
  `main.py` are leftover/admin endpoints that still assume a live Google
  Sheet (or, for `/login`, an unrelated Postgres `users` table that doesn't
  exist anywhere in this repo). They're not part of the documented feature
  set and aren't needed for the demo — they fail gracefully with a JSON
  error rather than crashing the server.
