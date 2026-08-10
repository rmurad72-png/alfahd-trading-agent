"""
🗄️ قاعدة بيانات الفهد — SQLite
"""
import sqlite3
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

from config.settings import settings

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")


def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


class Database:
    def __init__(self):
        self.db_path = DB_PATH

    async def init(self):
        def _init():
            conn = _connect()
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    tier TEXT DEFAULT 'free',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS virtual_wallets (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 100000.0,
                    positions TEXT DEFAULT '{}',
                    updated_at TEXT
                )
            """)
            c.execute("""
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
            c.execute("""
                CREATE TABLE IF NOT EXISTS exchange_credentials (
                    user_id INTEGER PRIMARY KEY,
                    exchange_id TEXT,
                    api_key TEXT,
                    api_secret TEXT,
                    passphrase TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
            conn.close()
        await asyncio.to_thread(_init)

    async def get_or_create_user(self, user_id: int, username: str = "", full_name: str = ""):
        def _get():
            conn = _connect()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                conn.close()
                return dict(row)
            now = datetime.utcnow().isoformat()
            c.execute(
                "INSERT INTO users (user_id, username, full_name, tier, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, full_name, "free", now, now)
            )
            c.execute(
                "INSERT INTO virtual_wallets (user_id, balance, positions, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, 100000.0, "{}", now)
            )
            conn.commit()
            conn.close()
            return {"user_id": user_id, "username": username, "full_name": full_name, "tier": "free"}
        return await asyncio.to_thread(_get)

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            conn = _connect()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        return await asyncio.to_thread(_get)

    async def update_user_tier(self, target_id: int, tier: str, admin_id: int):
        def _update():
            conn = _connect()
            c = conn.cursor()
            now = datetime.utcnow().isoformat()
            c.execute(
                "UPDATE users SET tier = ?, updated_at = ? WHERE user_id = ?",
                (tier, now, target_id)
            )
            conn.commit()
            conn.close()
        await asyncio.to_thread(_update)

    async def get_virtual_wallet(self, user_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            conn = _connect()
            c = conn.cursor()
            c.execute("SELECT * FROM virtual_wallets WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            conn.close()
            if row:
                d = dict(row)
                d["positions"] = json.loads(d.get("positions", "{}"))
                return d
            return None
        return await asyncio.to_thread(_get)

    async def update_virtual_wallet(self, user_id: int, balance: float, positions: Dict[str, Any]):
        def _update():
            conn = _connect()
            c = conn.cursor()
            now = datetime.utcnow().isoformat()
            c.execute(
                "UPDATE virtual_wallets SET balance = ?, positions = ?, updated_at = ? WHERE user_id = ?",
                (balance, json.dumps(positions), now, user_id)
            )
            conn.commit()
            conn.close()
        await asyncio.to_thread(_update)

    async def add_trade(self, user_id: int, symbol: str, direction: str, amount: float,
                        entry_price: float, take_profit: float, stop_loss: float) -> int:
        def _add():
            conn = _connect()
            c = conn.cursor()
            now = datetime.utcnow().isoformat()
            c.execute(
                "INSERT INTO trades (user_id, symbol, direction, amount, entry_price, take_profit, stop_loss, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, symbol, direction, amount, entry_price, take_profit, stop_loss, "open", now)
            )
            conn.commit()
            last_id = c.lastrowid
            conn.close()
            return last_id
        return await asyncio.to_thread(_add)

    async def get_open_trades(self, user_id: int) -> List[Dict[str, Any]]:
        def _get():
            conn = _connect()
            c = conn.cursor()
            c.execute("SELECT * FROM trades WHERE user_id = ? AND status = ?", (user_id, "open"))
            rows = c.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        return await asyncio.to_thread(_get)

    async def close_trade(self, trade_id: int, pnl: float):
        def _close():
            conn = _connect()
            c = conn.cursor()
            now = datetime.utcnow().isoformat()
            c.execute(
                "UPDATE trades SET status = ?, closed_at = ?, pnl = ? WHERE id = ?",
                ("closed", now, pnl, trade_id)
            )
            conn.commit()
            conn.close()
        await asyncio.to_thread(_close)

    async def save_exchange_credentials(self, user_id: int, exchange_id: str, api_key: str, api_secret: str, passphrase: str = ""):
        def _save():
            conn = _connect()
            c = conn.cursor()
            now = datetime.utcnow().isoformat()
            c.execute(
                "INSERT OR REPLACE INTO exchange_credentials (user_id, exchange_id, api_key, api_secret, passphrase, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, exchange_id, api_key, api_secret, passphrase, now)
            )
            conn.commit()
            conn.close()
        await asyncio.to_thread(_save)

    async def get_exchange_credentials(self, user_id: int) -> Optional[Dict[str, Any]]:
        def _get():
            conn = _connect()
            c = conn.cursor()
            c.execute("SELECT * FROM exchange_credentials WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        return await asyncio.to_thread(_get)


db = Database()
