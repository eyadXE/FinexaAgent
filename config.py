"""config.py — Central configuration loaded from .env"""

import os
from dotenv import load_dotenv
load_dotenv()

# ── Telegram ───────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN:   str = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Public HTTPS URL where Telegram will POST updates (your Railway/VPS URL)
# For local testing keep empty — bot will use polling instead
TELEGRAM_WEBHOOK_URL: str = os.getenv("TELEGRAM_WEBHOOK_URL", "")

# ── LLM provider switch ────────────────────────────────────────────────────────
# "groq"   → uses Groq cloud (recommended for production)
# "ollama" → uses local Ollama (for development / offline)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")

# ── Groq ───────────────────────────────────────────────────────────────────────
GROQ_API_KEY:    str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL:      str = os.getenv("GROQ_MODEL",   "llama-3.3-70b-versatile")
GROQ_VISION_MODEL: str = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_WHISPER_MODEL: str = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")

# ── Ollama ─────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL:    str = os.getenv("OLLAMA_MODEL",    "qwen2.5:7b-instruct")

# ── Convenience: active model name (used in logs) ─────────────────────────────
MODEL_NAME = GROQ_MODEL if LLM_PROVIDER == "groq" else OLLAMA_MODEL
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))

# ── Google Sheets ──────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_SHEET_ID:         str = os.getenv("GOOGLE_SHEET_ID", "")

# ── Sheet tab names ────────────────────────────────────────────────────────────
SHEET_TRANSACTIONS = "Transactions"
SHEET_COA          = "Chart of Accounts"
SHEET_CATEGORIES   = "Categories"
SHEET_SETTINGS     = "Settings"

# ── Transaction field order (must match Sheets column order exactly) ───────────
TRANSACTION_FIELDS = [
    "transaction_id", "date", "type", "amount", "currency",
    "category", "payment_method", "description",
    "account_code", "account_name", "account_type",
    "confidence_score", "status", "notes",
]

# ── Business rules ─────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.6
BUDGET_ALERT_PCT     = 0.80