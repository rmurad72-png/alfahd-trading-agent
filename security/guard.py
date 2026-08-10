"""
🛡️ حارس الفهد — التحقق من المدخلات
"""

VALID_EXCHANGES = {"okx", "bitget", "binance", "bybit"}


def validate_symbol(symbol: str):
    """التحقق من صحة الرمز"""
    s = symbol.upper().strip()
    if not s:
        return False, "❌ رمز غير صالح"
    if not s.endswith("USDT"):
        s += "USDT"
    return True, s


def validate_exchange(exchange_id: str):
    """التحقق من صحة المنصة"""
    e = exchange_id.lower().strip()
    if e not in VALID_EXCHANGES:
        return False, f"❌ المنصة '{exchange_id}' غير مدعومة. المدعومة: {', '.join(VALID_EXCHANGES)}"
    return True, e


def require_confirmation(action: str, is_demo: bool = True) -> str:
    """طلب تأكيد قبل التنفيذ الحي"""
    mode = "🧪 DEMO" if is_demo else "🔴 LIVE"
    return (
        f"⚠️ *تأكيد العملية* {mode}\n\n"
        f"الإجراء: `{action}`\n\n"
        f"اضغط للتأكيد (غير مفعل حالياً)"
    )
