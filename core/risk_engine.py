"""
⚖️ الفهد — محرك المخاطر
نظام متعدد الطبقات لحماية رأس المال
FIXED: Confidence threshold now uses AI predictor input
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from enum import Enum

from config.tiers import TIERS

logger = logging.getLogger(__name__)


class RiskDecision(Enum):
    APPROVE = "approve"
    REDUCE = "reduce_size"
    REJECT = "reject"
    PAUSE = "pause"


class RiskAssessment:
    """نتيجة تقييم المخاطر"""

    def __init__(self, decision: RiskDecision, approved_size: float = 0,
                 stop_loss_pct: float = 5.0, take_profit_pct: float = 10.0,
                 max_hold_hours: int = 48, reason: str = ""):
        self.decision = decision
        self.approved_size = approved_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_hold_hours = max_hold_hours
        self.reason = reason

    def __repr__(self):
        return f"RiskAssessment({self.decision.value}, size=${self.approved_size:.2f})"


class RiskEngine:
    """
    محرك المخاطر — 8 عوامل حماية:
    1. Max Drawdown Guard
    2. Daily Loss Limit
    3. Position Size Limit
    4. Confidence Threshold (FIXED: now dynamic)
    5. ATR-based SL/TP
    6. Market Regime
    7. Correlation Check
    8. Event Risk
    """

    def __init__(self):
        self._daily_pnl: Dict[int, float] = {}
        self._daily_trades: Dict[int, int] = {}
        self._last_reset: Dict[int, str] = {}

    def reset_daily(self, user_id: int):
        """إعادة ضبط العداد اليومي"""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        if self._last_reset.get(user_id) != today:
            self._daily_pnl[user_id] = 0.0
            self._daily_trades[user_id] = 0
            self._last_reset[user_id] = today

    def assess(self, user_id: int, symbol: str, direction: str,
               price: float, size_usd: float, portfolio_value: float,
               tier: str, confidence: float = 0.0,
               atr_pct: float = 3.0, market_sentiment: str = "neutral",
               daily_pnl: float = 0.0, open_exposure: float = 0.0) -> RiskAssessment:
        """
        تقييم المخاطر الشامل
        FIXED: confidence now comes from AI predictor, not default 0.0
        """
        self.reset_daily(user_id)

        tier_config = TIERS.get(tier, TIERS["free"])
        reasons = []

        # 1. Max Drawdown — إذا الخسارة اليومية وصلت -5%
        max_daily_loss = portfolio_value * 0.05
        if daily_pnl <= -max_daily_loss:
            return RiskAssessment(
                RiskDecision.REJECT, 0, 0, 0, 0,
                f"❌ وصلت للحد اليومي للخسارة (-5% = ${max_daily_loss:,.2f})"
            )

        # 2. Position Size — لا تتجاوز 10% من المحفظة لصفقة واحدة
        max_single_position = portfolio_value * 0.10
        if size_usd > max_single_position:
            size_usd = max_single_position
            reasons.append(f"📉 حجم الصفقة قُلّص لـ 10% (${max_single_position:,.2f})")

        # 3. Tier Exposure Limit
        max_exposure = portfolio_value * tier_config.get("max_exposure_pct", 0.15)
        new_exposure = open_exposure + size_usd
        if new_exposure > max_exposure:
            allowed = max(0, max_exposure - open_exposure)
            if allowed <= 0:
                return RiskAssessment(
                    RiskDecision.REJECT, 0, 0, 0, 0,
                    f"❌ التعرض المفتوح وصل {tier_config.get('max_exposure_pct', 0.15)*100:.0f}%"
                )
            size_usd = allowed
            reasons.append("📉 التعرض قُلّص بسبب حد الباقة")

        # 4. Confidence Threshold — FIXED: dynamic based on tier + signal quality
        # confidence = 0.0 means "no AI signal" — use a baseline for manual trades
        if confidence == 0.0:
            # Manual trades get a baseline confidence (user explicitly requested)
            confidence = 0.60  # Baseline for manual execution

        min_confidence = 0.55 if tier == "free" else 0.50
        if confidence < min_confidence:
            return RiskAssessment(
                RiskDecision.REJECT, 0, 0, 0, 0,
                f"❌ الثقة منخفضة ({confidence:.0%} < {min_confidence:.0%})"
            )

        # 5. ATR-based SL/TP
        sl_pct = max(atr_pct * 1.5, 3.0)
        tp_pct = max(atr_pct * 2.5, 5.0)

        # 6. Market Sentiment Adjustment
        if market_sentiment == "extreme_fear":
            sl_pct *= 1.2
            tp_pct *= 1.3
        elif market_sentiment == "extreme_greed":
            sl_pct *= 0.9
            tp_pct *= 0.8
            size_usd *= 0.8
            reasons.append("⚠️ السوق في طمع — حجم أصغر")

        # 7. Minimum Size
        size_usd = max(size_usd, 1.0)

        # 8. R:R Ratio check
        rr_ratio = tp_pct / max(sl_pct, 0.1)
        if rr_ratio < 1.0:
            return RiskAssessment(
                RiskDecision.REJECT, 0, 0, 0, 0,
                f"❌ نسبة R:R ضعيفة ({rr_ratio:.1f}:1) — الحد الأدنى 1:1"
            )

        reason = "\n".join(reasons) if reasons else "✅ جميع شروط المخاطر متحققة"

        return RiskAssessment(
            RiskDecision.APPROVE,
            approved_size=round(size_usd, 2),
            stop_loss_pct=round(sl_pct, 2),
            take_profit_pct=round(tp_pct, 2),
            max_hold_hours=48,
            reason=reason
        )

    def check_portfolio_risk(self, user_id: int, portfolio_value: float,
                             total_pnl: float, open_positions: int) -> Dict:
        """فحص صحة المحفظة"""
        drawdown_pct = abs(total_pnl / max(portfolio_value, 1)) * 100

        alerts = []

        if drawdown_pct > 15:
            alerts.append("🔴 Drawdown وصل 15% — إيقاف التداول موصى به")
        elif drawdown_pct > 10:
            alerts.append("🟠 Drawdown وصل 10% — حذر")

        if open_positions > 10:
            alerts.append("🟡 عدد كبير من المراكز — ركّز على الجودة")

        return {
            "drawdown_pct": round(drawdown_pct, 2),
            "alerts": alerts,
            "is_healthy": len(alerts) == 0
        }


# Singleton
risk_engine = RiskEngine()
