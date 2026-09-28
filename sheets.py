"""sheets.py — Transaction storage, now backed by a local JSON file
(local_db.py) instead of live Google Sheets.

Same public function names/signatures as the original Sheets-backed
version, so tools.py / dashboard.py / telegram_bot.py need no changes.
To restore a live Google Sheets backend, reimplement these functions
against gspread using GOOGLE_CREDENTIALS_PATH / GOOGLE_SHEET_ID from
config.py — nothing else in the codebase needs to change.
"""

import random
import string
from datetime import datetime, date
from typing import Any

import local_db
from config import TRANSACTION_FIELDS

TRANSACTIONS_KEY = "transactions"
SETTINGS_KEY = "settings"


# ── ID generation ──────────────────────────────────────────────────────────────
def _generate_txn_id() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
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
    Priority: 1) built-in map  2) type-based default
    (Sheet-keyword tier removed — no live Sheet in local-storage mode.)
    """
    cat_low = category.lower().strip()

    if cat_low in _BUILTIN_COA:
        return _BUILTIN_COA[cat_low]

    for key, val in _BUILTIN_COA.items():
        if key in cat_low or cat_low in key:
            return val

    defaults = {
        "Income":   {"account_code":"4000","account_name":"General Revenue",   "account_type":"Revenue"},
        "Expense":  {"account_code":"5000","account_name":"General Expense",   "account_type":"Expense"},
        "Transfer": {"account_code":"1000","account_name":"Cash & Equivalents","account_type":"Asset"},
    }
    return defaults.get(txn_type, defaults["Expense"])


# ── Write a transaction row ────────────────────────────────────────────────────
def append_transaction(fields: dict[str, Any]) -> str:
    """Append one transaction record. Returns the generated transaction_id."""
    txn_id = _generate_txn_id()
    fields = dict(fields)
    fields["transaction_id"] = txn_id
    fields.setdefault("status", "Pending")

    record = {f: fields.get(f, "") for f in TRANSACTION_FIELDS}

    records = local_db.load(TRANSACTIONS_KEY, [])
    records.append(record)
    local_db.save(TRANSACTIONS_KEY, records)
    return txn_id


# ── Update a single field ──────────────────────────────────────────────────────
def update_transaction_field(txn_id: str, field: str, value: str) -> bool:
    """Find a record by transaction_id and update one field. Returns success flag."""
    records = local_db.load(TRANSACTIONS_KEY, [])
    for r in records:
        if r.get("transaction_id") == txn_id:
            r[field] = value
            local_db.save(TRANSACTIONS_KEY, records)
            return True
    return False


# ── Read transactions ──────────────────────────────────────────────────────────
def get_transactions(
    category: str | None = None,
    txn_type: str | None = None,
    month: str | None = None,       # "YYYY-MM"
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return filtered transaction records."""
    records = local_db.load(TRANSACTIONS_KEY, [])

    result = []
    for r in records:
        if category and category.lower() not in str(r.get("category", "")).lower():
            continue
        if txn_type and str(r.get("type", "")).lower() != txn_type.lower():
            continue
        if month and not str(r.get("date", "")).startswith(month):
            continue
        result.append(r)

    return result[-limit:]   # most recent first (append-only order)


# ── Summary totals ─────────────────────────────────────────────────────────────
def _resolve_month(month: str | None) -> str | None:
    """
    Convert natural language month references to YYYY-MM format.
    'this month', 'current month', 'الشهر ده' → current YYYY-MM
    Already correct format '2026-05' → '2026-05'
    Empty / None / 'all time' → None (means all-time)
    """
    import re
    if not month:
        return None
    m = month.strip().lower()
    if any(k in m for k in ["this month","current month","الشهر","هذا الشهر","الشهر ده","now","today"]):
        return date.today().strftime("%Y-%m")
    if re.match(r"^\d{4}-\d{2}$", m):
        return m
    if re.match(r"^\d{4}-\d{2}-\d{2}$", m):
        return m[:7]
    return None


def get_summary(month: str | None = None) -> dict[str, float]:
    """
    Return {total_income, total_expense, net_profit,
            cash_in, cash_out, net_cash} for the given month (or all time).
    """
    resolved = _resolve_month(month)
    records = get_transactions(month=resolved)

    income = sum(float(r.get("amount", 0) or 0) for r in records if r.get("type") == "Income")
    expense = sum(float(r.get("amount", 0) or 0) for r in records if r.get("type") == "Expense")

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
    Compare current-month spending per category against limits in the local
    settings store. Returns list of {category, spent, limit, pct, over_threshold}.
    """
    if not month:
        month = date.today().strftime("%Y-%m")

    records = get_transactions(txn_type="Expense", month=month)

    spending: dict[str, float] = {}
    for r in records:
        cat = r.get("category", "Uncategorized")
        spending[cat] = spending.get(cat, 0.0) + float(r.get("amount", 0) or 0)

    limits: dict[str, float] = local_db.load(SETTINGS_KEY, {}).get("monthly_limits", {})

    results = []
    for cat, spent in spending.items():
        limit = float(limits.get(cat, 0.0))
        pct = (spent / limit) if limit > 0 else 0.0
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
    """Permanently delete a transaction record by its ID. Returns success flag."""
    records = local_db.load(TRANSACTIONS_KEY, [])
    new_records = [r for r in records if r.get("transaction_id") != txn_id]
    if len(new_records) == len(records):
        return False
    local_db.save(TRANSACTIONS_KEY, new_records)
    return True
