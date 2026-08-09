"""
🏦 الفهد — محولات المنصات
CCXT-based adapters — Spot ONLY
"""
import logging
from typing import Dict, Optional

import ccxt.async_support as ccxt

logger = logging.getLogger(__name__)


class ExchangeAdapter:
    """محول المنصة"""

    EXCHANGE_MAP = {
        "okx": ccxt.okx,
        "bybit": ccxt.bybit,
        "bitget": ccxt.bitget,
        "mexc": ccxt.mexc,
        "binance": ccxt.binance,
    }

    def __init__(self, exchange_id: str, api_key: str = "", api_secret: str = "",
                 passphrase: str = "", testnet: bool = False):
        self.exchange_id = exchange_id.lower()
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.testnet = testnet
        self._client = None

    async def connect(self) -> bool:
        """الاتصال بالمنصة"""
        try:
            exchange_class = self.EXCHANGE_MAP.get(self.exchange_id)
            if not exchange_class:
                logger.error(f"Exchange {self.exchange_id} not supported")
                return False

            config = {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "enableRateLimit": True,
                "options": {}
            }

            if self.passphrase:
                config["password"] = self.passphrase

            if self.testnet:
                if self.exchange_id == "binance":
                    config["options"]["testnet"] = True
                elif self.exchange_id == "bybit":
                    config["options"]["testnet"] = True

            self._client = exchange_class(config)
            await self._client.load_markets()
            logger.info(f"✅ Connected to {self.exchange_id.upper()}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect {self.exchange_id}: {e}")
            return False

    async def disconnect(self):
        """فصل الاتصال"""
        if self._client:
            await self._client.close()
            self._client = None

    async def get_balance(self, currency: str = "USDT") -> Dict:
        """جلب الرصيد"""
        if not self._client:
            return {"free": 0.0, "used": 0.0, "total": 0.0}

        try:
            balance = await self._client.fetch_balance()
            curr = currency.upper()
            spot = balance.get(curr, {})
            return {
                "free": float(spot.get("free", 0)),
                "used": float(spot.get("used", 0)),
                "total": float(spot.get("total", 0))
            }
        except Exception as e:
            logger.error(f"Balance error: {e}")
            return {"free": 0.0, "used": 0.0, "total": 0.0}

    async def get_price(self, symbol: str) -> float:
        """جلب السعر"""
        if not self._client:
            return 0.0
        try:
            sym = f"{symbol.upper()}/USDT"
            ticker = await self._client.fetch_ticker(sym)
            return float(ticker.get("last", 0))
        except Exception as e:
            logger.debug(f"Price fetch error: {e}")
            return 0.0

    async def create_order(self, symbol: str, side: str, amount_usd: float,
                          price: float = 0, order_type: str = "market") -> Optional[Dict]:
        """إنشاء أمر Spot"""
        if not self._client:
            return None

        try:
            sym = f"{symbol.upper()}/USDT"

            if price <= 0:
                price = await self.get_price(symbol)

            if price <= 0:
                return None

            qty = amount_usd / price
            market = self._client.market(sym)
            amount_precision = market.get("precision", {}).get("amount", 8)
            qty = round(qty, int(amount_precision))

            order = await self._client.create_order(
                symbol=sym,
                type=order_type.lower(),
                side=side.lower(),
                amount=qty,
                price=price if order_type.lower() == "limit" else None
            )

            return {
                "order_id": order.get("id"),
                "symbol": sym,
                "side": side,
                "amount": qty,
                "price": price,
                "status": order.get("status"),
                "filled": order.get("filled", 0),
                "remaining": order.get("remaining", 0)
            }
        except Exception as e:
            logger.error(f"Order error: {e}")
            return None


class ExchangeManager:
    """مدير المنصات"""

    def __init__(self):
        self._connections: Dict[int, Dict] = {}

    async def connect_user(self, user_id: int, exchange_id: str,
                           api_key: str, api_secret: str,
                           passphrase: str = "", testnet: bool = False) -> bool:
        """ربط مستخدم بمنصة"""
        adapter = ExchangeAdapter(exchange_id, api_key, api_secret, passphrase, testnet)

        if await adapter.connect():
            self._connections[user_id] = {
                "exchange_id": exchange_id,
                "adapter": adapter,
                "testnet": testnet
            }
            return True
        return False

    def disconnect_user(self, user_id: int):
        """فصل مستخدم"""
        if user_id in self._connections:
            self._connections.pop(user_id)

    def get_user_exchange(self, user_id: int) -> Optional[Dict]:
        """الحصول على اتصال المستخدم"""
        return self._connections.get(user_id)

    def is_connected(self, user_id: int) -> bool:
        """هل المستخدم متصل؟"""
        return user_id in self._connections


# Singleton
exchange_manager = ExchangeManager()
