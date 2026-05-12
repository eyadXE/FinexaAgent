"""memory.py — Adaptive memory system stored in Google Sheets.

How it works:
  1. Every confirmed transaction → extract keywords → save to Memory sheet
  2. Every new message → check memory first → if match found, pass as hint to LLM
  3. The more a vendor/category is confirmed, the higher the confidence

Memory sheet columns:
  keyword | category | payment_method | account_code | account_name | times_used | last_used
"""

import re
from datetime import date
from typing import Any

SHEET_MEMORY = "Memory"

# Stop words to skip when extracting keywords
_STOP = {
    "دفعت","اشتريت","صرفت","استلمت","حصلت","paid","received","bought",
    "من","في","على","the","for","and","من","كارت","cash","card","جنيه",
    "egp","usd","eur","a","an","to","of","by","with","via",
}


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a user message."""
    text  = text.lower().strip()
    words = re.findall(r"[\w\u0600-\u06FF]+", text)
    return [w for w in words if w not in _STOP and len(w) > 2]


def _get_sheet():
    """Get or create the Memory worksheet."""
    import gspread
    from google.oauth2.service_account import Credentials
    from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    ss     = client.open_by_key(GOOGLE_SHEET_ID)

    # Create Memory tab if it doesn't exist
    try:
        ws = ss.worksheet(SHEET_MEMORY)
    except Exception:
        ws = ss.add_worksheet(title=SHEET_MEMORY, rows=500, cols=8)
        ws.append_row(["keyword","category","payment_method",
                        "account_code","account_name","times_used","last_used","source"])
    return ws


def lookup(user_message: str) -> dict | None:
    """
    Check memory for known patterns in the user message.
    Returns {category, payment_method, account_code, account_name, confidence}
    or None if no match.
    """
    try:
        ws      = _get_sheet()
        records = ws.get_all_records()
        if not records:
            return None

        keywords = _extract_keywords(user_message)
        best     = None
        best_uses = 0

        for r in records:
            kw = str(r.get("keyword","")).lower()
            if not kw:
                continue
            # Check if this keyword appears in the message
            if kw in keywords or kw in user_message.lower():
                uses = int(r.get("times_used", 0))
                if uses > best_uses:
                    best_uses = uses
                    best = r

        if best and best_uses >= 1:
            # Confidence scales: 1 use → 0.80, 3 uses → 0.90, 5+ uses → 0.95
            confidence = min(0.95, 0.75 + (best_uses * 0.04))
            return {
                "category":       best.get("category",""),
                "payment_method": best.get("payment_method","Cash"),
                "account_code":   str(best.get("account_code","")),
                "account_name":   best.get("account_name",""),
                "confidence":     round(confidence, 2),
                "times_used":     best_uses,
                "keyword":        best.get("keyword",""),
            }
    except Exception:
        pass
    return None


def save(description: str, category: str, payment_method: str,
         account_code: str, account_name: str, source: str = "confirmed") -> None:
    """
    Save a confirmed transaction to memory.
    If keyword already exists, increment times_used.
    Called after user taps ✅ Confirm.
    """
    try:
        ws      = _get_sheet()
        records = ws.get_all_records()
        keywords = _extract_keywords(description)

        for kw in keywords:
            # Check if keyword already exists
            row_idx = None
            for i, r in enumerate(records, start=2):
                if str(r.get("keyword","")).lower() == kw:
                    row_idx = i
                    break

            if row_idx:
                # Update existing: increment times_used, update last_used
                times = int(records[row_idx-2].get("times_used",0)) + 1
                ws.update_cell(row_idx, 6, times)
                ws.update_cell(row_idx, 7, date.today().isoformat())
            else:
                # New keyword
                ws.append_row([
                    kw, category, payment_method,
                    account_code, account_name,
                    1, date.today().isoformat(), source,
                ])
    except Exception:
        pass   # Memory is best-effort — never crash the main flow


def forget(keyword: str) -> bool:
    """Remove a keyword from memory (in case of wrong learning)."""
    try:
        ws   = _get_sheet()
        cell = ws.find(keyword.lower())
        if cell:
            ws.delete_rows(cell.row)
            return True
    except Exception:
        pass
    return False


def get_all() -> list[dict]:
    """Return all memory records for display."""
    try:
        return _get_sheet().get_all_records()
    except Exception:
        return []
