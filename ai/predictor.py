"""
🧠 الفهد — محلل الذكاء الاصطناعي
Technical Analysis + Signal Quality Scoring
"""
import logging
from typing import Dict, List, Optional
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class AIPredictor:
    """
    محلل إشارات التداول
    - SMA Crossover
    - RSI
    - MACD
    - Bollinger Bands
    - Signal Quality Scoring (0.0 - 1.0)
    """

    def __init__(self):
        self.min_candles = 50

    def analyze(self, candles: List[Dict]) -> Dict:
        """
        تحليل الشموع وإنتاج إشارة مع confidence score
        """
        if not candles or len(candles) < self.min_candles:
            return {"signal": "neutral", "confidence": 0.0, "reason": "Insufficient data"}

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]

        # === Indicators ===
        sma20 = self._sma(closes, 20)
        sma50 = self._sma(closes, 50)
        rsi = self._rsi(closes, 14)
        macd, macd_signal, macd_hist = self._macd(closes)
        bb_upper, bb_lower, bb_pct = self._bollinger(closes, 20)
        vol_trend = self._volume_trend(volumes)

        # === Signal Scoring ===
        score = 0.0
        reasons = []

        # Trend: SMA20 vs SMA50
        if sma20 and sma50:
            if sma20 > sma50 * 1.02:
                score += 0.25
                reasons.append("SMA20 > SMA50 (bullish)")
            elif sma20 < sma50 * 0.98:
                score -= 0.25
                reasons.append("SMA20 < SMA50 (bearish)")

        # Momentum: RSI
        if rsi is not None:
            if rsi < 30:
                score += 0.20  # Oversold = buy signal
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                score -= 0.20  # Overbought = sell signal
                reasons.append(f"RSI overbought ({rsi:.1f})")
            elif 40 <= rsi <= 60:
                score += 0.05  # Neutral but stable

        # MACD
        if macd_hist is not None:
            if macd_hist > 0 and macd > macd_signal:
                score += 0.20
                reasons.append("MACD bullish crossover")
            elif macd_hist < 0 and macd < macd_signal:
                score -= 0.20
                reasons.append("MACD bearish crossover")

        # Bollinger Bands
        if bb_pct is not None:
            if bb_pct < 0.1:
                score += 0.15
                reasons.append("Price near lower BB (oversold)")
            elif bb_pct > 0.9:
                score -= 0.15
                reasons.append("Price near upper BB (overbought)")

        # Volume Confirmation
        if vol_trend:
            score += 0.10
            reasons.append("Volume confirming trend")

        # === Determine Signal ===
        confidence = min(abs(score) + 0.3, 1.0)  # Base confidence + signal strength

        if score > 0.3:
            signal = "buy"
        elif score < -0.3:
            signal = "sell"
        else:
            signal = "neutral"
            confidence = max(confidence, 0.4)  # Minimum for neutral

        return {
            "signal": signal,
            "confidence": round(confidence, 2),
            "score": round(score, 3),
            "indicators": {
                "sma20": round(sma20, 4) if sma20 else None,
                "sma50": round(sma50, 4) if sma50 else None,
                "rsi": round(rsi, 2) if rsi else None,
                "macd": round(macd, 4) if macd else None,
                "macd_signal": round(macd_signal, 4) if macd_signal else None,
                "bb_position": round(bb_pct, 2) if bb_pct else None,
            },
            "reasons": reasons,
            "recommendation": self._get_recommendation(signal, confidence)
        }

    def _sma(self, data: List[float], period: int) -> Optional[float]:
        """Simple Moving Average"""
        if len(data) < period:
            return None
        return mean(data[-period:])

    def _rsi(self, data: List[float], period: int = 14) -> Optional[float]:
        """Relative Strength Index"""
        if len(data) < period + 1:
            return None

        gains = []
        losses = []

        for i in range(1, min(len(data), period + 1)):
            change = data[-i] - data[-i - 1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))

        if not gains and not losses:
            return 50.0

        avg_gain = mean(gains) if gains else 0.001
        avg_loss = mean(losses) if losses else 0.001

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _macd(self, data: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """MACD Indicator"""
        if len(data) < slow + signal:
            return None, None, None

        ema_fast = self._ema(data, fast)
        ema_slow = self._ema(data, slow)

        if ema_fast is None or ema_slow is None:
            return None, None, None

        macd_line = ema_fast - ema_slow

        # Signal line = EMA of MACD
        macd_values = []
        for i in range(slow, len(data)):
            e_f = self._ema(data[:i+1], fast)
            e_s = self._ema(data[:i+1], slow)
            if e_f and e_s:
                macd_values.append(e_f - e_s)

        signal_line = self._ema(macd_values, signal) if len(macd_values) >= signal else macd_values[-1] if macd_values else 0
        histogram = macd_line - signal_line if signal_line else 0

        return macd_line, signal_line, histogram

    def _ema(self, data: List[float], period: int) -> Optional[float]:
        """Exponential Moving Average"""
        if len(data) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = mean(data[:period])

        for price in data[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def _bollinger(self, data: List[float], period: int = 20, std_dev: int = 2) -> tuple:
        """Bollinger Bands"""
        if len(data) < period:
            return None, None, None

        sma = mean(data[-period:])
        variance = sum((x - sma) ** 2 for x in data[-period:]) / period
        std = variance ** 0.5

        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)

        current = data[-1]
        band_width = upper - lower
        position = (current - lower) / band_width if band_width > 0 else 0.5

        return upper, lower, position

    def _volume_trend(self, volumes: List[float]) -> bool:
        """Volume trend confirmation"""
        if len(volumes) < 10:
            return False
        recent = mean(volumes[-5:])
        older = mean(volumes[-10:-5])
        return recent > older * 1.1  # 10% increase

    def _get_recommendation(self, signal: str, confidence: float) -> str:
        """توصية نصية"""
        if signal == "buy" and confidence > 0.7:
            return "🟢 إشارة شراء قوية"
        elif signal == "buy":
            return "🟡 إشارة شراء ضعيفة"
        elif signal == "sell" and confidence > 0.7:
            return "🔴 إشارة بيع قوية"
        elif signal == "sell":
            return "🟠 إشارة بيع ضعيفة"
        else:
            return "⚪ محايد — انتظر"


# Singleton
ai_predictor = AIPredictor()
