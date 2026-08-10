"""
💎 تعريفات الباقات
"""

TIERS = {
    "free": {
        "name": "🆓 مجاني",
        "max_coins": 30,
        "max_trades_per_day": 3,
        "max_exposure_pct": 15,
        "price_monthly": 0,
    },
    "silver": {
        "name": "🥈 فضي",
        "max_coins": 100,
        "max_trades_per_day": 5,
        "max_exposure_pct": 25,
        "price_monthly": 19,
    },
    "gold": {
        "name": "🥇 ذهبي",
        "max_coins": 150,
        "max_trades_per_day": 10,
        "max_exposure_pct": 35,
        "price_monthly": 49,
    },
    "diamond": {
        "name": "💎 ماسي",
        "max_coins": 300,
        "max_trades_per_day": 50,
        "max_exposure_pct": 50,
        "price_monthly": 199,
    },
    "admin": {
        "name": "👑 مدير",
        "max_coins": 9999,
        "max_trades_per_day": 9999,
        "max_exposure_pct": 100,
        "price_monthly": 0,
    },
}
