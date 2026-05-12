<div align="center">

# 🏦 Finexa — AI Finance Agent
![FinexaLogo](logofinexa.png)

### _Your business accountant, living inside Telegram._

**Send a message. Your finances are recorded, validated, categorised, and analysed — automatically.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-Agent-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=for-the-badge)](https://groq.com)
[![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)
[![Google Sheets](https://img.shields.io/badge/Google_Sheets-Database-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)](https://sheets.google.com)

<br/>

> _Built for Egyptian small businesses. Works in Arabic, English, or both._  
> _$0/month for local use. ~$1–3/month for 24/7 cloud deployment._

</div>

---

## 📌 The Problem This Solves

Small business owners lose money in three ways they rarely talk about:

| Problem | Real Cost |
|---|---|
| **Manual bookkeeping errors** | Mis-categorised expenses, wrong dates, duplicate entries — invisible until tax season |
| **Delayed recording** | Transactions recorded hours or days late introduce cash flow blind spots |
| **No real-time visibility** | Owners make purchasing decisions without knowing their actual financial position |
| **Accounting software friction** | Opening QuickBooks to log a 50 EGP expense takes longer than the transaction itself |
| **Hiring a bookkeeper** | A part-time human bookkeeper costs 1,500–3,000 EGP/month and still makes errors |

**Finexa eliminates all five.** You send one Telegram message. The system does everything else.

---

## ✨ What Finexa Does

```
You:      "دفعت 1500 إيجار النهارده"
Finexa:   ✅ Expense logged — 1,500 EGP · Rent · Acc. 5100 · Pending
          [Confirm] [Edit] [Undo]

You:      *taps Confirm*
Finexa:   ✅ Confirmed — saved to Google Sheets. Budget: Rent 75% used (1,500/2,000 EGP)
```

That's it. One message. Full double-entry bookkeeping entry created automatically.

---

## 💰 Real Cost Reduction — By the Numbers

### Before Finexa (Typical SME)

| Cost Item | Monthly Cost |
|---|---|
| Part-time bookkeeper | 2,000 EGP |
| Accounting software subscription | 200–500 EGP |
| Error correction time (owner's hours) | ~3 hrs × 150 EGP/hr = 450 EGP |
| Delayed decisions due to no real-time data | Unquantified, but real |
| **Total** | **~2,650–3,000 EGP/month** |

### After Finexa

| Cost Item | Monthly Cost |
|---|---|
| Groq API (LLM inference) | ~0 EGP (free tier covers typical usage) |
| Railway deployment | ~55 EGP (~$1.50/month) |
| Google Sheets | 0 EGP (free) |
| Owner's recording time | 5 seconds per transaction |
| **Total** | **~55 EGP/month** |

> **Savings: up to 2,945 EGP/month. Payback period: immediate.**

---

## 🧠 How Human Error Is Eliminated — Technically

Every transaction goes through a **5-rule validation pipeline** before touching the database:

```
Rule 1: Missing amount?          → Hard reject. Ask user to resend.
Rule 2: Missing date?            → Auto-fill with today's date. Never wrong.
Rule 3: Missing currency?        → Default to EGP. Correct for 98% of transactions.
Rule 4: Confidence score < 0.6?  → Ask for clarification. Never guess.
Rule 5: Missing critical fields? → Re-prompt. Never store incomplete data.
```

On top of this, the **Adaptive Memory System** learns from every confirmed transaction:

```
First time you say "نت":    confidence = 79%  → asks for confirmation
After 5 confirmations:       confidence = 95%  → logs automatically with full confidence
```

The system gets smarter the more you use it. Human error goes down over time, automatically.

---

## 🏗️ Architecture — Full Technical Deep Dive

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUTS                             │
│         Text (Arabic/English) · Voice Note · Receipt Photo      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT LAYER                           │
│  telegram_bot.py — receives all update types, routes to handler │
│  · Typing indicator fires instantly (UX)                        │
│  · Duplicate detection (same amount+category within 60s)        │
│  · Button-driven edit flow (no typing field names)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         [Text msg]   [Voice note]  [Photo/receipt]
              │            │            │
              │      Groq Whisper   Groq Vision
              │      (STT → text)  (OCR → text)
              └────────────┴────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MEMORY MODULE                               │
│  memory.py — checks message keywords against Memory sheet       │
│  · On match: injects hint into LLM prompt                       │
│  · Confidence formula: min(0.95, 0.75 + uses × 0.04)           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AI AGENT CORE                               │
│  agent.py — Classify-then-Dispatch pattern (NOT ReAct)          │
│                                                                 │
│  ONE LLM call → JSON response → direct tool dispatch            │
│                                                                 │
│  Intent options:  log · summary · query · budget · unknown      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┼─────────────┬──────────────┐
              ▼            ▼             ▼              ▼
       [log_transaction] [get_summary] [query_txns] [check_budget]
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION PIPELINE                          │
│  tools.py — 5 rules enforced before any write operation         │
│  COA lookup: built-in dict → Sheet keywords → type default      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GOOGLE SHEETS                               │
│  sheets.py — singleton client, all read/write operations        │
│  6 tabs: Transactions · COA · Categories · Statements ·         │
│           Dashboard · Memory                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

### Why Classify-then-Dispatch (Not ReAct)?

Most AI agent frameworks use a **ReAct loop** — the model reasons, calls a tool, reasons again, calls another tool, and so on. This works well with GPT-4 or Claude-grade models.

Finexa uses **Classify-then-Dispatch** instead, and the reason is deliberate:

| Factor | ReAct Loop | Classify-Dispatch (Finexa) |
|---|---|---|
| Works with small models (7B) | ❌ Often loops infinitely | ✅ Always terminates |
| Latency | High (multiple round trips) | Low (one LLM call) |
| Cost | High (many tokens) | Minimal |
| Predictability | Unpredictable | Deterministic |
| Debug-ability | Hard | Easy — inspect one JSON |

The LLM receives a carefully engineered prompt that forces a JSON-only response:

```
You are a finance assistant for Egyptian small businesses.
Read the user message and return ONLY a valid JSON object.

Schema: { "intent": "log|summary|query|budget|unknown", "params": {...} }

For log intent, extract:
  amount (REQUIRED), txn_type (Expense/Income/Transfer),
  category (infer from context), payment_method (Cash/Card/Bank Transfer),
  description, txn_date (YYYY-MM-DD or empty), currency (EGP/USD/EUR),
  confidence_score (0.0-1.0), notes

Arabic hints: دفعت=Expense, استلمت=Income, إيجار=Rent,
أكل=Food, نت=Internet, راتب=Salary, كاش=Cash, كارت=Card
```

The JSON response is parsed, validated, and dispatched to the correct tool in a single Python function call. Zero loops. Zero ambiguity.

---

### The Adaptive Memory System

Every time a user taps **Confirm** on a transaction, the system:

1. Extracts keywords from the transaction description
2. Saves them to the Memory sheet with a usage counter
3. On the next message, matches keywords before calling the LLM
4. If matched, injects a hint: `keyword 'uber' → category=Transportation, confidence=0.91`

The confidence formula scales with usage:

```
confidence = min(0.95, 0.75 + (times_confirmed × 0.04))

1 confirmation  → 79%  (asks user to verify)
2 confirmations → 83%
3 confirmations → 87%
5 confirmations → 95%  (maximum, logs automatically)
```

This means the system's accuracy compounds over time. The more it's used, the less work the user does.

---

### Chart of Accounts — 40+ Category Intelligence

Finexa uses standard double-entry accounting codes (1000–9999 convention) with a **3-tier lookup fallback**:

```
Tier 1: Built-in Python dict — 40+ categories, Arabic + English keywords
        "إيجار" → Code 5100, Rent Expense, Expense type

Tier 2: Google Sheets COA tab — user-extensible, custom keywords per row

Tier 3: Type-based default — if all else fails, use account type to assign code
```

Sample of the built-in intelligence:

| Code | Account | Keywords (Arabic + English) |
|---|---|---|
| 5100 | Rent Expense | rent, إيجار, lease |
| 5200 | Internet & Comms | internet, نت, wifi, phone, تليفون |
| 5300 | Food & Beverages | food, أكل, طعام, restaurant, meals |
| 5400 | Transportation | transport, مواصلات, uber, taxi, كريم |
| 5600 | Utilities | electricity, كهرباء, water, مية, فاتورة |
| 4100 | Salary Income | salary, راتب, مرتب |
| 4200 | Sales Revenue | sales, مبيعات, revenue |

---

### FastAPI — Why Not n8n?

The original design used n8n as the automation layer. It was replaced with a direct FastAPI webhook handler for these reasons:

| Factor | n8n | FastAPI (Finexa) |
|---|---|---|
| Free tier limits | 1 active trigger workflow | Unlimited |
| Process count | 2 (n8n + Python) | 1 |
| Concurrent users | Limited | Unlimited (async) |
| Deployment complexity | High | One `uvicorn` command |
| Business logic location | Split between n8n and Python | All in Python |
| Telegram input types | Needs custom nodes | Native handlers for text, voice, photo |

The result: one process, one command, one repo. Everything deploys together.

---

### LLM Provider Flexibility — One Line to Switch

```bash
# Local development — zero cost, full privacy
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b-instruct

# Production — 70B model, zero GPU required
LLM_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile
```

The same agent code handles both. No code changes. One environment variable.

---

## 📊 The Dashboard

Accessible at `/ui` from any browser. No login required. Auto-refreshes every 30 seconds.

```
┌──────────────────────────────────────────────────────────┐
│  KPI Cards: Revenue · Expenses · Net Profit · Pending    │
├───────────────────────────┬──────────────────────────────┤
│  Monthly Bar Chart        │  Expense Donut Chart         │
│  (6 months, income vs     │  (Top 8 categories,          │
│   expenses + profit line) │   colour-coded breakdown)    │
├───────────────────────────┴──────────────────────────────┤
│  30-day Cash Flow Trend (line chart, running position)   │
├───────────────────────────┬──────────────────────────────┤
│  Top Expense Categories   │  Budget Progress Bars        │
│  (horizontal bar, ranked) │  (spent vs monthly limit)    │
├───────────────────────────┴──────────────────────────────┤
│  🤖 AI Financial Analyst — one-click LLM narrative       │
│  "Your top cost this month is Internet (28% of expenses).│
│   Net profit is negative by 960 EGP. Consider..."        │
├──────────────────────────────────────────────────────────┤
│  Recent Transactions Table (with status badges)          │
└──────────────────────────────────────────────────────────┘
```

---

## 📁 Codebase — File by File

| File | What It Does |
|---|---|
| `main.py` | FastAPI app. All endpoints: `/webhook`, `/chat`, `/confirm`, `/edit`, `/summary`, `/dashboard`, `/ui`, `/diagnose`, `/health`. Registers Telegram commands on startup. |
| `agent.py` | Classify-dispatch AI agent. Builds LLM (Ollama or Groq), checks memory, makes one LLM call, dispatches to tool. Handles bilingual off-topic responses. |
| `telegram_bot.py` | All Telegram update handling. Text + commands, voice transcription, photo analysis, button edit flow, typing indicator, duplicate detection, undo flow. |
| `tools.py` | 4 LangChain tools: `log_transaction` (14 fields, 5 rules, COA lookup, budget check), `get_summary`, `query_transactions`, `check_budget`. |
| `sheets.py` | All Google Sheets I/O. Singleton client. 40+ COA mappings. Append, delete, update, query operations. |
| `memory.py` | Adaptive learning. Keyword extraction, Memory sheet read/write, confidence scaling formula. |
| `dashboard.py` | Data aggregation. Single function returns KPIs, 6 chart datasets, recent transactions. |
| `config.py` | All env vars. Provider switch. Constants. Credential handling for cloud. |
| `dashboard.html` | Single-file frontend. Chart.js, vanilla JS. Connects to FastAPI. Auto-detects its own API URL. |
| `startup_credentials.py` | Cloud credential handler. Reads `GOOGLE_CREDENTIALS_B64` or `GOOGLE_CREDENTIALS_JSON`, writes to `/tmp`, sets path. |
| `Procfile` | `uvicorn main:app --host 0.0.0.0 --port $PORT` — Railway reads this automatically. |

---

## 🔌 API Reference

**Base URL (local):** `http://localhost:8000`  
**Base URL (cloud):** `https://your-railway-url.up.railway.app`  
**Interactive docs:** `/docs` (Swagger UI, auto-generated)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status":"ok","provider":"groq","model":"..."}` |
| `GET` | `/ui` | Serves the full dashboard HTML |
| `GET` | `/dashboard` | All chart + KPI data in one JSON response |
| `POST` | `/ai-summary` | Body: `{"period":"this month"}` → LLM narrative |
| `POST` | `/webhook` | Telegram posts all updates here |
| `POST` | `/chat` | Body: `{"user_id":"x","message":"..."}` — direct agent test |
| `POST` | `/confirm/{txn_id}` | Marks a transaction Confirmed |
| `POST` | `/edit` | Updates one field of a transaction |
| `GET` | `/summary` | Financial totals, filterable by month |
| `GET` | `/diagnose` | Step-by-step Google Sheets connection test |

---

## 🗄️ Data Structure — 14-Field Transaction Schema

Every transaction stored in Google Sheets contains:

| Field | Type | Example |
|---|---|---|
| `transaction_id` | Auto-generated | `TXN-20260512075841-Q9OH` |
| `date` | YYYY-MM-DD | `2026-05-12` |
| `type` | Expense / Income / Transfer | `Expense` |
| `amount` | Number (always positive) | `1500` |
| `currency` | EGP / USD / EUR | `EGP` |
| `category` | String | `Rent` |
| `payment_method` | Cash / Card / Bank Transfer | `Cash` |
| `description` | String | `Monthly office rent` |
| `account_code` | 1000–9999 | `5100` |
| `account_name` | String | `Rent Expense` |
| `account_type` | Asset / Liability / Revenue / Expense | `Expense` |
| `confidence_score` | 0.0–1.0 | `0.91` |
| `status` | Pending / Confirmed / Cancelled | `Confirmed` |
| `notes` | String | `Q2 payment` |

---

## 🚀 Setup Guide

### Prerequisites

- Python 3.11+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Groq API key from [console.groq.com](https://console.groq.com) (free)
- A Google Cloud service account with Sheets API + Drive API enabled
- A Google Sheet with these 6 tabs: `Transactions`, `Chart of Accounts`, `Categories`, `Financial Statements`, `Dashboard`, `Memory`

---

## 🖥️ Option 1 — Local Development

Best for: testing, development, no always-on server available.

**Uses Ollama (free, local LLM) + ngrok (public tunnel for Telegram).**

### Step 1 — Clone and install

```bash
git clone https://github.com/eyadXE/FinexaAgent.git
cd FinexaAgent
python -m venv env
env\Scripts\activate          # Windows
# source env/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

### Step 2 — Pull the local model

```bash
ollama pull qwen2.5:7b-instruct
```

### Step 3 — Create your `.env` file

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app

LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

GROQ_API_KEY=your_groq_key       # needed for voice and photo features
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_WHISPER_MODEL=whisper-large-v3

GOOGLE_CREDENTIALS_PATH=C:/path/to/credentials.json
GOOGLE_SHEET_ID=your_sheet_id_from_url
```

### Step 4 — Set up Google Sheets

Create a Google Sheet and share it with your service account's `client_email` (found inside `credentials.json`) with **Editor** role. The sheet must have these tabs with exact names:

- `Transactions` — 14 column headers (see Data Structure above)
- `Chart of Accounts` — columns: Code, Name, Type, Keywords
- `Categories` — columns: Category, Arabic_Name, Account_Code
- `Financial Statements` — SUMIF formulas for Revenue, Expenses, Net Profit
- `Dashboard` — live KPI formulas
- `Memory` — managed automatically by the agent

### Step 5 — Run all three processes

Open three terminals:

```bash
# Terminal 1
ollama serve

# Terminal 2
python main.py

# Terminal 3
ngrok http 8000
```

Copy the ngrok URL (e.g. `https://abc123.ngrok-free.app`), paste it as `TELEGRAM_WEBHOOK_URL` in your `.env`, and restart the server.

### Step 6 — Verify

```
http://localhost:8000/health     → should show provider: ollama
http://localhost:8000/diagnose   → should show all Google Sheets checks passing
http://localhost:8000/ui         → dashboard loads
```

> ⚠️ **Limitation:** ngrok gives a new URL on every restart. You must update `TELEGRAM_WEBHOOK_URL` each time. Use Option 2 for a permanent URL.

---

## ☁️ Option 2 — Cloud Deployment (Railway)

Best for: production, 24/7 availability, permanent Telegram webhook, no laptop dependency.

**Uses Groq (free tier, 70B model in the cloud) + Railway (~$1.50/month).**

### Why Railway?

- Git-push deploys — every commit to `main` redeploys automatically
- Permanent HTTPS URL — your Telegram webhook never breaks
- No Docker knowledge required — Railway detects Python and uses the `Procfile`
- Built-in logs, metrics, and restart-on-failure

### The credentials challenge

Railway containers have no persistent filesystem — you cannot upload `credentials.json` as a file. The solution is to supply the credentials through an environment variable. Finexa supports two formats:

---

#### Credentials Option A — Raw JSON

1. Open `credentials.json` in any text editor
2. Copy the entire contents (the full JSON starting with `{`)
3. In Railway → **Variables** → add:

```
GOOGLE_CREDENTIALS_JSON = { "type": "service_account", "project_id": "...", ... }
```

---

#### Credentials Option B — Base64 Encoded _(recommended)_

Encoding avoids issues with special characters and newlines inside the private key.

**On Mac / Linux:**
```bash
base64 -i credentials.json | tr -d '\n'
# Copy the output — starts with eyJ...
```

**Using a browser tool:**  
Go to [base64encode.org](https://www.base64encode.org) → paste the JSON → click Encode → copy result.

Then in Railway → **Variables** → add:
```
GOOGLE_CREDENTIALS_B64 = eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsIC...
```

`startup_credentials.py` runs at container startup, detects whichever variable is set, decodes it, writes to `/tmp/google_credentials.json`, and sets `GOOGLE_CREDENTIALS_PATH`. No code changes needed.

---

### Step 1 — Deploy to Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select `FinexaAgent`
3. Let the first build complete (it will start, which is fine — variables come next)

### Step 2 — Generate your public domain

**Settings** → **Networking** → **Generate Domain** → enter port `8080` → **Generate**

Copy the URL (e.g. `https://finexaagent-production.up.railway.app`).

### Step 3 — Set all environment variables

Go to **Variables** tab and add:

```env
LLM_PROVIDER                = groq
GROQ_API_KEY                = gsk_...
GROQ_MODEL                  = llama-3.3-70b-versatile
GROQ_VISION_MODEL           = meta-llama/llama-4-scout-17b-16e-instruct
GROQ_WHISPER_MODEL          = whisper-large-v3
GOOGLE_SHEET_ID             = your_sheet_id_from_url
GOOGLE_CREDENTIALS_B64      = eyJ...    ← or use GOOGLE_CREDENTIALS_JSON
TELEGRAM_BOT_TOKEN          = your_token_from_botfather
TELEGRAM_WEBHOOK_URL        = https://finexaagent-production.up.railway.app
```

> ⚠️ Never commit any of these values to GitHub. Railway stores them encrypted.

Railway redeploys automatically after variables are saved.

### Step 4 — Verify the deployment

```
https://your-url.up.railway.app/health
→ {"status":"ok","provider":"groq","model":"llama-3.3-70b-versatile"}

https://your-url.up.railway.app/diagnose
→ all 5 checks should show OK

https://your-url.up.railway.app/ui
→ dashboard loads with your live data
```

---

## 💵 Cost Breakdown

| Component | Local Dev | Cloud (Railway) |
|---|---|---|
| Ollama + Qwen2.5-7B (text) | Free | N/A |
| Groq LLaMA-3.3-70B (text) | Free tier (100K tokens/day) | Free tier sufficient |
| Groq Whisper (voice/min) | ~$0.0001 | ~$0.0001 |
| Groq Vision (photo) | ~$0.0001 | ~$0.0001 |
| Google Sheets API | Free (5M cells/sheet) | Free |
| Railway | Not needed | ~$1.50/month |
| **Total** | **$0/month** | **~$1.50/month** |

---

## 📋 Feature Checklist

| Feature | Status |
|---|---|
| Text input (Arabic + English + mixed) | ✅ |
| Voice note → automatic transcription | ✅ |
| Photo / receipt → automatic extraction | ✅ |
| Intent classification (log / summary / query / budget) | ✅ |
| 14-field transaction extraction | ✅ |
| 5-rule validation pipeline | ✅ |
| Adaptive memory (learns from confirmations) | ✅ |
| 40+ category COA with Arabic keywords | ✅ |
| 3-tier COA fallback | ✅ |
| Telegram confirm / edit / undo buttons | ✅ |
| Duplicate detection (60-second window) | ✅ |
| Budget alerts (auto-fires at 80% threshold) | ✅ |
| Real-time dashboard (6 charts) | ✅ |
| AI financial analyst narrative | ✅ |
| Income statement + cash flow | ✅ |
| Month / all-time filters | ✅ |
| `/report`, `/history`, `/budget`, `/help` commands | ✅ |
| Ollama (local, free) | ✅ |
| Groq (cloud, 70B, one env var) | ✅ |
| Railway one-click deploy | ✅ |

---

## 🛣️ Roadmap

**Short term**
- Per-user isolation — each Telegram `user_id` gets its own data range
- `/delete` command for removing transactions by ID
- Rate limiting per user

**Medium term**
- PostgreSQL backend (Supabase free tier) for concurrent writes at scale
- Monthly PDF reports auto-sent on the 1st via Telegram
- Multi-currency with live EGP exchange rates
- Receipt photos stored in Google Drive alongside transactions

**Long term**
- WhatsApp channel via Twilio (same backend, second interface)
- Multi-tenant SaaS mode — each business gets an isolated environment
- Proactive Telegram alerts — budget warnings, unusual spending, month-end summaries
- Export to QuickBooks / Xero formats

---

## 🧰 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| AI / LLM (local) | Ollama + Qwen2.5-7B | Zero cost, full privacy, JSON-mode output |
| AI / LLM (cloud) | Groq + LLaMA-3.3-70B | Fastest inference available, generous free tier |
| Speech-to-Text | Groq Whisper | Best open-source STT, Arabic support |
| Vision / OCR | Groq Llama-4-Scout | Multimodal, handles Arabic text in images |
| Backend | FastAPI | Async, auto-generates Swagger, lightweight |
| Bot interface | httpx (direct API calls) | Full control, async-compatible, no heavy library |
| AI framework | LangChain + LangGraph | Tool binding, message formatting |
| Database | Google Sheets | Zero infrastructure, client-visible, formulas built-in |
| Auth | Google Service Account | Secure programmatic access, no OAuth flow |
| Frontend | Chart.js + vanilla JS | Single HTML file, no build step, fast |
| Deployment | Railway | Git-push deploy, permanent HTTPS, ~$1.50/month |
| Dev tunnel | ngrok | Local development only |

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first.


---

<div align="center">

**Built for Egyptian small businesses. Runs anywhere. Costs almost nothing.**

[GitHub](https://github.com/eyadXE/FinexaAgent) · [Live Demo](https://finexaagent-production.up.railway.app/ui) 

</div>
