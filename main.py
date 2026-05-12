import startup_credentials  # noqa: F401
"""main.py — FastAPI app with built-in Telegram webhook. No n8n needed."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
import os, pathlib
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn

import agent as agent_module
import sheets
import telegram_bot as tg
from config import TELEGRAM_WEBHOOK_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔧 Warming up agent...")
    agent_module.warmup()
    if TELEGRAM_WEBHOOK_URL:
        ok = await tg.set_webhook(TELEGRAM_WEBHOOK_URL)
        print(f"{'✅' if ok else '❌'} Webhook → {TELEGRAM_WEBHOOK_URL}/webhook")
    else:
        await tg.delete_webhook()
        print("ℹ️  No TELEGRAM_WEBHOOK_URL — test via POST /chat or /docs")
    # Register Telegram bot commands menu
    try:
        await tg._tg_post("setMyCommands", {"commands": [
            {"command": "start",   "description": "Welcome + how to use"},
            {"command": "report",  "description": "This month financial summary"},
            {"command": "history", "description": "Last 10 transactions"},
            {"command": "budget",  "description": "Budget status this month"},
            {"command": "help",    "description": "Show all commands"},
        ]})
        print("✅ Bot commands registered")
    except Exception as e:
        print(f"⚠️  Could not register commands: {e}")

    yield
    print("👋 Shutting down.")


app = FastAPI(title="Finexa AI Finance Recorder", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: list[dict] | None = None

class ChatResponse(BaseModel):
    reply: str
    user_id: str

class ConfirmRequest(BaseModel):
    user_id: str

class EditRequest(BaseModel):
    txn_id: str
    field:  str
    value:  str
    user_id: str


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Receives all Telegram updates — text, voice, photo, button taps."""
    update = await request.json()
    await tg.handle_update(update)
    return {"ok": True}


@app.get("/health")
def health():
    from config import LLM_PROVIDER, GROQ_MODEL, OLLAMA_MODEL
    return {"status": "ok", "provider": LLM_PROVIDER,
            "model": GROQ_MODEL if LLM_PROVIDER == "groq" else OLLAMA_MODEL}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Direct test endpoint — no Telegram needed."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    try:
        reply = agent_module.chat(req.message, req.history)
    except Exception as e:
        reply = f"❌ Error: {e}"
    return ChatResponse(reply=reply, user_id=req.user_id)


@app.post("/confirm/{txn_id}")
def confirm_transaction(txn_id: str, req: ConfirmRequest):
    ok = sheets.update_transaction_field(txn_id, "status", "Confirmed")
    if not ok:
        raise HTTPException(status_code=404, detail=f"{txn_id} not found")
    return {"message": f"✅ {txn_id} confirmed.", "status": "Confirmed"}


@app.post("/edit")
def edit_transaction(req: EditRequest):
    valid = {"amount","date","type","currency","category","payment_method","description","notes"}
    if req.field not in valid:
        raise HTTPException(status_code=400, detail=f"Field '{req.field}' not editable.")
    ok = sheets.update_transaction_field(req.txn_id, req.field, req.value)
    if not ok:
        raise HTTPException(status_code=404, detail=f"{req.txn_id} not found")
    return {"message": f"✏️ {req.field} → '{req.value}' on {req.txn_id}"}


@app.get("/summary")
def quick_summary(month: str = ""):
    try:
        return sheets.get_summary(month=month or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/diagnose")
def diagnose():
    import traceback
    results = {}
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID, SHEET_TRANSACTIONS
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds  = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        client = gspread.authorize(creds)
        results["1_credentials"] = "OK"
        sp = client.open_by_key(GOOGLE_SHEET_ID)
        results["2_open_sheet"] = "OK"
        results["3_tabs_found"] = [ws.title for ws in sp.worksheets()]
        ws = sp.worksheet(SHEET_TRANSACTIONS)
        results["4_transactions_tab"] = "OK"
        ws.append_row(["__TEST__"], value_input_option="USER_ENTERED")
        ws.delete_rows(len(ws.get_all_values()))
        results["5_write_test"] = "OK"
    except Exception as e:
        results["error"] = str(e)
        results["trace"] = traceback.format_exc()
    return results


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


# ── Dashboard ──────────────────────────────────────────────────────────────────
@app.get("/dashboard")
def dashboard_data():
    """All chart + KPI data for the dashboard in one call."""
    try:
        import dashboard as dash
        return dash.get_dashboard_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── AI Summarizer ──────────────────────────────────────────────────────────────
from pydantic import BaseModel as BM

class SummaryRequest(BM):
    period: str = "this month"

@app.post("/ai-summary")
def ai_summary(req: SummaryRequest):
    """Generate an AI narrative summary of financial performance."""
    try:
        import dashboard as dash
        data = dash.get_dashboard_data()
        k    = data["kpis"]
        cats = data["categories"]
        top_cats = ", ".join([f"{c['name']} ({c['value']:,.0f} EGP)" for c in cats[:5]])
        prompt = (
            f"You are a financial advisor for an Egyptian small business. "
            f"Write a concise 3-paragraph professional summary in English of their finances for {req.period}. "
            f"Data: Revenue={k['month_income']:,.0f} EGP, Expenses={k['month_expense']:,.0f} EGP, "
            f"Net Profit={k['month_profit']:,.0f} EGP, Total transactions={k['total_txns']}, "
            f"Pending confirmations={k['pending_count']}. "
            f"Top expense categories: {top_cats}. "
            f"Paragraph 1: Overall performance. Paragraph 2: Top spending areas and concerns. "
            f"Paragraph 3: One specific actionable recommendation. Keep it professional and concise."
        )
        reply = agent_module.chat(prompt)
        return {"summary": reply, "kpis": k, "top_categories": cats[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug-transactions")
def debug_transactions():
    """Show raw transaction data to diagnose zero-summary bug."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID, SHEET_TRANSACTIONS
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds  = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        client = gspread.authorize(creds)
        ws     = client.open_by_key(GOOGLE_SHEET_ID).worksheet(SHEET_TRANSACTIONS)
        all_values = ws.get_all_values()
        records    = ws.get_all_records()
        return {
            "row_count":       len(all_values),
            "header_row":      all_values[0] if all_values else [],
            "first_3_raw":     all_values[1:4] if len(all_values) > 1 else [],
            "first_3_records": records[:3],
            "sample_types":    list({r.get("type","") for r in records[:20]}),
            "sample_amounts":  [r.get("amount","") for r in records[:5]],
            "sample_dates":    [r.get("date","") for r in records[:5]],
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@app.post("/fix-account-codes")
def fix_account_codes():
    """
    One-time fix: re-apply correct COA lookup to all existing transactions
    that have wrong account codes (e.g. Rent showing 5000 instead of 5100).
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID, SHEET_TRANSACTIONS, TRANSACTION_FIELDS
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds  = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        ws     = gspread.authorize(creds).open_by_key(GOOGLE_SHEET_ID).worksheet(SHEET_TRANSACTIONS)

        records    = ws.get_all_records()
        fixed      = []
        code_col   = TRANSACTION_FIELDS.index("account_code") + 1
        name_col   = TRANSACTION_FIELDS.index("account_name") + 1
        type_col   = TRANSACTION_FIELDS.index("account_type") + 1

        for i, r in enumerate(records, start=2):   # row 1 is header
            cat      = str(r.get("category",""))
            txn_type = str(r.get("type","Expense"))
            coa      = sheets.lookup_coa(cat, txn_type)
            old_code = str(r.get("account_code",""))
            if old_code != coa["account_code"]:
                ws.update_cell(i, code_col, coa["account_code"])
                ws.update_cell(i, name_col, coa["account_name"])
                ws.update_cell(i, type_col, coa["account_type"])
                fixed.append({"row": i, "category": cat,
                               "old": old_code, "new": coa["account_code"],
                               "name": coa["account_name"]})

        return {"fixed": len(fixed), "details": fixed}
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=str(e))


# ── Serve dashboard at /ui ─────────────────────────────────────────────────────
@app.get("/ui", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    """
    Serve the dashboard HTML with the correct API URL auto-injected.
    Accessible at: https://your-railway-url.up.railway.app/ui
    """
    # Find dashboard.html (same folder as main.py)
    here = pathlib.Path(__file__).parent
    candidates = [
        here / "dashboard.html",
        here.parent / "dashboard.html",
        pathlib.Path("/mnt/user-data/outputs/dashboard.html"),
    ]
    html_path = next((p for p in candidates if p.exists()), None)

    if not html_path:
        return HTMLResponse("<h2>dashboard.html not found — place it in the same folder as main.py</h2>", status_code=404)

    html = html_path.read_text(encoding="utf-8")

    # Auto-inject the correct API base URL so it works when deployed
    base_url = str(request.base_url).rstrip("/")
    html = html.replace(
        'value="http://localhost:8000"',
        f'value="{base_url}"',
    )
    return HTMLResponse(content=html)
