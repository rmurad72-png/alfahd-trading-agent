"""
🧪 الفهد — اختبارات الوحدة
"""
import pytest
import asyncio
from decimal import Decimal

from ai.predictor import ai_predictor
from strategies.dca import get_okb_strategy, get_arb_strategy, get_sui_strategy, DCAConfig
from security.guard import guard
from security.vault import Vault


class TestAIPredictor:
    """اختبارات محلل الذكاء الاصطناعي"""

    def test_analyze_insufficient_data(self):
        result = ai_predictor.analyze([])
        assert result["signal"] == "neutral"
        assert result["confidence"] == 0.0

    def test_analyze_with_data(self):
        candles = []
        base = 50000
        for i in range(60):
            candles.append({
                "timestamp": i * 86400000,
                "open": base + i * 100,
                "high": base + i * 100 + 200,
                "low": base + i * 100 - 100,
                "close": base + i * 100 + 50,
                "volume": 1000 + i * 10
            })
        result = ai_predictor.analyze(candles)
        assert "signal" in result
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0


class TestDCAStrategy:
    """اختبارات استراتيجية DCA"""

    def test_okb_strategy_config(self):
        s = get_okb_strategy()
        assert s.config.symbol == "OKB/USDT"
        assert s.config.price_step_pct == 2.0
        assert s.config.take_profit_pct == 3.0
        assert s.config.initial_order_usd == 4.0
        assert s.config.safety_order_usd == 5.0
        assert s.config.max_safety_orders == 4
        assert s.config.safety_multiplier == 1.30
        assert s.config.stop_loss_pct == 9.0
        assert s.config.rsi_entry_threshold == 25.0

    def test_arb_strategy_config(self):
        s = get_arb_strategy()
        assert s.config.symbol == "ARB/USDT"
        assert s.config.price_step_pct == 4.0
        assert s.config.stop_loss_pct == 15.0
        assert s.config.rsi_entry_threshold == 18.0

    def test_sui_strategy_config(self):
        s = get_sui_strategy()
        assert s.config.symbol == "SUI/USDT"
        assert s.config.price_step_pct == 3.5
        assert s.config.stop_loss_pct == 12.0
        assert s.config.rsi_entry_threshold == 20.0

    def test_dca_open_position(self):
        s = get_okb_strategy()
        pos = s.open_position(100.0)
        assert pos.symbol == "OKB/USDT"
        assert pos.avg_price == 100.0
        assert pos.total_invested == 4.0
        assert len(pos.safety_prices) == 4
        assert pos.safety_prices[0] == 100.0 * 0.98  # 2% step

    def test_dca_safety_order(self):
        s = get_okb_strategy()
        pos = s.open_position(100.0)
        result = s.check_safety_order(pos, 97.0)  # Below first safety price (98)
        assert result is not None
        assert result["type"] == "safety"
        assert result["step"] == 1

    def test_dca_take_profit(self):
        s = get_okb_strategy()
        pos = s.open_position(100.0)
        tp_price = 100.0 * 1.03  # 3% TP
        result = s.check_exit(pos, tp_price)
        assert result is not None
        assert result["reason"] == "TP"
        assert pos.status == "CLOSED"

    def test_dca_stop_loss(self):
        s = get_okb_strategy()
        pos = s.open_position(100.0)
        sl_price = 100.0 * 0.91  # 9% SL
        result = s.check_exit(pos, sl_price)
        assert result is not None
        assert result["reason"] == "SL"


class TestGuard:
    """اختبارات حارس الأمان"""

    def test_validate_symbol(self):
        assert guard.validate_symbol("BTC")[0] is True
        assert guard.validate_symbol("USDT")[0] is False  # Blocked
        assert guard.validate_symbol("")[0] is False

    def test_validate_amount(self):
        assert guard.validate_amount("500")[0] is True
        assert guard.validate_amount("0.5", min_val=Decimal("1"))[0] is False
        assert guard.validate_amount("abc")[0] is False

    def test_mask_api_key(self):
        assert guard.mask_api_key("1234567890abcdef") == "12****ef"
        assert guard.mask_api_key("short") == "****"

    def test_is_write_action(self):
        assert guard.is_write_action("buy") is True
        assert guard.is_write_action("status") is False


class TestVault:
    """اختبارات الخزنة"""

    def test_encrypt_decrypt(self):
        vault = Vault("test_password_123", "test_salt")
        plaintext = "my_secret_api_key"
        encrypted = vault.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = vault.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_dict(self):
        vault = Vault("test_password_123", "test_salt")
        data = {"key1": "value1", "key2": "value2"}
        encrypted = vault.encrypt_dict(data)
        assert encrypted["key1"] != "value1"
        decrypted = vault.decrypt_dict(encrypted)
        assert decrypted["key1"] == "value1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
