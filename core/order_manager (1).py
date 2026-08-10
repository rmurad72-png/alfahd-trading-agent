"""
📋 الفهد — مدير الأوامر
إدارة دورة حياة الصفقات من الفتح حتى الإغلاق
FIXED: Avoids circular imports by accepting engine/data_layer as parameters
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from config.tiers import TIERS

logger = logging.getLogger(__name__)


class OrderManager:
    """
    مدير الأوامر — يتتبع:
    - حالة الصفقات المفتوحة
    - تنبيهات SL/TP
    - إحصائيات الأداء
    """

    def __init__(self):
        self._open_orders: Dict[int, Dict] = {}
        self._performance: Dict[int, Dict] = {}

    def register_order(self, user_id: int, order_id: str, symbol: str,
                       side: str, entry_price: float, size_usd: float,
                       stop_loss: float = 0, take_profit: float = 0,
                       is_virtual: bool = True, strategy: str = "manual"):
        """تسجيل أمر جديد"""
        if user_id not in self._open_orders:
            self._open_orders[user_id] = {}

        self._open_orders[user_id][order_id] = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "size_usd": size_usd,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "is_virtual": is_virtual,
            "strategy": strategy,
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"📋 Order registered: {order_id} {symbol} {side} ${size_usd:.2f}")

    def close_order(self, user_id: int, order_id: str, close_price: float,
                    close_reason: str, pnl: float = 0, pnl_pct: float = 0):
        """إغلاق أمر"""
        if user_id not in self._open_orders:
            return

        order = self._open_orders[user_id].get(order_id)
        if not order:
            return

        order["status"] = "CLOSED"
        order["close_price"] = close_price
        order["close_reason"] = close_reason
        order["pnl"] = pnl
        order["pnl_pct"] = pnl_pct
        order["closed_at"] = datetime.now(timezone.utc).isoformat()

        # Track performance
        if user_id not in self._performance:
            self._performance[user_id] = {"wins": 0, "losses": 0, "total_pnl": 0.0}

        perf = self._performance[user_id]
        perf["total_pnl"] += pnl
        if pnl >= 0:
            perf["wins"] += 1
        else:
            perf["losses"] += 1

        # Remove from open orders
        self._open_orders[user_id].pop(order_id, None)

        logger.info(f"📋 Order closed: {order_id} | PnL: ${pnl:,.2f} ({close_reason})")

    def get_open_orders(self, user_id: int) -> Dict:
        """الحصول على الأوامر المفتوحة"""
        return self._open_orders.get(user_id, {})

    def get_order(self, user_id: int, order_id: str) -> Optional[Dict]:
        """الحصول على أمر محدد"""
        return self._open_orders.get(user_id, {}).get(order_id)

    def get_performance(self, user_id: int) -> Dict:
        """إحصائيات الأداء"""
        perf = self._performance.get(user_id, {"wins": 0, "losses": 0, "total_pnl": 0.0})
        total = perf["wins"] + perf["losses"]
        win_rate = (perf["wins"] / total * 100) if total > 0 else 0
        return {
            **perf,
            "total_trades": total,
            "win_rate": round(win_rate, 2)
        }

    def check_sl_tp(self, user_id: int, symbol: str, current_price: float) -> List[Dict]:
        """التحقق من SL/TP"""
        alerts = []
        orders = self._open_orders.get(user_id, {})

        for order_id, order in orders.items():
            if order["symbol"] != symbol or order["status"] != "OPEN":
                continue

            sl = order.get("stop_loss", 0)
            tp = order.get("take_profit", 0)

            if sl > 0 and current_price <= sl:
                alerts.append({
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": "SELL",
                    "reason": "SL",
                    "price": current_price,
                    "target": sl
                })

            if tp > 0 and current_price >= tp:
                alerts.append({
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": "SELL",
                    "reason": "TP",
                    "price": current_price,
                    "target": tp
                })

        return alerts

    def get_all_positions_summary(self, user_id: int) -> Dict:
        """ملخص جميع المراكز"""
        orders = self._open_orders.get(user_id, {})
        total_invested = sum(o["size_usd"] for o in orders.values() if o["status"] == "OPEN")
        total_positions = len([o for o in orders.values() if o["status"] == "OPEN"])

        return {
            "total_positions": total_positions,
            "total_invested": total_invested,
            "orders": orders
        }


# Singleton
order_manager = OrderManager()
