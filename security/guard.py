"""
🛡️ الفهد — حارس الأمان
Input validation, sanitization, and access control
"""
import re
import logging
from typing import Optional, Tuple
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# === Regex Patterns ===
SYMBOL_PATTERN = re.compile(r"^[A-Z]{2,10}$")
CALLBACK_PATTERN = re.compile(
    r"^(confirm|cancel|exec|vclose|vreset|plan|survey)_([A-Za-z0-9_]+)$"
)
USDT_ADDRESS_PATTERN = re.compile(r"^(T[1-9A-HJ-NP-Za-km-z]{33})$")  # TRC-20

# === Allowed Exchanges ===
ALLOWED_EXCHANGES = {"okx", "bybit", "bitget", "mexc", "binance"}

# === Blocked Symbols (stablecoins, test tokens) ===
BLOCKED_SYMBOLS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD"}


class Guard:
    """حارس الأمان — يتحقق من جميع المدخلات"""

    @staticmethod
    def validate_symbol(symbol: str) -> Tuple[bool, str]:
        """التحقق من صحة رمز العملة"""
        if not symbol:
            return False, "❌ رمز العملة فارغ"

        sym = symbol.upper().replace("USDT", "").replace("/", "").replace("-", "")

        if sym in BLOCKED_SYMBOLS:
            return False, f"❌ {sym} عملة مستقرة — غير مسموح بالتداول"

        if not SYMBOL_PATTERN.match(sym):
            return False, f"❌ رمز غير صالح: {sym}"

        return True, sym

    @staticmethod
    def validate_amount(amount: str, min_val: Decimal = Decimal("1"), 
                         max_val: Decimal = Decimal("1000000")) -> Tuple[bool, Decimal, str]:
        """التحقق من صحة المبلغ"""
        try:
            val = Decimal(str(amount).replace(",", ""))
        except (InvalidOperation, ValueError):
            return False, Decimal("0"), "❌ المبلغ غير رقمي"

        if val <= 0:
            return False, val, "❌ المبلغ يجب أن يكون أكبر من صفر"

        if val < min_val:
            return False, val, f"❌ الحد الأدنى ${min_val}"

        if val > max_val:
            return False, val, f"❌ الحد الأقصى ${max_val}"

        return True, val, ""

    @staticmethod
    def validate_callback(data: str) -> Tuple[bool, str]:
        """التحقق من صحة callback data"""
        if not data or len(data) > 64:
            return False, "❌ بيانات غير صالحة"

        if not CALLBACK_PATTERN.match(data):
            return False, "❌ نمط callback غير مسموح"

        return True, ""

    @staticmethod
    def validate_exchange(exchange: str) -> Tuple[bool, str]:
        """التحقق من صحة المنصة"""
        ex = exchange.lower().strip()
        if ex not in ALLOWED_EXCHANGES:
            return False, f"❌ المنصة {ex} غير مدعومة"
        return True, ex

    @staticmethod
    def sanitize_text(text: str, max_length: int = 4096) -> str:
        """تطهير النصوص — إزالة الأحرف الخطرة"""
        if not text:
            return ""
        # إزالة الأحكم الخاصة والتعليمات البرمجية
        sanitized = re.sub(r"[<>`\$;|&{}\[\]]", "", text)
        return sanitized[:max_length]

    @staticmethod
    def validate_usdt_address(address: str) -> Tuple[bool, str]:
        """التحقق من عنوان USDT TRC-20"""
        if not address:
            return False, "❌ العنوان فارغ"
        if not USDT_ADDRESS_PATTERN.match(address):
            return False, "❌ عنوان USDT غير صالح (يجب أن يبدأ بـ T وطوله 34 حرف)"
        return True, address

    @staticmethod
    def mask_api_key(key: str) -> str:
        """إخفاء API Key — يُظهر 4 أحرف فقط"""
        if not key or len(key) < 8:
            return "****"
        return f"{key[:2]}****{key[-2:]}"


# Singleton
guard = Guard()
