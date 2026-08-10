"""
🐆 الفهد — المحرك الرئيسي
يقود جميع العمليات: تقييم، تنفيذ، مراقبة
FIXED: execute_live separated from execute_virtual, confidence from AI
"""
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from config.settings import settings
from config.tiers import TIERS
from core.database import db, async_session
from core.virtual_wallet import VirtualWallet
from core.data_layer import data_layer
from core.exchange import exchange_manager
from core.risk_engine import risk_engine, RiskDecision
from core.state_manager import state_manager
from core.order_manager import order_manager
from security.vault import get_vault
from security.guard import guard
from ai.predictor import ai_predictor

logger = logging.getLogger(__name__)


class Engine:
    """
    المحرك الرئيسي — يقود:
    1. تقييم الفرص (discover-first)
    2. تقييم المخاطر (multi-layer)
    3. تنفيذ الصفقات (write-safety)
    4. مراقبة الأداء
    """

    def __init__(self):
        self._initialized = False

    async def init(self):
        """تهيئة المحرك"""
        if self._initialized:
            return

        await db.init()
        await data_layer.init()
        await state_manager.init()
        self._initialized = True
        logger.info("🐆 Engine initialized")

    # === User Management ===

    async def get_or_create_user(self, telegram_id: int, **kwargs):
        """الحصول على مستخدم أو إنشاؤه"""
        user = await db.get_or_create_user(telegram_id, **kwargs)
        state_manager.set_tier(telegram_id, user.tier)
        return user

    async def get_user(self, telegram_id: int):
        """الحصول على مستخدم"""
        return await db.get_user(telegram_id)

    # === Portfolio ===

    async def get_portfolio_summary(self, user_id: int) -> Dict:
        """ملخص المحفظة"""
        user = await db.get_user(user_id)
        if not user:
            return {"error": "User not found"}

        wallet_data = await db.get_virtual_wallet(user_id)
        if not wallet_data:
            return {"error": "Wallet not found"}

        tier_config = TIERS.get(user.tier, TIERS["free"])
        risk_check = risk_engine.check_portfolio_risk(
            user_id, wallet_data["balance"] + wallet_data["invested"],
            wallet_data["total_pnl"], len(wallet_data.get("positions", {}))
        )

        return {
            "balance": wallet_data["balance"],
            "invested": wallet_data["invested"],
            "total_value": wallet_data["balance"] + wallet_data["invested"],
            "total_pnl": wallet_data["total_pnl"],
            "open_positions": len(wallet_data.get("positions", {})),
            "tier": tier_config["name"],
            "risk_alerts": risk_check["alerts"],
            "is_healthy": risk_check["is_healthy"],
            "drawdown_pct": risk_check["drawdown_pct"]
        }

    # === Trade Execution — FIXED: Confidence from AI ===

    async def _evaluate_trade(self, user_id: int, symbol: str, direction: str,
                              size_usd: float) -> Tuple[Dict, Dict]:
        """
        Bitget Skill: discover-first workflow
        1. Get AI signal (confidence)
        2. Get market data (price, candles, sentiment)
        3. Run risk assessment
        4. Return decision + details
        """
        user = await db.get_user(user_id)
        if not user:
            return {"ok": False, "msg": "❌ المستخدم غير موجود"}, {}

        # Step 1: AI Signal
        candles = await data_layer.get_ohlcv(symbol, "1d", 30)
        ai_result = ai_predictor.analyze(candles) if candles else {"signal": "neutral", "confidence": 0.0}
        confidence = ai_result.get("confidence", 0.0)

        # Step 2: Market Data
        price_data = await data_layer.get_price(symbol)
        if not price_data:
            return {"ok": False, "msg": f"❌ لا يمكن جلب سعر {symbol}"}, {}

        price = price_data["price"]
        sentiment = await data_layer.get_market_sentiment()

        # Step 3: Risk Assessment
        wallet_data = await db.get_virtual_wallet(user_id)
        portfolio_value = wallet_data["balance"] + wallet_data["invested"] if wallet_data else 100000
        open_exposure = wallet_data["invested"] if wallet_data else 0
        atr = data_layer.calc_atr(candles) if candles else 3.0

        assessment = risk_engine.assess(
            user_id=user_id,
            symbol=symbol,
            direction=direction,
            price=price,
            size_usd=size_usd,
            portfolio_value=portfolio_value,
            tier=user.tier,
            confidence=confidence,
            atr_pct=atr,
            market_sentiment=sentiment["sentiment"],
            daily_pnl=wallet_data.get("total_pnl", 0) if wallet_data else 0,
            open_exposure=open_exposure
        )

        details = {
            "price": price,
            "confidence": confidence,
            "ai_signal": ai_result.get("signal", "neutral"),
            "sentiment": sentiment,
            "atr": atr,
            "risk": {
                "sl_pct": assessment.stop_loss_pct,
                "tp_pct": assessment.take_profit_pct,
                "rr_ratio": round(assessment.take_profit_pct / max(assessment.stop_loss_pct, 0.1), 2)
            }
        }

        if assessment.decision == RiskDecision.REJECT:
            return {"ok": False, "msg": assessment.reason}, details

        if assessment.decision == RiskDecision.REDUCE:
            size_usd = assessment.approved_size
            details["risk"]["reduced"] = True

        details["approved_size"] = size_usd
        return {"ok": True, "msg": assessment.reason}, details

    async def execute_virtual(self, user_id: int, symbol: str, direction: str,
                              size_usd: float) -> Dict:
        """
        تنفيذ صفقة افتراضية
        Bitget Skill: --dry-run preview before execution
        """
        # Step 1: Evaluate
        result, details = await self._evaluate_trade(user_id, symbol, direction, size_usd)
        if not result["ok"]:
            return {**result, "details": details}

        approved_size = details.get("approved_size", size_usd)

        # Step 2: Check limits
        can_trade, limit_msg = await state_manager.can_open_trade(
            user_id, approved_size,
            details.get("price", 1)  # fallback
        )
        if not can_trade:
            return {"ok": False, "msg": limit_msg, "details": details}

        # Step 3: Execute
        wallet_data = await db.get_virtual_wallet(user_id)
        wallet = VirtualWallet(wallet_data) if wallet_data else VirtualWallet()

        price = details["price"]
        sl_pct = details["risk"]["sl_pct"]
        tp_pct = details["risk"]["tp_pct"]
        sl_price = price * (1 - sl_pct / 100) if direction == "buy" else price * (1 + sl_pct / 100)
        tp_price = price * (1 + tp_pct / 100) if direction == "buy" else price * (1 - tp_pct / 100)

        if direction == "buy":
            result = wallet.buy(symbol, price, approved_size, sl_price, tp_price)
        else:
            result = wallet.sell(symbol, price, approved_size)

        if result["ok"]:
            await db.update_virtual_wallet(user_id, wallet.to_dict())
            await state_manager.increment_daily_trades(user_id)
            await state_manager.add_exposure(user_id, approved_size)

            # Register order
            order_id = f"v_{user_id}_{symbol}_{int(datetime.now().timestamp())}"
            order_manager.register_order(
                user_id, order_id, symbol, direction, price, approved_size,
                sl_price, tp_price, is_virtual=True
            )

            await db.log_audit(user_id, "virtual_trade", {
                "symbol": symbol, "direction": direction,
                "size": approved_size, "price": price
            })

        return {**result, "details": details, "risk": details["risk"]}

    async def execute_live(self, user_id: int, symbol: str, direction: str,
                           size_usd: float, order_type: str = "market") -> Dict:
        """
        FIXED: تنفيذ صفقة حقيقية — منفصلة تماماً عن الافتراضية
        Bitget Skill: --confirm required, --dry-run preview
        """
        # Step 1: Check connection
        if not exchange_manager.is_connected(user_id):
            return {"ok": False, "msg": "❌ غير متصل بمنصة — استخدم /live connect"}

        # Step 2: Evaluate (same as virtual)
        result, details = await self._evaluate_trade(user_id, symbol, direction, size_usd)
        if not result["ok"]:
            return {**result, "details": details}

        approved_size = details.get("approved_size", size_usd)

        # Step 3: Check limits
        can_trade, limit_msg = await state_manager.can_open_trade(user_id, approved_size, details["price"])
        if not can_trade:
            return {"ok": False, "msg": limit_msg, "details": details}

        # Step 4: Execute via exchange
        conn = exchange_manager.get_user_exchange(user_id)
        adapter = conn["adapter"]

        order_result = await adapter.create_order(
            symbol, direction, approved_size, order_type=order_type
        )

        if not order_result:
            return {"ok": False, "msg": "❌ فشل تنفيذ الأمر على المنصة"}

        # Step 5: Record
        await state_manager.increment_daily_trades(user_id)
        await state_manager.add_exposure(user_id, approved_size)

        order_id = order_result.get("order_id", f"l_{user_id}_{symbol}")
        order_manager.register_order(
            user_id, order_id, symbol, direction,
            details["price"], approved_size,
            details["risk"]["sl_pct"], details["risk"]["tp_pct"],
            is_virtual=False, strategy="manual"
        )

        await db.log_audit(user_id, "live_trade", {
            "symbol": symbol, "direction": direction,
            "size": approved_size, "order_id": order_id,
            "exchange": conn.get("exchange_id", "unknown")
        })

        return {
            "ok": True,
            "msg": f"✅ تم التنفيذ الحقيقي: {order_id}",
            "order": order_result,
            "details": details,
            "risk": details["risk"]
        }

    # === Exchange Management ===

    async def connect_exchange(self, user_id: int, exchange_id: str,
                               api_key: str, api_secret: str,
                               passphrase: str = "") -> bool:
        """ربط منصة"""
        testnet = settings.PAPER_TRADING  # Bitget Skill: demo mode
        success = await exchange_manager.connect_user(
            user_id, exchange_id, api_key, api_secret, passphrase, testnet
        )

        if success:
            await db.log_audit(user_id, "exchange_connect", {
                "exchange": exchange_id,
                "testnet": testnet
            })
            logger.info(f"🏦 User {user_id} connected to {exchange_id}")

        return success

    def disconnect_exchange(self, user_id: int):
        """فصل منصة"""
        # Note: this is now async in exchange_manager
        import asyncio
        asyncio.create_task(exchange_manager.disconnect_user(user_id))
        logger.info(f"🔌 User {user_id} disconnected")

    def has_live_trading(self, user_id: int) -> bool:
        """هل المستخدم متصل بمنصة؟"""
        return exchange_manager.is_connected(user_id)

    # === Kill Switch ===

    async def kill_switch(self, user_id: int, reason: str = "manual") -> str:
        """إيقاف الطوارئ — إغلاق جميع المراكز"""
        wallet_data = await db.get_virtual_wallet(user_id)
        if wallet_data and wallet_data.get("positions"):
            wallet = VirtualWallet(wallet_data)
            for symbol in list(wallet.positions.keys()):
                price_data = await data_layer.get_price(symbol.replace("USDT", ""))
                if price_data:
                    wallet.sell(symbol, price_data["price"])

            await db.update_virtual_wallet(user_id, wallet.to_dict())

        await db.log_audit(user_id, "kill_switch", {"reason": reason})
        return f"🛑 Kill Switch مُفعّل: {reason}\nتم إغلاق جميع المراكز"


# Singleton
engine = Engine()
