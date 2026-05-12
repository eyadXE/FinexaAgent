"""dashboard.py — Data aggregation for all dashboard charts."""

from datetime import date, datetime
from collections import defaultdict
import sheets

def get_dashboard_data() -> dict:
    """Single function that returns everything the dashboard needs."""
    records = sheets.get_transactions(limit=1000)
    today   = date.today()

    # ── KPIs ──────────────────────────────────────────────────────
    this_month = today.strftime("%Y-%m")
    month_recs = [r for r in records if str(r.get("date","")).startswith(this_month)]

    total_income   = sum(float(r.get("amount",0)) for r in records if r.get("type")=="Income")
    total_expense  = sum(float(r.get("amount",0)) for r in records if r.get("type")=="Expense")
    month_income   = sum(float(r.get("amount",0)) for r in month_recs if r.get("type")=="Income")
    month_expense  = sum(float(r.get("amount",0)) for r in month_recs if r.get("type")=="Expense")
    pending_count  = sum(1 for r in records if r.get("status")=="Pending")

    # ── Monthly bar chart (last 6 months) ─────────────────────────
    monthly: dict = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for r in records:
        m = str(r.get("date",""))[:7]
        if not m: continue
        if r.get("type") == "Income":
            monthly[m]["income"] += float(r.get("amount", 0))
        elif r.get("type") == "Expense":
            monthly[m]["expense"] += float(r.get("amount", 0))
    sorted_months = sorted(monthly.keys())[-6:]
    monthly_chart = [
        {"month": m, "income": round(monthly[m]["income"],2),
         "expense": round(monthly[m]["expense"],2),
         "profit": round(monthly[m]["income"] - monthly[m]["expense"],2)}
        for m in sorted_months
    ]

    # ── Category pie chart (expenses only) ────────────────────────
    cat_totals: dict = defaultdict(float)
    for r in records:
        if r.get("type") == "Expense":
            cat_totals[r.get("category","Other")] += float(r.get("amount",0))
    categories = [{"name": k, "value": round(v,2)}
                  for k, v in sorted(cat_totals.items(), key=lambda x: -x[1])][:8]

    # ── Cash trend (last 30 days) ──────────────────────────────────
    daily: dict = defaultdict(float)
    for r in records:
        d = str(r.get("date",""))[:10]
        if not d: continue
        amt = float(r.get("amount",0))
        daily[d] += amt if r.get("type")=="Income" else -amt
    sorted_days = sorted(daily.keys())[-30:]
    running = 0.0
    trend = []
    for d in sorted_days:
        running += daily[d]
        trend.append({"date": d, "cash": round(running,2)})

    # ── Budget usage ───────────────────────────────────────────────
    try:
        budget = sheets.get_budget_status(month=this_month)
    except Exception:
        budget = []

    # ── Recent transactions ────────────────────────────────────────
    recent = []
    for r in list(reversed(records))[:8]:
        recent.append({
            "id":       r.get("transaction_id",""),
            "date":     r.get("date",""),
            "type":     r.get("type",""),
            "amount":   float(r.get("amount",0)),
            "currency": r.get("currency","EGP"),
            "category": r.get("category",""),
            "method":   r.get("payment_method",""),
            "status":   r.get("status",""),
        })

    return {
        "kpis": {
            "total_income":   round(total_income,2),
            "total_expense":  round(total_expense,2),
            "net_profit":     round(total_income - total_expense,2),
            "month_income":   round(month_income,2),
            "month_expense":  round(month_expense,2),
            "month_profit":   round(month_income - month_expense,2),
            "pending_count":  pending_count,
            "total_txns":     len(records),
        },
        "monthly_chart": monthly_chart,
        "categories":    categories,
        "cash_trend":    trend,
        "budget":        budget,
        "recent":        recent,
        "generated_at":  datetime.utcnow().isoformat(),
    }
