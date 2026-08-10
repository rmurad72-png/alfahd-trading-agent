"""
🛡️ حارس الفهد — التحقق من المدخلات
"""

VALID_EXCHANGES = {"okx", "bitget", "binance", "bybit"}


class Guard:
    def validate_symbol(self, symbol: str):
        s = symbol.upper().strip()
        if not s:
            return False, "❌ رمز غير صالح"
        if not s.endswith("USDT"):
            s += "USDT"
        return True, s

    def validate_exchange(self, exchange_id: str):
        e = exchange_id.lower().strip()
        if e not in VALID_EXCHANGES:
            return False, f"❌ المنصة '{exchange_id}' غير مدعومة. المدعومة: {', '.join(VALID_EXCHANGES)}"
        return True, e

    def require_confirmation(self, action: str, is_demo: bool = True) -> str:
        mode = "🧪 DEMO" if is_demo else "🔴 LIVE"
        return (
            f"⚠️ *تأكيد العملية* {mode}\n\n"
            f"الإجراء: `{action}`\n\n"
            f"اضغط للتأكيد (غير مفعل حالياً)"
        )


guard = Guard()
