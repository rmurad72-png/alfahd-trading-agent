"""
🎮 الفهد — المحفظة الافتراضية
محاكاة دقيقة للتداول الفعلي مع Spot فقط
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class VirtualWallet:
    """
    محفظة افتراضية — $100,000
    محاكاة دقيقة: رسوم، انزلاق سعري، تعرض
    """

    INITIAL_BALANCE = 100000.0
    FEE_RATE = 0.001  # 0.1% Spot fee (مثل Binance)
    SLIPPAGE = 0.05   # 0.05% انزلاق سعري

    def __init__(self, data: Optional[Dict] = None):
        data = data or {}
        self.balance = float(data.get("balance", self.INITIAL_BALANCE))
        self.invested = float(data.get("invested", 0.0))
        self.total_pnl = float(data.get("total_pnl", 0.0))
        self.positions: Dict[str, Dict] = data.get("positions", {})
        self.history: List[Dict] = data.get("history", [])
        self.reset_count = int(data.get("reset_count", 0))
        self.last_reset = data.get("last_reset")

    @property
    def total_value(self) -> float:
        """القيمة الإجمالية = رصيد + استثمارات"""
        return self.balance + self.invested

    @property
    def open_positions_count(self) -> int:
        """عدد المراكز المفتوحة"""
        return len(self.positions)

    def buy(self, symbol: str, price: float, amount_usd: float, 
            stop_loss: float = 0.0, take_profit: float = 0.0) -> Dict:
        """
        شراء افتراضي
        """
        sym = symbol.upper().replace("USDT", "") + "USDT"

        # التحقق من الرصيد
        if amount_usd > self.balance:
            return {"ok": False, "msg": f"❌ رصيدك ${self.balance:,.2f} أقل من المطلوب ${amount_usd:,.2f}"}

        if amount_usd < 1:
            return {"ok": False, "msg": "❌ الحد الأدنى للصفقة $1"}

        # حساب الرسوم والانزلاق
        fee = amount_usd * self.FEE_RATE
        slip = amount_usd * (self.SLIPPAGE / 100)
        actual_amount = amount_usd - fee - slip

        if actual_amount <= 0:
            return {"ok": False, "msg": "❌ المبلغ صغير جداً بعد الرسوم"}

        qty = actual_amount / price
        cost = amount_usd

        # تحديث المركز
        if sym in self.positions:
            # إضافة لمركز موجود
            pos = self.positions[sym]
            old_qty = pos["quantity"]
            old_cost = pos["cost"]
            new_qty = old_qty + qty
            new_cost = old_cost + cost
            avg_price = new_cost / new_qty

            self.positions[sym] = {
                "quantity": new_qty,
                "avg_price": avg_price,
                "cost": new_cost,
                "stop_loss": stop_loss if stop_loss > 0 else pos.get("stop_loss", 0),
                "take_profit": take_profit if take_profit > 0 else pos.get("take_profit", 0),
                "created_at": pos.get("created_at", datetime.now(timezone.utc).isoformat()),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            # مركز جديد
            self.positions[sym] = {
                "quantity": qty,
                "avg_price": price,
                "cost": cost,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

        # خصم من الرصيد
        self.balance -= cost
        self.invested += cost

        # تسجيل في السجل
        self.history.append({
            "type": "buy",
            "symbol": sym,
            "price": price,
            "quantity": qty,
            "cost": cost,
            "fee": fee,
            "slippage": slip,
            "time": datetime.now(timezone.utc).isoformat()
        })

        return {
            "ok": True,
            "msg": f"✅ اشتريت {qty:.6f} {sym.replace('USDT','')} @ ${price:,.4f}",
            "position": self.positions[sym]
        }

    def sell(self, symbol: str, price: float, qty: float = None) -> Dict:
        """
        بيع افتراضي
        """
        sym = symbol.upper().replace("USDT", "") + "USDT"

        if sym not in self.positions:
            return {"ok": False, "msg": f"❌ ما عندك مركز مفتوح على {sym}"}

        pos = self.positions[sym]
        max_qty = pos["quantity"]

        if qty is None or qty >= max_qty:
            qty = max_qty
            close_all = True
        else:
            close_all = False

        if qty <= 0:
            return {"ok": False, "msg": "❌ الكمية يجب أن تكون أكبر من صفر"}

        # حساب العائد
        sell_value = qty * price
        fee = sell_value * self.FEE_RATE
        slip = sell_value * (self.SLIPPAGE / 100)
        net_value = sell_value - fee - slip

        # حساب PnL
        cost_basis = (qty / max_qty) * pos["cost"]
        pnl = net_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

        # تحديث الرصيد
        self.balance += net_value
        self.invested -= cost_basis
        self.total_pnl += pnl

        # تحديث/إزالة المركز
        if close_all:
            del self.positions[sym]
        else:
            remaining_qty = max_qty - qty
            remaining_cost = pos["cost"] - cost_basis
            self.positions[sym] = {
                "quantity": remaining_qty,
                "avg_price": pos["avg_price"],
                "cost": remaining_cost,
                "stop_loss": pos.get("stop_loss", 0),
                "take_profit": pos.get("take_profit", 0),
                "created_at": pos.get("created_at"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

        # تسجيل في السجل
        trade_record = {
            "type": "sell",
            "symbol": sym,
            "price": price,
            "quantity": qty,
            "sell_value": sell_value,
            "fee": fee,
            "slippage": slip,
            "net_value": net_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "time": datetime.now(timezone.utc).isoformat()
        }
        self.history.append(trade_record)

        emoji = "🟢" if pnl >= 0 else "🔴"
        sign = "+" if pnl >= 0 else ""

        return {
            "ok": True,
            "msg": f"{emoji} بعت {qty:.6f} {sym.replace('USDT','')} @ ${price:,.4f} | PnL: {sign}${pnl:,.2f} ({sign}{pnl_pct:.2f}%)",
            "trade": trade_record,
            "pnl": pnl,
            "balance": self.balance
        }

    def get_position_pnl(self, symbol: str, current_price: float) -> Dict:
        """حساب PnL لمركز مفتوح"""
        sym = symbol.upper().replace("USDT", "") + "USDT"

        if sym not in self.positions:
            return {"ok": False, "msg": "لا يوجد مركز"}

        pos = self.positions[sym]
        qty = pos["quantity"]
        avg_price = pos["avg_price"]
        cost = pos["cost"]

        current_value = qty * current_price
        pnl = current_value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0

        return {
            "ok": True,
            "symbol": sym,
            "avg_price": avg_price,
            "current_price": current_price,
            "quantity": qty,
            "cost": cost,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "stop_loss": pos.get("stop_loss", 0),
            "take_profit": pos.get("take_profit", 0)
        }

    def check_sl_tp(self, symbol: str, current_price: float) -> Optional[Dict]:
        """التحقق من وقف الخسارة وهدف الربح"""
        sym = symbol.upper().replace("USDT", "") + "USDT"

        if sym not in self.positions:
            return None

        pos = self.positions[sym]
        sl = pos.get("stop_loss", 0)
        tp = pos.get("take_profit", 0)
        avg_price = pos["avg_price"]

        # للـ Long: SL أقل من الدخول، TP أعلى
        if sl > 0 and current_price <= sl:
            return {"action": "sell", "reason": "SL", "price": current_price}

        if tp > 0 and current_price >= tp:
            return {"action": "sell", "reason": "TP", "price": current_price}

        return None

    def reset(self) -> str:
        """إعادة ضبط المحفظة"""
        self.balance = self.INITIAL_BALANCE
        self.invested = 0.0
        self.total_pnl = 0.0
        self.positions = {}
        self.history = []
        self.reset_count += 1
        self.last_reset = datetime.now(timezone.utc).isoformat()

        return f"✅ تمت إعادة الضبط! الرصيد الجديد: ${self.INITIAL_BALANCE:,.2f}"

    def to_dict(self) -> Dict:
        """تحويل إلى dictionary"""
        return {
            "balance": self.balance,
            "invested": self.invested,
            "total_pnl": self.total_pnl,
            "positions": self.positions,
            "history": self.history,
            "reset_count": self.reset_count,
            "last_reset": self.last_reset
        }

    def report(self) -> str:
        """تقرير المحفظة"""
        lines = [
            "💼 *محفظتك الافتراضية*",
            "━━━━━━━━━━━━━━━━━━",
            f"💵 الرصيد: ${self.balance:,.2f}",
            f"📊 مستثمر: ${self.invested:,.2f}",
            f"💰 الإجمالي: ${self.total_value:,.2f}",
            f"📈 صافي الربح: ${self.total_pnl:+,.2f}",
            f"🎯 مراكز مفتوحة: {self.open_positions_count}",
            f"🔄 إعادة ضبط: {self.reset_count} مرة",
        ]

        if self.positions:
            lines.append("")
            lines.append("📋 *المراكز المفتوحة:*")
            for sym, pos in self.positions.items():
                lines.append(f"• {sym}: {pos['quantity']:.4f} @ ${pos['avg_price']:,.4f}")

        return "\n".join(lines)
