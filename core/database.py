"""
🗄️ الفهد — طبقة قاعدة البيانات
SQLAlchemy 2.0 + asyncpg
FIXED: back_populates relationships, renamed VirtualWalletDB
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float,
    Boolean, DateTime, Text, JSON, ForeignKey, Index, select, and_
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

from config.settings import settings

logger = logging.getLogger(__name__)
Base = declarative_base()

# === Engine & Session ===
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# === Models ===

class User(Base):
    """👤 المستخدم"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100))
    full_name = Column(String(200))
    tier = Column(String(20), default="free", nullable=False)
    language = Column(String(10), default="ar")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # FIXED: back_populates matches child models
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    virtual_wallet_db = relationship("VirtualWalletDB", back_populates="user", uselist=False)
    strategy_configs = relationship("StrategyConfig", back_populates="user", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    """🔑 مفاتيح API المشفّرة"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    exchange = Column(String(20), nullable=False)
    api_key_enc = Column(Text, nullable=False)
    api_secret_enc = Column(Text, nullable=False)
    passphrase_enc = Column(Text)
    is_testnet = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (Index("idx_apikey_user_ex", "user_id", "exchange"),)


class Trade(Base):
    """📊 الصفقات"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    size_usd = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String(20), default="OPEN")
    pnl_usd = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    close_price = Column(Float)
    close_reason = Column(String(50))
    strategy = Column(String(50), default="manual")
    is_virtual = Column(Boolean, default=True)
    exchange = Column(String(20))
    order_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="trades")

    __table_args__ = (
        Index("idx_trade_user_status", "user_id", "status"),
        Index("idx_trade_created", "created_at"),
    )


class VirtualWalletDB(Base):
    """🎮 المحفظة الافتراضية (DB Model) — RENAMED to avoid conflict with core.virtual_wallet.VirtualWallet"""
    __tablename__ = "virtual_wallets"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False)
    balance = Column(Float, default=100000.0)
    invested = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    positions = Column(JSON, default=dict)
    history = Column(JSON, default=list)
    reset_count = Column(Integer, default=0)
    last_reset = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="virtual_wallet_db")


class Payment(Base):
    """💳 المدفوعات"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    tier_target = Column(String(20), nullable=False)
    amount_usd = Column(Float, nullable=False)
    tx_hash = Column(String(100))
    status = Column(String(20), default="pending")
    confirmed_by = Column(BigInteger)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="payments")


class AuditLog(Base):
    """📋 سجل المراجعة"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(50), nullable=False)
    details = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_audit_user_time", "user_id", "created_at"),)


class StrategyConfig(Base):
    """⚙️ إعدادات الاستراتيجيات"""
    __tablename__ = "strategy_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="strategy_configs")


class Approval(Base):
    """✅ موافقات المستخدم"""
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    plan_type = Column(String(20), nullable=False)
    plan_data = Column(JSON, nullable=False)
    status = Column(String(20), default="pending")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="approvals")


# === Database Operations ===

class Database:
    """مدير قاعدة البيانات"""

    @staticmethod
    async def init():
        """إنشاء الجداول"""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("🗄️ Database tables created")

    @staticmethod
    async def get_session() -> AsyncSession:
        """الحصول على session"""
        return async_session()

    @staticmethod
    async def get_or_create_user(telegram_id: int, **kwargs) -> User:
        """الحصول على مستخدم أو إنشاؤه"""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(telegram_id=telegram_id, **kwargs)
                session.add(user)
                wallet = VirtualWalletDB(user_id=telegram_id)
                session.add(wallet)
                await session.commit()
                logger.info(f"👤 New user created: {telegram_id}")

            return user

    @staticmethod
    async def get_user(telegram_id: int) -> Optional[User]:
        """الحصول على مستخدم"""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def update_user_tier(telegram_id: int, new_tier: str, by_admin: int):
        """تحديث باقة المستخدم"""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user:
                old_tier = user.tier
                user.tier = new_tier

                audit = AuditLog(
                    user_id=telegram_id,
                    action="tier_change",
                    details={
                        "old_tier": old_tier,
                        "new_tier": new_tier,
                        "changed_by": by_admin
                    }
                )
                session.add(audit)
                await session.commit()
                logger.info(f"💎 Tier changed: {telegram_id} {old_tier} -> {new_tier}")
                return True
            return False

    @staticmethod
    async def log_audit(user_id: int, action: str, details: dict):
        """تسجيل حدث"""
        async with async_session() as session:
            audit = AuditLog(user_id=user_id, action=action, details=details)
            session.add(audit)
            await session.commit()

    @staticmethod
    async def get_virtual_wallet(user_id: int) -> Optional[Dict]:
        """الحصول على المحفظة الافتراضية"""
        async with async_session() as session:
            result = await session.execute(
                select(VirtualWalletDB).where(VirtualWalletDB.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            if wallet:
                return {
                    "balance": wallet.balance,
                    "invested": wallet.invested,
                    "total_pnl": wallet.total_pnl,
                    "positions": wallet.positions or {},
                    "history": wallet.history or [],
                    "reset_count": wallet.reset_count,
                    "last_reset": wallet.last_reset.isoformat() if wallet.last_reset else None
                }
            return None

    @staticmethod
    async def update_virtual_wallet(user_id: int, data: dict):
        """تحديث المحفظة الافتراضية"""
        async with async_session() as session:
            result = await session.execute(
                select(VirtualWalletDB).where(VirtualWalletDB.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            if wallet:
                wallet.balance = data.get("balance", wallet.balance)
                wallet.invested = data.get("invested", wallet.invested)
                wallet.total_pnl = data.get("total_pnl", wallet.total_pnl)
                wallet.positions = data.get("positions", wallet.positions)
                wallet.history = data.get("history", wallet.history)
                wallet.reset_count = data.get("reset_count", wallet.reset_count)
                await session.commit()


# Singleton
db = Database()
