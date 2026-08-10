"""
🗄️ قاعدة بيانات الفهد — SQLite
"""
import aiosqlite
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from config.settings import settings

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")


class Database:
    def __init__(self):
        self.db_path = DB_PATH

    async def _connect(self):
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        return conn

    async def init(self):
        async with await self._connect() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    tier TEXT DEFAULT 'free',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS virtual_wallets (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 100000.0,
                    positions TEXT DEFAULT '{}',
                    updated_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    symbol TEXT,
                    direction TEXT,
                    amount REAL,
                    entry_price REAL,
                    take_profit REAL,
                    stop_loss REAL,
                    status TEXT DEFAULT 'open',
                    created_at TEXT,
                    closed_at TEXT,
                    pnl REAL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS exchange_credentials (
                    user_id INTEGER PRIMARY KEY,
                    exchange_id TEXT,
                    api_key TEXT,
                    api_secret TEXT,
                    passphrase TEXT,
                    created_at TEXT
                )
            """)
            await db.commit()

    async def get_or_create_user(self, user_id: int, username: str = "", full_name: str = ""):
        async with await self._connect() as db:
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            now = datetime.utcnow().isoformat()
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, tier, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, full_name, "free", now, now)
            )
            await db.execute(
                "INSERT INTO virtual_wallets (user_id, balance, positions, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, 100000.0, "{}", now)
            )
            await db.commit()
            return {"user_id": user_id, "username": username, "full_name": full_name, "tier": "free"}

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with await self._connect() as db:
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_user_tier(self, target_id: int, tier: str, admin_id: int):
        async with await self._connect() as db:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "UPDATE users SET tier = ?, updated_at = ? WHERE user_id = ?",
                (tier, now, target_id)
            )
            await db.commit()

    async def get_virtual_wallet(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with await self._connect() as db:
            cursor = await db.execute("SELECT * FROM virtual_wallets WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                d["positions"] = json.loads(d.get("positions", "{}"))
                return d
            return None

    async def update_virtual_wallet(self, user_id: int, balance: float, positions: Dict[str, Any]):
        async with await self._connect() as db:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "UPDATE virtual_wallets SET balance = ?, positions = ?, updated_at = ? WHERE user_id = ?",
                (balance, json.dumps(positions), now, user_id)
            )
            await db.commit()

    async def add_trade(self, user_id: int, symbol: str, direction: str, amount: float,
                        entry_price: float, take_profit: float, stop_loss: float) -> int:
        async with await self._connect() as db:
            now = datetime.utcnow().isoformat()
            cursor = await db.execute(
                "INSERT INTO trades (user_id, symbol, direction, amount, entry_price, take_profit, stop_loss, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, symbol, direction, amount, entry_price, take_profit, stop_loss, "open", now)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_open_trades(self, user_id: int) -> List[Dict[str, Any]]:
        async with await self._connect() as db:
            cursor = await db.execute(
                "SELECT * FROM trades WHERE user_id = ? AND status = ?", (user_id, "open")
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def close_trade(self, trade_id: int, pnl: float):
        async with await self._connect() as db:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "UPDATE trades SET status = ?, closed_at = ?, pnl = ? WHERE id = ?",
                ("closed", now, pnl, trade_id)
            )
            await db.commit()

    async def save_exchange_credentials(self, user_id: int, exchange_id: str, api_key: str, api_secret: str, passphrase: str = ""):
        async with await self._connect() as db:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO exchange_credentials (user_id, exchange_id, api_key, api_secret, passphrase, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, exchange_id, api_key, api_secret, passphrase, now)
            )
            await db.commit()

    async def get_exchange_credentials(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with await self._connect() as db:
            cursor = await db.execute("SELECT * FROM exchange_credentials WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None


db = Database()
