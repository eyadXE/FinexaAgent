"""agent.py — Classify-then-dispatch agent (Groq + Ollama switchable).

One LLM call classifies intent and extracts parameters as JSON.
We call the matching tool directly — no loop, no hang, works on any model.
"""

import json, re
from langchain_core.messages import HumanMessage, SystemMessage
from config import LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL, OLLAMA_BASE_URL, OLLAMA_MODEL, MAX_TOKENS
from tools import log_transaction, get_summary, query_transactions, check_budget

EXTRACT_PROMPT = """You are a finance assistant for Egyptian small businesses.
Read the user message and return ONLY a valid JSON object — no markdown, no explanation.

Schema:
{
  "intent": "log" | "summary" | "query" | "budget" | "unknown",
  "params": { ... }
}

Intent rules:
- "log"     → user mentions paying, spending, receiving, or transferring money
- "summary" → user asks for totals, profit, overview, how much earned/spent
- "query"   → user wants to see a list of past transactions
- "budget"  → user asks about budget, limits, overspending
- "unknown" → greetings, unclear, off-topic

Params for "log":
{
  "amount": <number REQUIRED>,
  "txn_type": "Expense"|"Income"|"Transfer",
  "category": <infer from context>,
  "payment_method": "Cash"|"Card"|"Bank Transfer",
  "description": <short english summary>,
  "txn_date": "YYYY-MM-DD or empty",
  "currency": "EGP"|"USD"|"EUR",
  "confidence_score": <0.0–1.0>,
  "notes": ""
}
Params for "summary": { "month": "YYYY-MM or empty" }
Params for "query":   { "category": "", "txn_type": "", "month": "", "limit": 10 }
Params for "budget":  { "month": "" }
Params for "unknown": { "reply": "<friendly reply in user's language>" }

Arabic hints:
دفعت/اشتريت/صرفت=Expense  استلمت/حصلت=Income
إيجار=Rent  أكل/طعام=Food  نت/إنترنت=Internet  راتب/مرتب=Salary
كاش/نقدي=Cash  كارت/فيزا=Card  تحويل=Bank Transfer
الشهر ده=current month

Return ONLY JSON. Nothing else."""


def _build_llm():
    if LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=GROQ_API_KEY, model=GROQ_MODEL,
            max_tokens=MAX_TOKENS, temperature=0.1,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL,
            num_predict=MAX_TOKENS, temperature=0.1, format="json",
        )


_llm = None

def _get_llm():
    global _llm
    if _llm is None:
        _llm = _build_llm()
    return _llm


def _parse_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group() if m else text)


def chat(user_message: str, history=None) -> str:
    """Classify the message, call the right tool, return plain-text reply."""

    # ── Step 0: check memory for known patterns ────────────────────
    memory_hint = ""
    try:
        import memory as mem
        match = mem.lookup(user_message)
        if match:
            memory_hint = (
                f"\n\nMEMORY HINT (from {match['times_used']} past transactions): "
                f"keyword '{match['keyword']}' → category={match['category']}, "
                f"payment_method={match['payment_method']}, "
                f"account_code={match['account_code']}. "
                f"Use confidence_score={match['confidence']} if this matches."
            )
    except Exception:
        pass

    # ── Step 1: classify + extract ─────────────────────────────────
    try:
        prompt = EXTRACT_PROMPT + memory_hint
        resp   = _get_llm().invoke([SystemMessage(content=prompt),
                                     HumanMessage(content=user_message)])
        parsed = _parse_json(resp.content)
    except Exception as e:
        return f"Sorry, I couldn't understand that. ({e})"

    intent = parsed.get("intent", "unknown")
    params = parsed.get("params", {})

    try:
        if intent == "log":
            return log_transaction.invoke(params)
        elif intent == "summary":
            return get_summary.invoke({"month": params.get("month", "")})
        elif intent == "query":
            return query_transactions.invoke({
                "category": params.get("category", ""),
                "txn_type": params.get("txn_type", ""),
                "month":    params.get("month", ""),
                "limit":    int(params.get("limit", 10)),
            })
        elif intent == "budget":
            return check_budget.invoke({"month": params.get("month", "")})
        else:
            arabic_chars = len([c for c in user_message if "\u0600" <= c <= "\u06FF"])
            is_arabic    = arabic_chars > len(user_message) * 0.2
            llm_reply = params.get("reply", "").strip()
            if llm_reply:
                return llm_reply
            if is_arabic:
                return (
                    "أنا Finexa — مساعدك المالي الذكي 🤖\n\n"
                    "مش فاهم الرسالة دي. أنا بشتغل في:\n\n"
                    "💸 تسجيل معاملة: 'دفعت 750 جنيه إيجار'\n"
                    "📊 ملخص مالي: 'عايز ملخص الشهر ده'\n"
                    "📋 سجل: 'وريني آخر 10 مصاريف'\n"
                    "🎯 ميزانية: 'هل تجاوزت الميزانية؟'\n\n"
                    "أو ابعت صورة فاتورة 📷 أو رسالة صوتية 🎙"
                )
            else:
                return (
                    "I am Finexa — your AI finance assistant 🤖\n\n"
                    "I did not understand that. Here is what I can do:\n\n"
                    "💸 Log a transaction: 'paid 750 EGP for rent'\n"
                    "📊 Financial summary: 'show me this month summary'\n"
                    "📋 History: 'show last 10 expenses'\n"
                    "🎯 Budget: 'am I overspending?'\n\n"
                    "Or send a receipt photo 📷 or voice note 🎙"
                )
    except Exception as e:
        return f"Tool error: {e}"


def warmup():
    _get_llm()
    print(f"✅ Agent ready — {LLM_PROVIDER.upper()} / {MODEL_NAME if LLM_PROVIDER == 'ollama' else GROQ_MODEL}")


from config import MODEL_NAME, GROQ_MODEL