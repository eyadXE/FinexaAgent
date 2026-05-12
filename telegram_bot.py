"""telegram_bot.py — Handles ALL Telegram update types.

Routes:
  text message   → agent directly
  voice message  → Groq Whisper STT → agent
  photo message  → Groq Vision → agent
  callback_query → Confirm / Edit button flow (fully menu-driven)

Edit flow (no typing required for structured fields):
  ✏️ Edit → choose field → choose value (buttons) or type (amount/date/notes)
"""

import re
import httpx
import base64
from typing import Any

import agent as agent_module
import sheets
from config import (
    TELEGRAM_BOT_TOKEN,
    GROQ_API_KEY,
    GROQ_WHISPER_MODEL,
    GROQ_VISION_MODEL,
    LLM_PROVIDER,
)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# In-memory: users waiting to TYPE a value (amount / date / notes / custom category)
# { user_id: {"txn_id": str, "field": str} }
_type_state: dict[str, dict] = {}

# Duplicate detection: {user_id: [(amount_str, category, timestamp)]}
import time as _time
_recent_logs: dict[str, list] = {}


# ═══════════════════════════════════════════════════════════════════
# Telegram API helpers
# ═══════════════════════════════════════════════════════════════════

async def _tg_post(method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{TELEGRAM_API}/{method}", json=payload)
        return r.json()


async def send_text(chat_id, text: str, keyboard=None) -> None:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    await _tg_post("sendMessage", payload)


async def edit_message(chat_id, message_id: int, text: str, keyboard=None) -> None:
    payload = {"chat_id": chat_id, "message_id": message_id,
               "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    await _tg_post("editMessageText", payload)


async def answer_callback(callback_id: str, text: str = "") -> None:
    await _tg_post("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


async def send_typing(chat_id) -> None:
    """Show typing indicator while processing."""
    await _tg_post("sendChatAction", {"chat_id": chat_id, "action": "typing"})


async def _get_file_bytes(file_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        r    = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        path = r.json()["result"]["file_path"]
        dl   = await client.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{path}")
        return dl.content


# ═══════════════════════════════════════════════════════════════════
# Keyboard builders
# ═══════════════════════════════════════════════════════════════════

def _kb_confirm_edit(txn_id: str) -> list:
    """Initial ✅ Confirm / ✏️ Edit / 🗑 Undo keyboard."""
    return [
        [
            {"text": "✅ Confirm",  "callback_data": f"confirm:{txn_id}"},
            {"text": "✏️ Edit",     "callback_data": f"edit:{txn_id}"},
        ],
        [
            {"text": "🗑 Undo Transaction", "callback_data": f"undo:{txn_id}"},
        ],
    ]


def _kb_field_select(txn_id: str) -> list:
    """Choose which field to edit."""
    t = txn_id
    return [
        [{"text": "📁 Category",       "callback_data": f"ef:{t}:category"},
         {"text": "💳 Payment Method", "callback_data": f"ef:{t}:payment_method"}],
        [{"text": "🔄 Type",           "callback_data": f"ef:{t}:type"},
         {"text": "💰 Amount",         "callback_data": f"ef:{t}:amount"}],
        [{"text": "📅 Date",           "callback_data": f"ef:{t}:date"},
         {"text": "📝 Notes",          "callback_data": f"ef:{t}:notes"}],
        [{"text": "❌ Cancel",          "callback_data": f"editcancel:{t}"}],
    ]


def _kb_category(txn_id: str) -> list:
    """Category options — most common Egyptian SMB categories."""
    t = txn_id
    cats = [
        ("🏠 Rent",         "Rent"),
        ("🍕 Food",         "Food"),
        ("🌐 Internet",     "Internet"),
        ("🚗 Transport",    "Transportation"),
        ("💼 Salary",       "Salary"),
        ("⚡ Utilities",    "Utilities"),
        ("📢 Marketing",    "Marketing"),
        ("🖥️ Software",    "Software"),
        ("🏥 Healthcare",   "Healthcare"),
        ("📦 Supplies",     "Office Supplies"),
        ("🔧 Maintenance",  "Maintenance"),
        ("🛒 Shopping",     "Shopping"),
    ]
    rows = []
    for i in range(0, len(cats), 2):
        row = []
        for label, val in cats[i:i+2]:
            row.append({"text": label, "callback_data": f"ev:{t}:category:{val}"})
        rows.append(row)
    rows.append([{"text": "✏️ Type custom category", "callback_data": f"etype:{t}:category"}])
    rows.append([{"text": "⬅️ Back", "callback_data": f"edit:{t}"}])
    return rows


def _kb_payment(txn_id: str) -> list:
    t = txn_id
    return [
        [{"text": "💵 Cash",         "callback_data": f"ev:{t}:payment_method:Cash"},
         {"text": "💳 Card",         "callback_data": f"ev:{t}:payment_method:Card"}],
        [{"text": "🏦 Bank Transfer","callback_data": f"ev:{t}:payment_method:Bank Transfer"}],
        [{"text": "⬅️ Back",          "callback_data": f"edit:{t}"}],
    ]


def _kb_type(txn_id: str) -> list:
    t = txn_id
    return [
        [{"text": "💸 Expense",  "callback_data": f"ev:{t}:type:Expense"},
         {"text": "💰 Income",   "callback_data": f"ev:{t}:type:Income"}],
        [{"text": "🔄 Transfer", "callback_data": f"ev:{t}:type:Transfer"}],
        [{"text": "⬅️ Back",     "callback_data": f"edit:{t}"}],
    ]


# ═══════════════════════════════════════════════════════════════════
# Voice + Photo pre-processing
# ═══════════════════════════════════════════════════════════════════

async def transcribe_voice(file_id: str) -> str:
    audio_bytes = await _get_file_bytes(file_id)
    if LLM_PROVIDER != "groq" or not GROQ_API_KEY:
        return "[Voice transcription requires GROQ_API_KEY and LLM_PROVIDER=groq]"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": ("voice.ogg", audio_bytes, "audio/ogg")},
            data={"model": GROQ_WHISPER_MODEL, "language": "ar", "response_format": "text"},
        )
    return r.text.strip() if r.status_code == 200 else f"[Whisper error: {r.text}]"


async def analyze_photo(file_id: str) -> str:
    image_bytes = await _get_file_bytes(file_id)
    img_b64     = base64.b64encode(image_bytes).decode("utf-8")
    if LLM_PROVIDER != "groq" or not GROQ_API_KEY:
        return "[Photo analysis requires GROQ_API_KEY and LLM_PROVIDER=groq]"
    prompt = (
        "Analyze this receipt or invoice. Describe the transaction in one sentence: "
        "'paid [amount] [currency] for [item] at [vendor] by [payment method]'. "
        "If no transaction found, say: 'no transaction found in image'. "
        "Reply with ONLY the sentence."
    )
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_VISION_MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt},
                ]}],
                "max_tokens": 256, "temperature": 0.1,
            },
        )
    return r.json()["choices"][0]["message"]["content"].strip() if r.status_code == 200 else f"[Vision error: {r.text}]"


# ═══════════════════════════════════════════════════════════════════
# Reply helper
# ═══════════════════════════════════════════════════════════════════

def _extract_txn_id(reply: str) -> str | None:
    m = re.search(r"TXN-[\w-]+", reply)
    return m.group() if m else None


async def _send_reply(chat_id, reply: str) -> None:
    txn_id = _extract_txn_id(reply)
    await send_text(chat_id, reply, keyboard=_kb_confirm_edit(txn_id) if txn_id else None)


# ═══════════════════════════════════════════════════════════════════
# Main dispatcher
# ═══════════════════════════════════════════════════════════════════

async def handle_update(update: dict[str, Any]) -> None:
    if "callback_query" in update:
        await _handle_callback(update["callback_query"])
        return

    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    user_id = str(message["from"]["id"])

    # User is typing a custom value (amount / date / notes / custom category)
    if user_id in _type_state:
        await _handle_typed_value(chat_id, user_id, message.get("text", ""))
        return

    if "text" in message:
        text = message["text"].strip()
        await send_typing(chat_id)

        # ── Built-in commands ──────────────────────────────────────
        if text in ("/start", "/help"):
            await send_text(chat_id,
                "👋 Welcome to <b>Finexa</b> — AI Finance Recorder!\n\n"
                "Just send a transaction in Arabic or English:\n"
                "• <code>دفعت 750 جنيه إيجار بالكارت</code>\n"
                "• <code>paid 200 EGP for internet by card</code>\n"
                "• <code>received 5000 EGP salary</code>\n\n"
                "📷 Send a receipt photo or 🎙 voice note\n\n"
                "<b>Commands:</b>\n"
                "/report — this month summary\n"
                "/history — last 10 transactions\n"
                "/budget — budget status\n"
                "/help — show this message"
            )
            return

        if text == "/report":
            await send_typing(chat_id)
            reply = agent_module.chat("show me this month financial summary")
            await send_text(chat_id, reply)
            return

        if text == "/history":
            await send_typing(chat_id)
            reply = agent_module.chat("show last 10 transactions")
            await send_text(chat_id, reply)
            return

        if text == "/budget":
            await send_typing(chat_id)
            reply = agent_module.chat("check my budget status this month")
            await send_text(chat_id, reply)
            return

        # ── Duplicate detection ────────────────────────────────────
        reply = agent_module.chat(text)
        if reply.startswith("Recorded") and "TXN-" in reply:
            txn_id = _extract_txn_id(reply)
            import re as _re
            amt_m = _re.search(r"Amount:\s+([\d,.]+)", reply)
            cat_m = _re.search(r"Category:\s+(\S+)", reply)
            if amt_m and cat_m:
                key   = f"{amt_m.group(1)}|{cat_m.group(1)}"
                now   = _time.time()
                recnt = _recent_logs.setdefault(user_id, [])
                dupes = [e for e in recnt if e[0] == key and now - e[1] < 60]
                _recent_logs[user_id] = [e for e in recnt if now - e[1] < 120]
                _recent_logs[user_id].append((key, now))
                if dupes:
                    await send_text(chat_id,
                        f"⚠️ <b>Possible duplicate!</b>\n"
                        f"A similar transaction was just logged 1 minute ago.\n\n"
                        + reply,
                        keyboard=[
                            [{"text": "✅ Confirm (keep both)", "callback_data": f"confirm:{txn_id}"},
                             {"text": "🗑 Cancel this one",    "callback_data": f"deldup:{txn_id}"}]
                        ]
                    )
                    return

        await _send_reply(chat_id, reply)
        return

    if "voice" in message:
        await send_typing(chat_id)
        await send_text(chat_id, "🎙 Transcribing your voice note...")
        transcript = await transcribe_voice(message["voice"]["file_id"])
        if transcript.startswith("["):
            await send_text(chat_id, f"❌ {transcript}")
            return
        await send_text(chat_id, f"📝 Understood: <i>{transcript}</i>")
        await _send_reply(chat_id, agent_module.chat(transcript))
        return

    if "photo" in message:
        await send_typing(chat_id)
        await send_text(chat_id, "📷 Analyzing your photo...")
        description = await analyze_photo(message["photo"][-1]["file_id"])
        if "no transaction" in description.lower() or description.startswith("["):
            await send_text(chat_id, "❓ No transaction found in this image. Please type the details.")
            return
        await send_text(chat_id, f"📝 Extracted: <i>{description}</i>")
        await _send_reply(chat_id, agent_module.chat(description))
        return

    await send_text(chat_id,
        "I support text, voice notes, and receipt photos.\n"
        "Try: <code>دفعت 500 جنيه إيجار</code>"
    )


# ═══════════════════════════════════════════════════════════════════
# Callback handler — all button taps
# ═══════════════════════════════════════════════════════════════════

async def _handle_callback(callback: dict) -> None:
    cb_id      = callback["id"]
    chat_id    = callback["message"]["chat"]["id"]
    msg_id     = callback["message"]["message_id"]
    user_id    = str(callback["from"]["id"])
    data       = callback.get("data", "")
    orig_text  = callback["message"].get("text", "")

    # ── ✅ Confirm ──────────────────────────────────────────────────
    if data.startswith("confirm:"):
        txn_id = data.split(":", 1)[1]
        ok     = sheets.update_transaction_field(txn_id, "status", "Confirmed")
        await answer_callback(cb_id, "✅ Confirmed!")
        if ok:
            new_text = orig_text.replace("Pending", "✅ Confirmed")
            await edit_message(chat_id, msg_id, new_text)
            # Save to memory
            try:
                import memory as mem, re as _re
                cat_m    = _re.search(r"Category:\s*([^\n]+)", orig_text)
                method_m = _re.search(r"Method:\s*([^\n]+)", orig_text)
                code_m   = _re.search(r"\((\d{4})\)", orig_text)
                name_m   = _re.search(r"Account:\s*([^(]+)\(", orig_text)
                if cat_m:
                    mem.save(
                        description    = cat_m.group(1).strip(),
                        category       = cat_m.group(1).strip(),
                        payment_method = method_m.group(1).strip() if method_m else "Cash",
                        account_code   = code_m.group(1) if code_m else "5000",
                        account_name   = name_m.group(1).strip() if name_m else "",
                        source         = "user_confirmed",
                    )
            except Exception:
                pass
        else:
            await send_text(chat_id, f"❌ Transaction {txn_id} not found.")

    # ── ✏️ Edit — show field selection menu ────────────────────────
    elif data.startswith("edit:"):
        txn_id = data.split(":", 1)[1]
        await answer_callback(cb_id, "Select what to edit")
        await send_text(chat_id,
            f"✏️ <b>Editing {txn_id}</b>\nWhat would you like to correct?",
            keyboard=_kb_field_select(txn_id),
        )

    # ── ef: — field chosen, show value options ─────────────────────
    elif data.startswith("ef:"):
        _, txn_id, field = data.split(":", 2)
        await answer_callback(cb_id)

        if field == "category":
            await edit_message(chat_id, msg_id,
                f"📁 <b>Choose category</b> for {txn_id}:",
                keyboard=_kb_category(txn_id),
            )
        elif field == "payment_method":
            await edit_message(chat_id, msg_id,
                f"💳 <b>Choose payment method</b> for {txn_id}:",
                keyboard=_kb_payment(txn_id),
            )
        elif field == "type":
            await edit_message(chat_id, msg_id,
                f"🔄 <b>Choose transaction type</b> for {txn_id}:",
                keyboard=_kb_type(txn_id),
            )
        elif field in ("amount", "date", "notes"):
            # These need typed input
            _type_state[user_id] = {"txn_id": txn_id, "field": field}
            hints = {
                "amount": "Enter the correct amount (numbers only):\ne.g. <code>850</code>",
                "date":   "Enter the correct date:\ne.g. <code>2026-05-10</code>",
                "notes":  "Enter any notes or extra details:",
            }
            await send_text(chat_id,
                f"✏️ {hints[field]}\n\nType <code>cancel</code> to abort.",
            )

    # ── ev: — value chosen, apply the edit ────────────────────────
    elif data.startswith("ev:"):
        parts  = data.split(":", 3)   # ev : txn_id : field : value
        txn_id = parts[1]
        field  = parts[2]
        value  = parts[3]
        ok     = sheets.update_transaction_field(txn_id, field, value)
        await answer_callback(cb_id, "✅ Updated!")
        if ok:
            await edit_message(chat_id, msg_id,
                f"✅ <b>{field.replace('_',' ').title()}</b> updated to <b>{value}</b>\n"
                f"Transaction: {txn_id}",
            )
        else:
            await send_text(chat_id, f"❌ Could not update {txn_id}.")

    # ── etype: — custom typed category ────────────────────────────
    elif data.startswith("etype:"):
        _, txn_id, field = data.split(":", 2)
        _type_state[user_id] = {"txn_id": txn_id, "field": field}
        await answer_callback(cb_id)
        await send_text(chat_id,
            "✏️ Type the custom category name:\ne.g. <code>Photography</code> or <code>Consulting</code>\n\n"
            "Type <code>cancel</code> to abort."
        )

    # ── Delete duplicate ─────────────────────────────────────────
    elif data.startswith("deldup:"):
        txn_id = data.split(":", 1)[1]
        # Mark as cancelled by deleting the row or setting status to Cancelled
        sheets.update_transaction_field(txn_id, "status", "Cancelled")
        await answer_callback(cb_id, "🗑 Removed")
        await edit_message(chat_id, msg_id, f"🗑 Duplicate transaction {txn_id} removed.")

    # ── Undo / delete transaction ─────────────────────────────────
    elif data.startswith("undo:"):
        txn_id = data.split(":", 1)[1]
        await answer_callback(cb_id, "Are you sure?")
        await send_text(chat_id,
            f"⚠️ <b>Undo transaction {txn_id}?</b>\n"
            "This will permanently delete it from Google Sheets.",
            keyboard=[[
                {"text": "✅ Yes, delete it", "callback_data": f"undoconfirm:{txn_id}"},
                {"text": "❌ No, keep it",    "callback_data": f"undocancel:{txn_id}"},
            ]],
        )

    elif data.startswith("undoconfirm:"):
        txn_id = data.split(":", 1)[1]
        ok     = sheets.delete_transaction(txn_id)
        await answer_callback(cb_id, "🗑 Deleted")
        if ok:
            await edit_message(chat_id, msg_id,
                f"🗑 <b>Transaction {txn_id} deleted.</b>\n"
                "It has been permanently removed from Google Sheets."
            )
        else:
            await send_text(chat_id, f"❌ Could not find transaction {txn_id} — it may already be deleted.")

    elif data.startswith("undocancel:"):
        txn_id = data.split(":", 1)[1]
        await answer_callback(cb_id, "Kept ✅")
        await edit_message(chat_id, msg_id,
            f"✅ Transaction {txn_id} kept.\nTap Confirm when you're ready."
        )

    # ── Cancel ────────────────────────────────────────────────────
    elif data.startswith("editcancel:"):
        await answer_callback(cb_id, "Cancelled")
        await edit_message(chat_id, msg_id, "❌ Edit cancelled.")


# ═══════════════════════════════════════════════════════════════════
# Typed value handler (amount / date / notes / custom category)
# ═══════════════════════════════════════════════════════════════════

async def _handle_typed_value(chat_id, user_id: str, text: str) -> None:
    state  = _type_state.pop(user_id)
    txn_id = state["txn_id"]
    field  = state["field"]

    if text.strip().lower() == "cancel":
        await send_text(chat_id, "Edit cancelled.")
        return

    value = text.strip()

    # Validate amount is a number
    if field == "amount":
        try:
            float(value.replace(",", ""))
        except ValueError:
            await send_text(chat_id,
                "❌ That doesn't look like a number. Please enter digits only, e.g. <code>750</code>"
            )
            # Re-enter state so they can try again
            _type_state[user_id] = state
            return

    ok = sheets.update_transaction_field(txn_id, field, value)
    if ok:
        await send_text(chat_id,
            f"✅ <b>{field.replace('_',' ').title()}</b> updated to <b>{value}</b>\n"
            f"Transaction: {txn_id}"
        )
    else:
        await send_text(chat_id, f"❌ Could not find transaction {txn_id}.")


# ═══════════════════════════════════════════════════════════════════
# Webhook registration
# ═══════════════════════════════════════════════════════════════════

async def set_webhook(webhook_url: str) -> bool:
    r = await _tg_post("setWebhook", {
        "url":                  f"{webhook_url}/webhook",
        "allowed_updates":      ["message", "callback_query"],
        "drop_pending_updates": True,
    })
    return r.get("ok", False)


async def delete_webhook() -> None:
    await _tg_post("deleteWebhook", {"drop_pending_updates": True})