# AI Finance Recorder — Phase 3: LangGraph Agent

## File structure

```
finance-agent/
├── main.py          # FastAPI app (5 endpoints)
├── agent.py         # LangGraph ReAct agent
├── tools.py         # 4 tools: log, summary, query, budget
├── sheets.py        # Google Sheets read/write client
├── config.py        # Environment config + constants
├── requirements.txt
└── .env.example     # Copy this to .env and fill in your keys
```

---

## Setup (one time)

### 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### 2 — Get your Groq API key
Go to https://console.groq.com → create account → API Keys → Create key  
Free tier handles thousands of requests/day.

### 3 — Set up Google Sheets API
1. Go to https://console.cloud.google.com
2. Create a new project → Enable **Google Sheets API** + **Google Drive API**
3. Create a **Service Account** → download the JSON key file
4. Save the JSON file as `credentials.json` in this folder
5. Open your Google Sheet → Share it with the service account email

### 4 — Create your .env file
```bash
cp .env.example .env
# Then edit .env and fill in:
#   GROQ_API_KEY=...
#   GOOGLE_SHEET_ID=...   (from the Sheet URL)
```

### 5 — Set up the Google Sheet tabs
Your Sheet needs these exact tab names:
- `Transactions`     — 14 columns (see config.py TRANSACTION_FIELDS)
- `Chart of Accounts` — columns: Code, Name, Type, Keywords
- `Categories`       — columns: Category, Arabic_Name, Account_Code
- `Settings`         — columns: Category, Monthly_Limit
- `Financial Statements` — formulas (added manually or via script)

**Transactions tab header row (row 1):**
```
transaction_id | date | type | amount | currency | category | payment_method | description | account_code | account_name | account_type | confidence_score | status | notes
```

**Chart of Accounts sample rows:**
```
Code  | Name              | Type    | Keywords
1000  | Cash & Equivalents| Asset   | cash,كاش,نقدي
4000  | Sales Revenue     | Revenue | sales,revenue,income,راتب,مرتب,salary
5100  | Internet & Comms  | Expense | internet,نت,wifi,communications
5200  | Rent Expense      | Expense | rent,إيجار,lease
5300  | Food & Beverages  | Expense | food,أكل,طعام,restaurant
5400  | Transportation    | Expense | transport,مواصلات,uber,taxi,كريم
```

**Settings tab sample rows:**
```
Category    | Monthly_Limit
Rent        | 5000
Internet    | 500
Food        | 3000
Transport   | 1000
```

---

## Run the server
```bash
python main.py
# Server starts at http://localhost:8000
# Auto-reload is ON during development
```

---

## Test with curl

### Health check
```bash
curl http://localhost:8000/health
```

### Log a text transaction (Arabic)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "دفعت 750 جنيه إيجار بالكارت"
  }'
```

### Log a transaction (English)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "paid 200 EGP for internet by card"
  }'
```

### Income transaction
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "استلمت مرتب 8000 جنيه"
  }'
```

### Get monthly summary
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "show me this month summary"
  }'
```

### Query past transactions
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "show all my rent expenses"
  }'
```

### Check budget
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "هل تجاوزت الميزانية؟"
  }'
```

### Confirm a transaction (inline button)
```bash
curl -X POST http://localhost:8000/confirm/TXN-20250115120000-AB3C \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'
```

### Edit a field
```bash
curl -X POST http://localhost:8000/edit \
  -H "Content-Type: application/json" \
  -d '{
    "txn_id": "TXN-20250115120000-AB3C",
    "field": "category",
    "value": "Rent",
    "user_id": "test_user"
  }'
```

### Quick summary (no agent)
```bash
curl "http://localhost:8000/summary?month=2025-01"
```

---

## API docs (auto-generated)
Open http://localhost:8000/docs in your browser — FastAPI generates
interactive Swagger docs automatically. You can test every endpoint there.

---

## What n8n sends to /chat
```json
{
  "user_id": "{{$json.message.from.id}}",
  "message": "{{$json.cleanText}}"
}
```
Where `cleanText` is the output of the STT or vision pre-processing node.
The agent's `reply` field goes directly to the Telegram Send Message node.
