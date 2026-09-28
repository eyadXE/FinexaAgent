"""seed_demo_data.py — Populate local_db with realistic demo transactions
and budget limits, so /ui and /dashboard have something to show immediately
without requiring the user to send messages first.

Run: python seed_demo_data.py [--reset]
"""

import sys

import local_db
import sheets

DEMO_TRANSACTIONS = [
    # (days_ago, type, amount, category, payment_method, description)
    (89, "Income", 8000, "Salary", "Bank Transfer", "Monthly salary"),
    (85, "Expense", 1500, "Rent", "Bank Transfer", "Office rent"),
    (80, "Expense", 250, "Internet", "Card", "Monthly internet bill"),
    (75, "Expense", 420, "Food", "Cash", "Team lunch"),
    (70, "Expense", 180, "Transportation", "Cash", "Uber rides"),
    (60, "Income", 3000, "Freelance", "Bank Transfer", "Consulting project"),
    (59, "Expense", 1500, "Rent", "Bank Transfer", "Office rent"),
    (55, "Expense", 300, "Marketing", "Card", "Facebook ads"),
    (50, "Expense", 380, "Food", "Cash", "Client dinner"),
    (45, "Expense", 150, "Transportation", "Cash", "Fuel"),
    (30, "Income", 8000, "Salary", "Bank Transfer", "Monthly salary"),
    (29, "Expense", 1500, "Rent", "Bank Transfer", "Office rent"),
    (25, "Expense", 260, "Internet", "Card", "Monthly internet bill"),
    (20, "Expense", 500, "Food", "Cash", "Groceries and supplies"),
    (15, "Expense", 220, "Transportation", "Cash", "Uber rides"),
    (10, "Expense", 600, "Shopping", "Card", "Office supplies run"),
    (5,  "Income", 2500, "Freelance", "Bank Transfer", "Small project"),
    (4,  "Expense", 1500, "Rent", "Bank Transfer", "Office rent"),
    (3,  "Expense", 470, "Food", "Cash", "Client dinner + groceries"),
    (2,  "Expense", 430, "Food", "Card", "Team lunch"),
    (1,  "Expense", 260, "Transportation", "Cash", "Uber + fuel"),
]

BUDGET_LIMITS = {
    "Rent": 2000,
    "Food": 1500,
    "Internet": 300,
    "Transportation": 800,
    "Marketing": 1000,
    "Shopping": 700,
}


def seed(reset: bool = False):
    from datetime import date, timedelta

    if reset:
        local_db.save("transactions", [])
        local_db.save("memory", [])

    existing = local_db.load("transactions", [])
    if existing and not reset:
        print(f"{len(existing)} transactions already exist — skipping seed (use --reset to overwrite).")
        return

    today = date.today()
    for days_ago, txn_type, amount, category, method, desc in DEMO_TRANSACTIONS:
        txn_date = (today - timedelta(days=days_ago)).isoformat()
        coa = sheets.lookup_coa(category, txn_type)
        fields = {
            "date": txn_date,
            "type": txn_type,
            "amount": amount,
            "currency": "EGP",
            "category": category,
            "payment_method": method,
            "description": desc,
            "account_code": coa["account_code"],
            "account_name": coa["account_name"],
            "account_type": coa["account_type"],
            "confidence_score": 1.0,
            "status": "Confirmed",
            "notes": "seed data",
        }
        sheets.append_transaction(fields)

    local_db.save("settings", {"monthly_limits": BUDGET_LIMITS})
    print(f"Seeded {len(DEMO_TRANSACTIONS)} demo transactions and budget limits.")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
