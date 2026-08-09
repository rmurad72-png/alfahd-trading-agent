"""
💎 نظام الباقات — الفهد
"""
from typing import Dict, Any

TIERS: Dict[str, Dict[str, Any]] = {
    "free": {
        "name": "🆓 مجاني",
        "price_usd": 0,
        "coins_limit": 30,           # أول 30 عملة من CoinGecko
        "daily_trades": 3,
        "weekly_trades": 0,          # لا يسمح بالأسبوعية
        "monthly_trades": 0,         # لا يسمح بالشهرية
        "max_exposure_pct": 0.15,    # 15% من المحفظة
        "strategies": ["spot_basic"],
        "support_priority": "low",
    },
    "silver": {
        "name": "🥈 فضي",
        "price_usd": 19,
        "coins_limit": 100,          # أول 100 عملة
        "daily_trades": 5,
        "weekly_trades": 0,
        "monthly_trades": 0,
        "max_exposure_pct": 0.25,    # 25% من المحفظة
        "strategies": ["spot_basic", "dca", "grid"],
        "support_priority": "medium",
    },
    "gold": {
        "name": "🥇 ذهبي",
        "price_usd": 49,
        "coins_limit": 150,          # أول 150 عملة
        "daily_trades": 5,
        "weekly_trades": 0,
        "monthly_trades": 0,
        "max_exposure_pct": 0.35,    # 35% من المحفظة
        "strategies": ["spot_basic", "dca", "grid", "breakout", "mean_reversion"],
        "support_priority": "high",
    },
    "diamond": {
        "name": "💎 ماسي",
        "price_usd": 199,
        "coins_limit": 300,          # أول 300 عملة + جميع أصول المنصة
        "daily_trades": 10,
        "weekly_trades": 5,
        "monthly_trades": 10,
        "max_daily_exposure_pct": 0.30,    # 30% يومي
        "max_weekly_exposure_pct": 0.20,   # 20% أسبوعي
        "max_monthly_exposure_pct": 0.15,  # 15% شهري
        "strategies": ["spot_basic", "dca", "grid", "breakout", "mean_reversion", "ai_signals"],
        "support_priority": "highest",
    },
    "admin": {
        "name": "👑 مدير",
        "price_usd": 0,
        "coins_limit": 999999,
        "daily_trades": 999999,
        "weekly_trades": 999999,
        "monthly_trades": 999999,
        "max_exposure_pct": 1.0,
        "strategies": ["all"],
        "support_priority": "admin",
    },
}

# حدود الجلسة (Session Limits) — للماسي فقط
TIER_LIMITS = {
    "free": {"daily_trades": 3, "max_open_exposure": 0.15},
    "silver": {"daily_trades": 5, "max_open_exposure": 0.25},
    "gold": {"daily_trades": 5, "max_open_exposure": 0.35},
    "diamond": {
        "daily_trades": 10, "max_daily_exposure": 0.30,
        "weekly_trades": 5, "max_weekly_exposure": 0.20,
        "monthly_trades": 10, "max_monthly_exposure": 0.15,
    },
    "admin": {"unlimited": True},
}

# ترتيب الباقات
TIER_ORDER = ["free", "silver", "gold", "diamond", "admin"]
