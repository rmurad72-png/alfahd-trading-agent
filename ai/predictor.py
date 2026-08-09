"""🧠 الفهد — محلل AI خفيف"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class AIPredictor:
    """محلل إشارات مبسط"""
    
    def analyze(self, candles: list, fear_greed: int = 50) -> Dict:
        if len(candles) < 20:
            return {"signal": "neutral", "confidence": 0.0, "reason": "بيانات غير كافية"}
        
        closes = [c["close"] for c in candles]
        sma20 = sum(closes[-20:]) / 20
        
        if closes[-1] > sma20 * 1.05:
            return {"signal": "buy", "confidence": 0.65, "reason": "فوق المتوسط 5%"}
        elif closes[-1] < sma20 * 0.95:
            return {"signal": "sell", "confidence": 0.65, "reason": "تحت المتوسط 5%"}
        return {"signal": "neutral", "confidence": 0.5, "reason": "لا إشارة واضحة"}
