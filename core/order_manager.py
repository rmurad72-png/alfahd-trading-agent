"""
📋 الفهد — مدير الأوامر
إدارة دورة حياة الصفقات
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.database import Trade, async_session, db
from core.state_manager import state_manager
from core.exchange import exchange_manager
from core.virtual_wallet import VirtualWallet

logger = logging.getLogger(__name__)


class OrderManager:
    """مدير الأوامر"""

    def __init__(self):
        self._pending_approvals: Dict[str, Dict] = {}

    async def create_virtual_trade(self, user_id: int, symbol: str,
                                    direction: str, size_usd: float,
                                    price: float, stop_loss: float = 0,
                                    take_profit: float = 0) -> Dict:
        """إنشاء صفقة افتراضية"""
        wallet_data = await db.get_virtual_wallet(user_id)
        wallet = VirtualWallet(wallet_data or {})

        is_buy = direction in ("buy", "long")

        if is_buy:
            result = wallet.buy(symbol, price, size_usd, stop_loss, take_profit)
        else:
            result = wallet.sell(symbol, price)

        if result.get("ok"):
            # حفظ في DB
            async with async_session() as session:
                trade = Trade(
                    user_id=user_id,
                    symbol=symbol.upper(),
                    side="BUY" if is_buy else "SELL",
                    size_usd=size_usd,
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    status="OPEN",
                    is_virtual=True,
                    strategy="manual"
                )
                session.add(trade)
                await session.commit()

            # تحديث المحفظة
            await db.update_virtual_wallet(user_id, wallet.to_dict())

            # تحديث التعرض
            await state_manager.add_exposure(user_id, size_usd)
            await state_manager.increment_daily_trades(user_id)

            logger.info(f"🎮 Virtual trade: {user_id} {symbol} {direction} ${size_usd:.2f}")

        return result

    async def create_live_trade(self, user_id: int, symbol: str,
                                 direction: str, size_usd: float,
                                 price: float = 0, order_type: str = "market",
                                 stop_loss: float = 0, take_profit: float = 0) -> Dict:
        """إنشاء صفقة حقيقية"""
        conn = exchange_manager.get_user_exchange(user_id)
        if not conn:
            return {"ok": False, "msg": "❌ ما عندك منصة مربوطة"}

        adapter = conn["adapter"]

        # فحص الرصيد
        balance = await adapter.get_balance("USDT")
        if balance["free"] < size_usd * 1.05:
            return {
                "ok": False, 
                "msg": f"❌ رصيدك ${balance['free']:,.2f} ما يكفي"
            }

        # إنشاء الأمر
        side = "buy" if direction in ("buy", "long") else "sell"
        order = await adapter.create_order(symbol, side, size_usd, price, order_type)

        if not order:
            return {"ok": False, "msg": "❌ فشل في إنشاء الأمر"}

        # حفظ في DB
        async with async_session() as session:
            trade = Trade(
                user_id=user_id,
                symbol=symbol.upper(),
                side=side.upper(),
                size_usd=size_usd,
                entry_price=order["price"],
                stop_loss=stop_loss,
                take_profit=take_profit,
                status="OPEN",
                is_virtual=False,
                exchange=conn["exchange_id"],
                order_id=order["order_id"],
                strategy="manual"
            )
            session.add(trade)
            await session.commit()

        await state_manager.add_exposure(user_id, size_usd)
        await state_manager.increment_daily_trades(user_id)

        logger.info(f"💰 Live trade: {user_id} {symbol} {side} ${size_usd:.2f}")

        return {
            "ok": True,
            "msg": f"✅ تم التنفيذ على {conn['exchange_id'].upper()}",
            "order": order
        }

    async def close_virtual_trade(self, user_id: int, symbol: str,
                                   current_price: float, pct: int = 100) -> Dict:
        """إغلاق صفقة افتراضية"""
        wallet_data = await db.get_virtual_wallet(user_id)
        wallet = VirtualWallet(wallet_data or {})

        sym = symbol.upper().replace("USDT", "") + "USDT"

        if sym not in wallet.positions:
            return {"ok": False, "msg": f"❌ ما عندك مركز على {sym}"}

        pos = wallet.positions[sym]
        qty = pos["quantity"]

        if pct < 100:
            qty = qty * (pct / 100)

        result = wallet.sell(sym, current_price, qty)

        if result.get("ok"):
            await db.update_virtual_wallet(user_id, wallet.to_dict())

            removed = pos["cost"] * (pct / 100)
            await state_manager.remove_exposure(user_id, removed)

            logger.info(f"🎮 Virtual close: {user_id} {sym} {pct}% @ ${current_price:.4f}")

        return result

    async def get_user_trades(self, user_id: int, is_virtual: bool = True,
                               status: str = "OPEN", limit: int = 20) -> List[Trade]:
        """الحصول على صفقات المستخدم"""
        async with async_session() as session:
            from sqlalchemy import select, and_
            stmt = select(Trade).where(
                and_(
                    Trade.user_id == user_id,
                    Trade.is_virtual == is_virtual,
                    Trade.status == status
                )
            ).order_by(Trade.created_at.desc()).limit(limit)

            result = await session.execute(stmt)
            return result.scalars().all()


# Singleton
order_manager = OrderManager()
