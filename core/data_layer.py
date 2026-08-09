"""
📡 الفهد — طبقة البيانات
جلب الأسعار والشموع من مصادر مجانية وموثوقة
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal

import aiohttp
import ccxt.async_support as ccxt
from config.settings import settings

logger = logging.getLogger(__name__)


class DataLayer:
    """
    طبقة البيانات — مصادر مجانية:
    - CoinGecko: الأسعار والتصنيف
    - CCXT: الشموع (OHLCV) من المنصات
    - Alternative.me: Fear & Greed
    """

    COINGECKO_BASE = "https://api.coingecko.com/api/v3"
    FEAR_GREED_URL = "https://api.alternative.me/fng/"

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 30  # 30 ثانية للأسعار
        self._top_coins: List[str] = []
        self._top_coins_last_fetch: Optional[datetime] = None

    async def init(self):
        """تهيئة الجلسة"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        logger.info("📡 DataLayer initialized")

    async def close(self):
        """إغلاق الجلسة"""
        if self._session:
            await self._session.close()

    # === CoinGecko: Top Coins ===

    async def get_top_coins(self, limit: int = 300) -> List[Dict]:
        """الحصول على أفضل العملات من CoinGecko"""
        cache_key = f"top_coins:{limit}"

        # التحقق من الكاش
        if cache_key in self._cache:
            last = self._cache_time.get(cache_key)
            if last and (datetime.now(timezone.utc) - last).seconds < 300:  # 5 دقائق
                return self._cache[cache_key]

        url = f"{self.COINGECKO_BASE}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": min(limit, 250),  # CoinGecko max 250 per page
            "page": 1,
            "sparkline": "false"
        }

        if settings.COINGECKO_API_KEY:
            params["x_cg_demo_api_key"] = settings.COINGECKO_API_KEY

        try:
            async with self._session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._cache[cache_key] = data
                    self._cache_time[cache_key] = datetime.now(timezone.utc)
                    self._top_coins = [c["symbol"].upper() for c in data]
                    self._top_coins_last_fetch = datetime.now(timezone.utc)
                    logger.info(f"📊 Fetched {len(data)} top coins")
                    return data
                else:
                    logger.warning(f"CoinGecko error: {resp.status}")
                    return self._cache.get(cache_key, [])
        except Exception as e:
            logger.error(f"get_top_coins error: {e}")
            return self._cache.get(cache_key, [])

    async def get_coin_list(self, limit: int = 300) -> List[str]:
        """قائمة رموز العملات فقط"""
        coins = await self.get_top_coins(limit)
        return [c["symbol"].upper() for c in coins]

    async def is_coin_allowed(self, symbol: str, tier: str) -> bool:
        """التحقق إذا كانت العملة مسموحة للباقة"""
        config = {
            "free": 30, "silver": 100, "gold": 150, 
            "diamond": 300, "admin": 999999
        }.get(tier, 30)

        if not self._top_coins or not self._top_coins_last_fetch:
            await self.get_top_coins(config)

        sym = symbol.upper().replace("USDT", "")

        # الماسي والمدير: جميع العملات + أصول المنصة
        if tier in ("diamond", "admin"):
            return True

        try:
            idx = self._top_coins.index(sym)
            return idx < config
        except ValueError:
            return False

    # === Price Feeds ===

    async def get_price(self, symbol: str) -> Optional[Dict]:
        """جلب سعر العملة"""
        cache_key = f"price:{symbol.upper()}"

        if cache_key in self._cache:
            last = self._cache_time.get(cache_key)
            if last and (datetime.now(timezone.utc) - last).seconds < self._cache_ttl:
                return self._cache[cache_key]

        # محاولة من CoinGecko
        sym = symbol.upper().replace("USDT", "").lower()
        url = f"{self.COINGECKO_BASE}/simple/price"
        params = {
            "ids": sym,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }

        if settings.COINGECKO_API_KEY:
            params["x_cg_demo_api_key"] = settings.COINGECKO_API_KEY

        try:
            async with self._session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if sym in data:
                        result = {
                            "symbol": symbol.upper(),
                            "price": float(data[sym]["usd"]),
                            "change_24h": float(data[sym].get("usd_24h_change", 0)),
                            "source": "coingecko",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        self._cache[cache_key] = result
                        self._cache_time[cache_key] = datetime.now(timezone.utc)
                        return result
        except Exception as e:
            logger.debug(f"CoinGecko price error: {e}")

        # Fallback: CCXT
        try:
            exchange = ccxt.okx()
            ticker = await exchange.fetch_ticker(f"{symbol.upper()}/USDT")
            await exchange.close()
            result = {
                "symbol": symbol.upper(),
                "price": float(ticker["last"]),
                "change_24h": float(ticker.get("percentage", 0)),
                "source": "okx",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self._cache[cache_key] = result
            self._cache_time[cache_key] = datetime.now(timezone.utc)
            return result
        except Exception as e:
            logger.debug(f"OKX price fallback error: {e}")

        return None

    # === OHLCV (Candles) ===

    async def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> List[Dict]:
        """جلب الشموع"""
        cache_key = f"ohlcv:{symbol.upper()}:{timeframe}:{limit}"

        if cache_key in self._cache:
            last = self._cache_time.get(cache_key)
            if last and (datetime.now(timezone.utc) - last).seconds < 300:
                return self._cache[cache_key]

        try:
            exchange = ccxt.okx()
            ohlcv = await exchange.fetch_ohlcv(
                f"{symbol.upper()}/USDT", 
                timeframe=timeframe, 
                limit=limit
            )
            await exchange.close()

            candles = []
            for c in ohlcv:
                candles.append({
                    "timestamp": c[0],
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5])
                })

            self._cache[cache_key] = candles
            self._cache_time[cache_key] = datetime.now(timezone.utc)
            return candles
        except Exception as e:
            logger.error(f"OHLCV error: {e}")
            return self._cache.get(cache_key, [])

    # === Fear & Greed ===

    async def get_fear_greed(self) -> Optional[Dict]:
        """مؤشر الخوف والطمع"""
        cache_key = "fear_greed"

        if cache_key in self._cache:
            last = self._cache_time.get(cache_key)
            if last and (datetime.now(timezone.utc) - last).seconds < 3600:  # 1 ساعة
                return self._cache[cache_key]

        try:
            async with self._session.get(self.FEAR_GREED_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = {
                        "value": int(data["data"][0]["value"]),
                        "classification": data["data"][0]["value_classification"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    self._cache[cache_key] = result
                    self._cache_time[cache_key] = datetime.now(timezone.utc)
                    return result
        except Exception as e:
            logger.error(f"Fear & Greed error: {e}")

        return {"value": 50, "classification": "Neutral", "timestamp": datetime.now(timezone.utc).isoformat()}

    # === ATR Calculation ===

    @staticmethod
    def calc_atr(candles: List[Dict], period: int = 14) -> float:
        """حساب Average True Range"""
        if len(candles) < period + 1:
            return 3.0  # default

        trs = []
        for i in range(1, min(len(candles), period + 5)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i-1]["close"]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)

        if not trs:
            return 3.0

        atr = sum(trs[-period:]) / period
        current_price = candles[-1]["close"]
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 3.0

        return round(atr_pct, 2)

    # === Market Sentiment ===

    async def get_market_sentiment(self) -> Dict:
        """تحليل المشاعر العامة"""
        fg = await self.get_fear_greed()
        value = fg.get("value", 50)

        if value <= 20:
            return {"sentiment": "extreme_fear", "emoji": "😱", "advice": "السوق في رعب شديد — فرصة شراء محتملة"}
        elif value <= 40:
            return {"sentiment": "fear", "emoji": "😰", "advice": "السوق خائف — كن حذراً"}
        elif value <= 60:
            return {"sentiment": "neutral", "emoji": "😐", "advice": "السوق محايد — انتظر فرصة واضحة"}
        elif value <= 80:
            return {"sentiment": "greed", "emoji": "😏", "advice": "السوق طماع — لا تتبع القطيع"}
        else:
            return {"sentiment": "extreme_greed", "emoji": "🤑", "advice": "السوق في طمع شديد — احذر التصحيح"}


# Singleton
data_layer = DataLayer()
