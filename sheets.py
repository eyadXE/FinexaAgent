"""sheets.py — All Google Sheets read / write operations.

One module owns the Sheets connection so the rest of the codebase
never imports gspread directly.
"""

import gspread
import random
import string
from datetime import datetime, date
from typing import Any
from google.oauth2.service_account import Credentials

from config import (
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SHEET_ID,
    SHEET_TRANSACTIONS,
    SHEET_COA,
    SHEET_CATEGORIES,
    SHEET_SETTINGS,
    TRANSACTION_FIELDS,
)

# ── Auth scopes ────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Singleton client ───────────────────────────────────────────────────────────
_client: gspread.Client | None = None


def _get_client() -> gspread.Client:
    global _client
    if _client is None:
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
        )
        _client = gspread.authorize(creds)
    return _client


def _sheet(tab_name: str) -> gspread.Worksheet:
    """Return a worksheet by tab name."""
    return _get_client().open_by_key(GOOGLE_SHEET_ID).worksheet(tab_name)


# ── ID generation ──────────────────────────────────────────────────────────────
def _generate_txn_id() -> str:
    ts    = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    rand  = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"TXN-{ts}-{rand}"


# ── Built-in category → COA map (works without Sheet keywords) ─────────────────
_BUILTIN_COA: dict[str, dict] = {
    # ── Revenue (4xxx) ───────────────────────────────────────────────
    "salary":          {"account_code":"4100","account_name":"Salary Income",       "account_type":"Revenue"},
    "مرتب":            {"account_code":"4100","account_name":"Salary Income",       "account_type":"Revenue"},
    "راتب":            {"account_code":"4100","account_name":"Salary Income",       "account_type":"Revenue"},
    "sales":           {"account_code":"4200","account_name":"Sales Revenue",       "account_type":"Revenue"},
    "مبيعات":          {"account_code":"4200","account_name":"Sales Revenue",       "account_type":"Revenue"},
    "freelance":       {"account_code":"4300","account_name":"Freelance Income",    "account_type":"Revenue"},
    "consulting":      {"account_code":"4300","account_name":"Consulting Income",   "account_type":"Revenue"},
    "investment":      {"account_code":"4400","account_name":"Investment Income",   "account_type":"Revenue"},
    "rental income":   {"account_code":"4500","account_name":"Rental Income",       "account_type":"Revenue"},
    # ── Operating expenses (5xxx) ────────────────────────────────────
    "rent":            {"account_code":"5100","account_name":"Rent Expense",        "account_type":"Expense"},
    "إيجار":           {"account_code":"5100","account_name":"Rent Expense",        "account_type":"Expense"},
    "internet":        {"account_code":"5200","account_name":"Internet & Comms",    "account_type":"Expense"},
    "نت":              {"account_code":"5200","account_name":"Internet & Comms",    "account_type":"Expense"},
    "إنترنت":          {"account_code":"5200","account_name":"Internet & Comms",    "account_type":"Expense"},
    "phone":           {"account_code":"5200","account_name":"Phone & Comms",       "account_type":"Expense"},
    "تليفون":          {"account_code":"5200","account_name":"Phone & Comms",       "account_type":"Expense"},
    "food":            {"account_code":"5300","account_name":"Food & Beverages",    "account_type":"Expense"},
    "أكل":             {"account_code":"5300","account_name":"Food & Beverages",    "account_type":"Expense"},
    "طعام":            {"account_code":"5300","account_name":"Food & Beverages",    "account_type":"Expense"},
    "meals":           {"account_code":"5300","account_name":"Food & Beverages",    "account_type":"Expense"},
    "restaurant":      {"account_code":"5300","account_name":"Food & Beverages",    "account_type":"Expense"},
    "transportation":  {"account_code":"5400","account_name":"Transportation",      "account_type":"Expense"},
    "مواصلات":         {"account_code":"5400","account_name":"Transportation",      "account_type":"Expense"},
    "uber":            {"account_code":"5400","account_name":"Transportation",      "account_type":"Expense"},
    "taxi":            {"account_code":"5400","account_name":"Transportation",      "account_type":"Expense"},
    "كريم":            {"account_code":"5400","account_name":"Transportation",      "account_type":"Expense"},
    "fuel":            {"account_code":"5400","account_name":"Fuel & Transport",    "account_type":"Expense"},
    "بنزين":           {"account_code":"5400","account_name":"Fuel & Transport",    "account_type":"Expense"},
    "office supplies": {"account_code":"5500","account_name":"Office Supplies",     "account_type":"Expense"},
    "supplies":        {"account_code":"5500","account_name":"Office Supplies",     "account_type":"Expense"},
    "utilities":       {"account_code":"5600","account_name":"Utilities",           "account_type":"Expense"},
    "electricity":     {"account_code":"5600","account_name":"Electricity Bill",    "account_type":"Expense"},
    "كهرباء":          {"account_code":"5600","account_name":"Electricity Bill",    "account_type":"Expense"},
    "water":           {"account_code":"5600","account_name":"Water Bill",          "account_type":"Expense"},
    "مية":             {"account_code":"5600","account_name":"Water Bill",          "account_type":"Expense"},
    "bill":            {"account_code":"5600","account_name":"Utilities Bill",      "account_type":"Expense"},
    "فاتورة":          {"account_code":"5600","account_name":"Utilities Bill",      "account_type":"Expense"},
    "software":        {"account_code":"5700","account_name":"Software & Subscriptions","account_type":"Expense"},
    "subscription":    {"account_code":"5700","account_name":"Software & Subscriptions","account_type":"Expense"},
    "marketing":       {"account_code":"5800","account_name":"Marketing & Ads",     "account_type":"Expense"},
    "advertising":     {"account_code":"5800","account_name":"Marketing & Ads",     "account_type":"Expense"},
    "إعلانات":         {"account_code":"5800","account_name":"Marketing & Ads",     "account_type":"Expense"},
    "maintenance":     {"account_code":"5900","account_name":"Maintenance & Repairs","account_type":"Expense"},
    "صيانة":           {"account_code":"5900","account_name":"Maintenance & Repairs","account_type":"Expense"},
    "shopping":        {"account_code":"5950","account_name":"Shopping & Purchases", "account_type":"Expense"},
    "تسوق":            {"account_code":"5950","account_name":"Shopping & Purchases", "account_type":"Expense"},
    "health":          {"account_code":"5960","account_name":"Health & Medical",    "account_type":"Expense"},
    "medical":         {"account_code":"5960","account_name":"Health & Medical",    "account_type":"Expense"},
    "طب":              {"account_code":"5960","account_name":"Health & Medical",    "account_type":"Expense"},
    "education":       {"account_code":"5970","account_name":"Education & Training","account_type":"Expense"},
    "تعليم":           {"account_code":"5970","account_name":"Education & Training","account_type":"Expense"},
    # ── Assets (1xxx) ────────────────────────────────────────────────
    "cash":            {"account_code":"1000","account_name":"Cash & Equivalents",  "account_type":"Asset"},
    "bank":            {"account_code":"1100","account_name":"Bank Account",        "account_type":"Asset"},
    "transfer":        {"account_code":"1000","account_name":"Cash & Equivalents",  "account_type":"Asset"},
    "تحويل":           {"account_code":"1100","account_name":"Bank Transfer",       "account_type":"Asset"},
    "equipment":       {"account_code":"1500","account_name":"Equipment & Machinery","account_type":"Asset"},
    "معدات":           {"account_code":"1500","account_name":"Equipment & Machinery","account_type":"Asset"},
}

# ── COA lookup ────────────────────────────────────────────────────────────────
def lookup_coa(category: str, txn_type: str) -> dict[str, str]:
    """
    Return {account_code, account_name, account_type} for a category.
    Priority: 1) built-in map  2) Sheet keywords  3) type-based default
    """
    cat_low = category.lower().strip()

    # 1 — exact match in built-in map
    if cat_low in _BUILTIN_COA:
        return _BUILTIN_COA[cat_low]

    # 2 — partial match in built-in map
    for key, val in _BUILTIN_COA.items():
        if key in cat_low or cat_low in key:
            return val

    # 3 — try the Sheet's COA tab (if it has keywords filled in)
    try:
        ws      = _sheet(SHEET_COA)
        records = ws.get_all_records()
        for row in records:
            keywords = str(row.get("Keywords", "")).lower()
            name_low = str(row.get("Name", "")).lower()
            if cat_low in keywords or cat_low in name_low:
                return {
                    "account_code": str(row.get("Code", "")),
                    "account_name": str(row.get("Name", "")),
                    "account_type": str(row.get("Type", "")),
                }
    except Exception:
        pass

    # 4 — type-based fallback
    defaults = {
        "Income":   {"account_code":"4000","account_name":"General Revenue",   "account_type":"Revenue"},
        "Expense":  {"account_code":"5000","account_name":"General Expense",   "account_type":"Expense"},
        "Transfer": {"account_code":"1000","account_name":"Cash & Equivalents","account_type":"Asset"},
    }
    return defaults.get(txn_type, defaults["Expense"])


# ── Write a transaction row ────────────────────────────────────────────────────
def append_transaction(fields: dict[str, Any]) -> str:
    """
    Append one row to the Transactions tab.
    Returns the generated transaction_id.
    """
    txn_id = _generate_txn_id()
    fields["transaction_id"] = txn_id
    fields.setdefault("status", "Pending")

    # Build the row in the exact column order
    row = [str(fields.get(f, "")) for f in TRANSACTION_FIELDS]

    _sheet(SHEET_TRANSACTIONS).append_row(row, value_input_option="USER_ENTERED")
    return txn_id


# ── Update a single cell ───────────────────────────────────────────────────────
def update_transaction_field(txn_id: str, field: str, value: str) -> bool:
    """Find a row by transaction_id and update one field. Returns success flag."""
    ws   = _sheet(SHEET_TRANSACTIONS)
    cell = ws.find(txn_id)
    if not cell:
        return False
    col_index = TRANSACTION_FIELDS.index(field) + 1   # gspread is 1-indexed
    ws.update_cell(cell.row, col_index, value)
    return True


# ── Read transactions ──────────────────────────────────────────────────────────
def get_transactions(
    category: str | None = None,
    txn_type: str | None = None,
    month: str | None = None,       # "YYYY-MM"
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return filtered transaction records."""
    ws      = _sheet(SHEET_TRANSACTIONS)
    records = ws.get_all_records()          # list of {header: value}

    result = []
    for r in records:
        if category and category.lower() not in str(r.get("category", "")).lower():
            continue
        if txn_type and r.get("type", "").lower() != txn_type.lower():
            continue
        if month and not str(r.get("date", "")).startswith(month):
            continue
        result.append(r)

    return result[-limit:]   # most recent first (sheet is append-only)


# ── Summary totals ─────────────────────────────────────────────────────────────
def _resolve_month(month: str | None) -> str | None:
    """
    Convert natural language month references to YYYY-MM format.
    'this month', 'current month', 'الشهر ده' → '2026-05'
    Already correct format '2026-05' → '2026-05'
    Empty / None / 'all time' → None (means all-time)
    """
    import re
    from datetime import date
    if not month:
        return None
    m = month.strip().lower()
    # Natural language → current month
    if any(k in m for k in ["this month","current month","الشهر","هذا الشهر","الشهر ده","now","today"]):
        return date.today().strftime("%Y-%m")
    # Already YYYY-MM format
    if re.match(r"^\d{4}-\d{2}$", m):
        return m
    # YYYY-MM-DD → strip to month
    if re.match(r"^\d{4}-\d{2}-\d{2}$", m):
        return m[:7]
    # Anything else (e.g. "all time", "total") → all-time
    return None


def get_summary(month: str | None = None) -> dict[str, float]:
    """
    Return {total_income, total_expense, net_profit,
            cash_in, cash_out, net_cash} for the given month (or all time).
    """
    resolved = _resolve_month(month)
    records  = get_transactions(month=resolved)

    income  = sum(float(r.get("amount", 0)) for r in records if r.get("type") == "Income")
    expense = sum(float(r.get("amount", 0)) for r in records if r.get("type") == "Expense")

    return {
        "total_income":  income,
        "total_expense": expense,
        "net_profit":    income - expense,
        "cash_in":       income,
        "cash_out":      expense,
        "net_cash":      income - expense,
        "period":        resolved or "all time",
    }


# ── Budget check ───────────────────────────────────────────────────────────────
def get_budget_status(month: str | None = None) -> list[dict[str, Any]]:
    """
    Compare current-month spending per category against limits in Settings tab.
    Returns list of {category, spent, limit, pct, over_threshold}.
    """
    if not month:
        month = date.today().strftime("%Y-%m")

    records = get_transactions(txn_type="Expense", month=month)

    # Tally spending per category
    spending: dict[str, float] = {}
    for r in records:
        cat = r.get("category", "Uncategorized")
        spending[cat] = spending.get(cat, 0.0) + float(r.get("amount", 0))

    # Read limits from Settings tab
    limits: dict[str, float] = {}
    try:
        ws = _sheet(SHEET_SETTINGS)
        for row in ws.get_all_records():
            if row.get("Category") and row.get("Monthly_Limit"):
                limits[row["Category"]] = float(row["Monthly_Limit"])
    except Exception:
        pass

    results = []
    for cat, spent in spending.items():
        limit = limits.get(cat, 0.0)
        pct   = (spent / limit) if limit > 0 else 0.0
        results.append({
            "category":      cat,
            "spent":         spent,
            "limit":         limit,
            "pct":           round(pct, 2),
            "over_threshold": pct >= 0.80,
        })

    return sorted(results, key=lambda x: x["pct"], reverse=True)


# ── Delete a transaction row ───────────────────────────────────────────────────
def delete_transaction(txn_id: str) -> bool:
    """
    Permanently delete a transaction row by its ID.
    Returns True if found and deleted, False if not found.
    """
    ws   = _sheet(SHEET_TRANSACTIONS)
    cell = ws.find(txn_id)
    if not cell:
        return False
    ws.delete_rows(cell.row)
    return True