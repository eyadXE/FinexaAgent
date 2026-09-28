"""memory.py — Adaptive memory system, now backed by a local JSON file
(local_db.py) instead of a live Google Sheets "Memory" tab.

How it works:
  1. Every confirmed transaction → extract keywords → save to local memory store
  2. Every new message → check memory first → if match found, pass as hint to LLM
  3. The more a vendor/category is confirmed, the higher the confidence

Same public function names/signatures as the original Sheets-backed
version, so agent.py / telegram_bot.py need no changes.

Record shape:
  {keyword, category, payment_method, account_code, account_name,
   times_used, last_used, source}
"""

import re
from datetime import date

import local_db

MEMORY_KEY = "memory"

# Stop words to skip when extracting keywords
_STOP = {
    "دفعت","اشتريت","صرفت","استلمت","حصلت","paid","received","bought",
    "من","في","على","the","for","and","كارت","cash","card","جنيه",
    "egp","usd","eur","a","an","to","of","by","with","via",
}


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a user message."""
    text = text.lower().strip()
    words = re.findall(r"[\w؀-ۿ]+", text)
    return [w for w in words if w not in _STOP and len(w) > 2]


def lookup(user_message: str) -> dict | None:
    """
    Check memory for known patterns in the user message.
    Returns {category, payment_method, account_code, account_name, confidence}
    or None if no match.
    """
    records = local_db.load(MEMORY_KEY, [])
    if not records:
        return None

    keywords = _extract_keywords(user_message)
    best = None
    best_uses = 0

    for r in records:
        kw = str(r.get("keyword", "")).lower()
        if not kw:
            continue
        if kw in keywords or kw in user_message.lower():
            uses = int(r.get("times_used", 0))
            if uses > best_uses:
                best_uses = uses
                best = r

    if best and best_uses >= 1:
        confidence = min(0.95, 0.75 + (best_uses * 0.04))
        return {
            "category":       best.get("category", ""),
            "payment_method": best.get("payment_method", "Cash"),
            "account_code":   str(best.get("account_code", "")),
            "account_name":   best.get("account_name", ""),
            "confidence":     round(confidence, 2),
            "times_used":     best_uses,
            "keyword":        best.get("keyword", ""),
        }
    return None


def save(description: str, category: str, payment_method: str,
         account_code: str, account_name: str, source: str = "confirmed") -> None:
    """
    Save a confirmed transaction to memory.
    If a keyword already exists, increment times_used.
    Called after user taps Confirm.
    """
    try:
        records = local_db.load(MEMORY_KEY, [])
        keywords = _extract_keywords(description)

        by_keyword = {str(r.get("keyword", "")).lower(): r for r in records}

        for kw in keywords:
            if kw in by_keyword:
                r = by_keyword[kw]
                r["times_used"] = int(r.get("times_used", 0)) + 1
                r["last_used"] = date.today().isoformat()
            else:
                new_r = {
                    "keyword": kw,
                    "category": category,
                    "payment_method": payment_method,
                    "account_code": account_code,
                    "account_name": account_name,
                    "times_used": 1,
                    "last_used": date.today().isoformat(),
                    "source": source,
                }
                records.append(new_r)
                by_keyword[kw] = new_r

        local_db.save(MEMORY_KEY, records)
    except Exception:
        pass   # Memory is best-effort — never crash the main flow


def forget(keyword: str) -> bool:
    """Remove a keyword from memory (in case of wrong learning)."""
    records = local_db.load(MEMORY_KEY, [])
    new_records = [r for r in records if str(r.get("keyword", "")).lower() != keyword.lower()]
    if len(new_records) == len(records):
        return False
    local_db.save(MEMORY_KEY, new_records)
    return True


def get_all() -> list[dict]:
    """Return all memory records for display."""
    return local_db.load(MEMORY_KEY, [])
