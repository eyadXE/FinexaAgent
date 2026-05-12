"""tools.py — The 4 agent tools wired to Google Sheets.

Tools use individual typed parameters so the LLM can call them
directly without needing to construct a JSON string wrapper.
"""

from datetime import date
from langchain_core.tools import tool

import sheets
from config import CONFIDENCE_THRESHOLD, BUDGET_ALERT_PCT


# ═══════════════════════════════════════════════════════════════════
# TOOL 1 — log_transaction
# ═══════════════════════════════════════════════════════════════════

@tool
def log_transaction(
    amount: float,
    txn_type: str = "Expense",
    category: str = "General",
    payment_method: str = "Cash",
    description: str = "",
    txn_date: str = "",
    currency: str = "EGP",
    confidence_score: float = 1.0,
    notes: str = "",
) -> str:
    """
    Log a financial transaction to Google Sheets.

    Args:
        amount:           REQUIRED. The transaction amount as a number.
        txn_type:         "Expense", "Income", or "Transfer". Default: "Expense".
        category:         Category such as Rent, Food, Internet, Salary. Default: "General".
        payment_method:   "Cash", "Card", or "Bank Transfer". Default: "Cash".
        description:      Short English summary of the transaction.
        txn_date:         Date as YYYY-MM-DD. Leave empty to use today.
        currency:         "EGP", "USD", or "EUR". Default: "EGP".
        confidence_score: How confident you are in the extraction, 0.0 to 1.0.
        notes:            Any extra context from the user message.

    Use this tool when the user mentions paying, spending, receiving, or transferring money.
    Examples:
      "دفعت 750 جنيه إيجار"       -> amount=750, txn_type=Expense, category=Rent
      "received 5000 salary"       -> amount=5000, txn_type=Income, category=Salary
      "paid 200 by card internet"  -> amount=200, payment_method=Card, category=Internet
    """
    # Validation Rule 1: amount must be positive
    if amount is None or amount <= 0:
        return "Could not find the amount. Please provide a positive number."

    # Validation Rule 2: default date to today
    resolved_date = txn_date.strip() if txn_date else date.today().isoformat()

    # Validation Rule 3: normalise currency
    resolved_currency = (currency or "EGP").upper()

    # Validation Rule 4: confidence check
    if confidence_score < CONFIDENCE_THRESHOLD:
        return (
            f"Not confident enough ({confidence_score:.0%}) about this transaction. "
            "Could you clarify: What was it for and how much?"
        )

    # Validation Rule 5: resolve remaining fields
    resolved_category = (category or "General").strip()
    resolved_type     = (txn_type or "Expense").strip()
    resolved_method   = (payment_method or "Cash").strip()
    resolved_desc     = description or f"{resolved_type} — {resolved_category}"

    # COA lookup
    coa = sheets.lookup_coa(resolved_category, resolved_type)

    # Build the full 14-field record
    fields = {
        "date":             resolved_date,
        "type":             resolved_type,
        "amount":           amount,
        "currency":         resolved_currency,
        "category":         resolved_category,
        "payment_method":   resolved_method,
        "description":      resolved_desc,
        "account_code":     coa["account_code"],
        "account_name":     coa["account_name"],
        "account_type":     coa["account_type"],
        "confidence_score": confidence_score,
        "status":           "Pending",
        "notes":            notes or "",
    }

    # Write to Sheets
    try:
        txn_id = sheets.append_transaction(fields)
    except Exception as e:
        return f"Failed to write to Google Sheets: {e}"

    # Build confirmation message
    reply = (
        f"Recorded\n"
        f"  ID:       {txn_id}\n"
        f"  Amount:   {amount:,.2f} {resolved_currency}\n"
        f"  Type:     {resolved_type}\n"
        f"  Category: {resolved_category}\n"
        f"  Method:   {resolved_method}\n"
        f"  Account:  {coa['account_name']} ({coa['account_code']})\n"
        f"  Date:     {resolved_date}\n"
        f"  Status:   Pending\n"
    )

    # Auto budget check
    alert = _budget_alerts_for(resolved_category)
    if alert:
        reply += "\n" + alert

    return reply


def _budget_alerts_for(category: str) -> str:
    try:
        statuses = sheets.get_budget_status(month=date.today().strftime("%Y-%m"))
        alerts = [
            f"Budget Alert - {s['category']}: "
            f"{s['spent']:,.0f} / {s['limit']:,.0f} EGP ({s['pct']:.0%} used)"
            for s in statuses
            if s["category"] == category and s["over_threshold"] and s["limit"] > 0
        ]
        return "\n".join(alerts)
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════
# TOOL 2 — get_summary
# ═══════════════════════════════════════════════════════════════════

@tool
def get_summary(month: str = "") -> str:
    """
    Return a financial summary: total income, total expenses, net profit,
    cash in, cash out, and net cash position.

    Args:
        month: Optional period in format YYYY-MM (e.g. "2025-01").
               Leave empty for all-time totals.

    Use this when the user asks for totals, profit, overview, or summary.
    Examples:
      "how much did I earn this month?" -> get_summary for current month
      "what is my profit in May?"       -> get_summary(month="2025-05")
    """
    month_param = month.strip() if month else None
    try:
        s = sheets.get_summary(month=month_param)
    except Exception as e:
        return f"Could not fetch summary: {e}"

    period_label = s["period"]
    return (
        f"Financial Summary - {period_label}\n"
        f"  Total Income:   {s['total_income']:,.2f} EGP\n"
        f"  Total Expenses: {s['total_expense']:,.2f} EGP\n"
        f"  Net Profit:     {s['net_profit']:,.2f} EGP\n"
        f"  Cash In:        {s['cash_in']:,.2f} EGP\n"
        f"  Cash Out:       {s['cash_out']:,.2f} EGP\n"
        f"  Net Cash:       {s['net_cash']:,.2f} EGP\n"
    )


# ═══════════════════════════════════════════════════════════════════
# TOOL 3 — query_transactions
# ═══════════════════════════════════════════════════════════════════

@tool
def query_transactions(
    category: str = "",
    txn_type: str = "",
    month: str = "",
    limit: int = 10,
) -> str:
    """
    Search and list past transactions with optional filters.

    Args:
        category: Filter by category name, e.g. "Rent", "Food". Leave empty for all.
        txn_type: Filter by "Expense", "Income", or "Transfer". Leave empty for all.
        month:    Filter by month in YYYY-MM format. Leave empty for all.
        limit:    Maximum rows to return. Default: 10.

    Use this when the user wants to see past transactions.
    Examples:
      "show my rent expenses"      -> query_transactions(category="Rent")
      "show all income this month" -> query_transactions(txn_type="Income", month="2025-05")
      "last 5 transactions"        -> query_transactions(limit=5)
    """
    try:
        records = sheets.get_transactions(
            category=category or None,
            txn_type=txn_type or None,
            month=month or None,
            limit=limit,
        )
    except Exception as e:
        return f"Could not query transactions: {e}"

    if not records:
        parts = []
        if category: parts.append(f"category={category}")
        if txn_type:  parts.append(f"type={txn_type}")
        if month:     parts.append(f"month={month}")
        return "No transactions found" + (f" for {', '.join(parts)}." if parts else ".")

    lines = [f"Transactions ({len(records)} shown)"]
    for r in records:
        lines.append(
            f"  {r.get('date',''):10}  "
            f"{r.get('type',''):8}  "
            f"{float(r.get('amount', 0)):>10,.2f} {r.get('currency','EGP')}  "
            f"{r.get('category',''):15}  "
            f"[{r.get('status','')}]"
        )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# TOOL 4 — check_budget
# ═══════════════════════════════════════════════════════════════════

@tool
def check_budget(month: str = "") -> str:
    """
    Check spending against monthly budget limits for every category.
    Flags any category that has exceeded 80% of its limit.

    Args:
        month: Optional period in YYYY-MM format. Defaults to current month.

    Use this when the user asks about budget, overspending, or limits.
    Examples:
      "check my budget"    -> check_budget
      "am I overspending?" -> check_budget
    """
    month_param = month.strip() or date.today().strftime("%Y-%m")
    try:
        statuses = sheets.get_budget_status(month=month_param)
    except Exception as e:
        return f"Could not check budget: {e}"

    if not statuses:
        return f"No spending data found for {month_param}."

    lines = [f"Budget Status - {month_param}"]
    for s in statuses:
        bar       = _progress_bar(s["pct"])
        icon      = "!" if s["over_threshold"] else "OK"
        limit_str = f"{s['limit']:,.0f}" if s["limit"] > 0 else "no limit"
        lines.append(
            f"  [{icon}] {s['category']:18} "
            f"{s['spent']:>8,.0f} / {limit_str:>8} EGP  "
            f"{bar}  {s['pct']:.0%}"
        )

    alerts = [s for s in statuses if s["over_threshold"]]
    if alerts:
        lines.append(f"\n{len(alerts)} category(ies) above 80% - review your spending!")
    else:
        lines.append("\nAll categories within budget.")

    return "\n".join(lines)


def _progress_bar(pct: float, width: int = 10) -> str:
    filled = min(int(pct * width), width)
    return "[" + "#" * filled + "." * (width - filled) + "]"