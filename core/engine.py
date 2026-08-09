"""
🐆 الفهد — المحرك الرئيسي
الموجه المركزي لجميع المكونات
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config.settings import settings
from config.tiers import TIERS
from core.database import db
from core.state_manager import state_manager
from core.data_layer import data_layer
from core.risk_engine import risk_engine, RiskDecision
from core.exchange import exchange_manager
from core.order_manager import order_manager
from core.virtual_wallet import VirtualWallet

logger = logging.getLogger(__name__)


class AlFahdEngine:
    """المحرك الرئيسي"""

    def __init__(self):
        self.is_running = False
        self._monitor_task = None

    async def init(self):
        """تهيئة جميع المكونات"""
        logger.info("🐆 initializing Al-Fahd Engine...")
        await db.init()
        await state_manager.init()
        await data_layer.init()
        await data_layer.get_top_coins(300)
        self.is_running = True
        logger.info("✅ Al-Fahd Engine ready!")

    async def shutdown(self):
        """إيقاف المحرك"""
        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        await data_layer.close()
        logger.info("🛑 Al-Fahd Engine stopped")

    async def get_or_create_user(self, telegram_id: int, **kwargs):
        """الحصول على مستخدم أو إنشاؤه"""
        user = await db.get_or_create_user(telegram_id, **kwargs)
        state_manager.set_tier(telegram_id, user.tier)
        return user

    async def get_user(self, telegram_id: int):
        """الحصول على مستخدم"""
        return await db.get_user(telegram_id)

    async def connect_exchange(self, user_id: int, exchange_id: str,
                               api_key: str, api_secret: str,
                               passphrase: str = "", testnet: bool = False) -> bool:
        """ربط منصة تداول"""
        return await exchange_manager.connect_user(
            user_id, exchange_id, api_key, api_secret, passphrase, testnet
        )

    def disconnect_exchange(self, user_id: int):
        """فصل المنصة"""
        exchange_manager.disconnect_user(user_id)

    def has_live_trading(self, user_id: int) -> bool:
        """هل المستخدم يملك تداول حقيقي؟"""
        return exchange_manager.is_connected(user_id)

    async def execute_virtual(self, user_id: int, symbol: str,
                             direction: str, size_usd: float,
                             confidence: float = 0.0) -> Dict:
        """تنفيذ صفقة افتراضية مع تقييم مخاطر كامل"""
        tier = state_manager.get_tier(user_id)

        allowed = await data_layer.is_coin_allowed(symbol, tier)
        if not allowed:
            return {"ok": False, "msg": f"❌ {symbol} غير متاح في باقتك ({tier})"}

        price_data = await data_layer.get_price(symbol)
        if not price_data:
            return {"ok": False, "msg": f"❌ تعذر جلب سعر {symbol}"}

        price = price_data["price"]

        wallet_data = await db.get_virtual_wallet(user_id)
        wallet = VirtualWallet(wallet_data or {})
        portfolio_value = wallet.total_value

        can_trade, reason = await state_manager.can_open_trade(
            user_id, size_usd, portfolio_value
        )
        if not can_trade:
            return {"ok": False, "msg": reason}

        candles = await data_layer.get_ohlcv(symbol, "1d", 30)
        atr_pct = data_layer.calc_atr(candles) if candles else 3.0
        sentiment = await data_layer.get_market_sentiment()

        assessment = risk_engine.assess(
            user_id=user_id,
            symbol=symbol,
            direction=direction,
            price=price,
            size_usd=size_usd,
            portfolio_value=portfolio_value,
            tier=tier,
            confidence=confidence,
            atr_pct=atr_pct,
            market_sentiment=sentiment["sentiment"],
            open_exposure=await state_manager.get_open_exposure(user_id)
        )

        if assessment.decision == RiskDecision.REJECT:
            return {"ok": False, "msg": assessment.reason}

        is_buy = direction in ("buy", "long")
        sl_pct = assessment.stop_loss_pct
        tp_pct = assessment.take_profit_pct

        if is_buy:
            sl_price = price * (1 - sl_pct / 100)
            tp_price = price * (1 + tp_pct / 100)
        else:
            sl_price = price * (1 + sl_pct / 100)
            tp_price = price * (1 - tp_pct / 100)

        result = await order_manager.create_virtual_trade(
            user_id=user_id,
            symbol=symbol,
            direction=direction,
            size_usd=assessment.approved_size,
            price=price,
            stop_loss=sl_price,
            take_profit=tp_price
        )

        if result.get("ok"):
            result["risk"] = {
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "rr_ratio": round(tp_pct / max(sl_pct, 0.1), 2),
                "max_hold_hours": assessment.max_hold_hours,
                "reason": assessment.reason
            }

        return result

    async def execute_live(self, user_id: int, symbol: str,
                          direction: str, size_usd: float,
                          order_type: str = "market") -> Dict:
        """تنفيذ صفقة حقيقية"""
        if not self.has_live_trading(user_id):
            return {"ok": False, "msg": "❌ ما عندك منصة مربوطة"}

        result = await self.execute_virtual(user_id, symbol, direction, size_usd)
        if not result.get("ok"):
            return result

        live_result = await order_manager.create_live_trade(
            user_id=user_id,
            symbol=symbol,
            direction=direction,
            size_usd=result.get("size_usd", size_usd),
            order_type=order_type
        )

        return live_result

    async def close_virtual_position(self, user_id: int, symbol: str,
                                     current_price: float, pct: int = 100) -> Dict:
        """إغلاق مركز افتراضي"""
        return await order_manager.close_virtual_trade(
            user_id, symbol, current_price, pct
        )

    async def get_portfolio_summary(self, user_id: int) -> Dict:
        """ملخص المحفظة"""
        user = await db.get_user(user_id)
        if not user:
            return {"error": "User not found"}

        wallet_data = await db.get_virtual_wallet(user_id)
        wallet = VirtualWallet(wallet_data or {})

        open_trades = await order_manager.get_user_trades(user_id, is_virtual=True, status="OPEN")
        today_pnl = sum(t.pnl_usd for t in open_trades if t.pnl_usd)

        risk_check = risk_engine.check_portfolio_risk(
            user_id, wallet.total_value, wallet.total_pnl, len(open_trades)
        )

        return {
            "balance": wallet.balance,
            "invested": wallet.invested,
            "total_value": wallet.total_value,
            "total_pnl": wallet.total_pnl,
            "open_positions": len(open_trades),
            "today_pnl": today_pnl,
            "tier": state_manager.get_tier_name(user_id),
            "risk_alerts": risk_check["alerts"],
            "is_healthy": risk_check["is_healthy"]
        }


# Singleton
engine = AlFahdEngine()
