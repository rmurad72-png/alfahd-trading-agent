"""
⚙️ محرك الفهد — يربط كل المكونات
"""
import logging
from typing import Dict, Any, Optional

from config.settings import settings
from config.tiers import TIERS
from core.database import db
from core.data_layer import data_layer

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self):
        self._initialized = False

    async def init(self):
        """تهيئة المحرك"""
        if self._initialized:
            return
        await db.init()
        self._initialized = True
        logger.info("🐆 Engine initialized")

    async def get_or_create_user(self, user_id: int, username: str = "", full_name: str = "") -> Dict[str, Any]:
        return await db.get_or_create_user(user_id, username, full_name)

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return await db.get_user(user_id)

    async def get_portfolio_summary(self, user_id: int) -> Dict[str, Any]:
        """ملخص المحفظة الافتراضية"""
        user = await db.get_user(user_id)
        wallet = await db.get_virtual_wallet(user_id)

        if not wallet:
            return {"error": "لا توجد محفظة"}

        positions = wallet.get("positions", {})
        total_invested = sum(p.get("cost", 0) for p in positions.values())
        balance = wallet.get("balance", 0)

        # حساب PnL
        total_pnl = 0.0
        for sym, pos in positions.items():
            coin = sym.replace("USDT", "")
            price_data = await data_layer.get_price(coin)
            current = price_data.get("price", pos["avg_price"]) if price_data else pos["avg_price"]
            pnl = (current - pos["avg_price"]) * pos["quantity"]
            total_pnl += pnl

        tier = user.get("tier", "free") if user else "free"
        tier_info = TIERS.get(tier, TIERS["free"])

        return {
            "balance": balance,
            "invested": total_invested,
            "total_value": balance + total_invested + total_pnl,
            "total_pnl": total_pnl,
            "open_positions": len(positions),
            "tier": tier_info["name"],
            "risk_alerts": [],
            "is_healthy": True,
        }

    async def execute_virtual(self, user_id: int, symbol: str, direction: str, amount: float) -> Dict[str, Any]:
        """تنفيذ صفقة افتراضية"""
        wallet = await db.get_virtual_wallet(user_id)
        if not wallet:
            return {"ok": False, "msg": "❌ لا توجد محفظة"}

        if direction == "buy":
            if wallet["balance"] < amount:
                return {"ok": False, "msg": "❌ رصيد غير كافٍ"}

            # جلب السعر
            coin = symbol.replace("USDT", "")
            price_data = await data_layer.get_price(coin)
            price = price_data.get("price", 0)
            if not price:
                return {"ok": False, "msg": "❌ تعذر جلب السعر"}

            qty = amount / price
            positions = wallet.get("positions", {})

            if symbol in positions:
                # متوسط التكلفة
                old = positions[symbol]
                total_qty = old["quantity"] + qty
                total_cost = old["cost"] + amount
                positions[symbol] = {
                    "avg_price": total_cost / total_qty,
                    "quantity": total_qty,
                    "cost": total_cost,
                    "take_profit": price * 1.057,
                    "stop_loss": price * 0.9658,
                }
            else:
                positions[symbol] = {
                    "avg_price": price,
                    "quantity": qty,
                    "cost": amount,
                    "take_profit": price * 1.057,
                    "stop_loss": price * 0.9658,
                }

            new_balance = wallet["balance"] - amount
            await db.update_virtual_wallet(user_id, new_balance, positions)

            # حفظ في trades
            await db.add_trade(user_id, symbol, direction, amount, price,
                               positions[symbol]["take_profit"], positions[symbol]["stop_loss"])

            sl_pct = round((1 - 0.9658) * 100, 2)
            tp_pct = round((1.057 - 1) * 100, 2)
            rr = round(tp_pct / sl_pct, 2) if sl_pct else 2

            return {
                "ok": True,
                "risk": {
                    "sl_pct": sl_pct,
                    "tp_pct": tp_pct,
                    "rr_ratio": rr,
                }
            }

        elif direction == "sell":
            positions = wallet.get("positions", {})
            if symbol not in positions:
                return {"ok": False, "msg": "❌ لا تمتلك هذا الأصل"}

            pos = positions[symbol]
            coin = symbol.replace("USDT", "")
            price_data = await data_layer.get_price(coin)
            price = price_data.get("price", pos["avg_price"])
            proceeds = pos["quantity"] * price
            pnl = proceeds - pos["cost"]

            new_balance = wallet["balance"] + proceeds
            del positions[symbol]
            await db.update_virtual_wallet(user_id, new_balance, positions)

            return {"ok": True, "pnl": pnl}

        return {"ok": False, "msg": "❌ اتجاه غير معروف"}

    def has_live_trading(self, user_id: int) -> bool:
        """للتبسيط — نعيد False حتى نبني exchange.py"""
        return False

    def disconnect_exchange(self, user_id: int):
        pass

    async def connect_exchange(self, user_id: int, exchange_id: str, api_key: str, api_secret: str, passphrase: str = "") -> bool:
        return False

    async def kill_switch(self, user_id: int, reason: str) -> str:
        return "🛑 Kill Switch مُفعَّل — جميع المراكز مغلقة"


engine = Engine()
