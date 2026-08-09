"""
📊 الفهد — مدير الحالة
يتتبع: الباقات، حدود الصفقات، التعرض، الموافقات
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

import redis.asyncio as redis
from config.settings import settings
from config.tiers import TIERS, TIER_LIMITS

logger = logging.getLogger(__name__)


class StateManager:
    """
    مدير الحالة — يتتبع جميع القيود والحدود
    """

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._local_cache: Dict = {}

    async def init(self):
        """تهيئة Redis"""
        try:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await self._redis.ping()
            logger.info("🔌 Redis connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, using local cache: {e}")
            self._redis = None

    # === Tier Management ===

    def get_tier(self, user_id: int) -> str:
        """الحصول على باقة المستخدم"""
        return self._local_cache.get(f"tier:{user_id}", "free")

    def set_tier(self, user_id: int, tier: str):
        """تعيين باقة المستخدم"""
        self._local_cache[f"tier:{user_id}"] = tier

    def get_tier_name(self, user_id: int) -> str:
        """اسم الباقة بالعربية"""
        tier = self.get_tier(user_id)
        return TIERS.get(tier, TIERS["free"])["name"]

    def get_tier_config(self, user_id: int) -> dict:
        """إعدادات الباقة"""
        tier = self.get_tier(user_id)
        return TIERS.get(tier, TIERS["free"])

    # === Trade Limits ===

    async def get_daily_trades(self, user_id: int) -> int:
        """عدد الصفقات اليومية"""
        key = f"trades:daily:{user_id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        if self._redis:
            count = await self._redis.get(key)
            return int(count) if count else 0
        return self._local_cache.get(key, 0)

    async def increment_daily_trades(self, user_id: int):
        """زيادة عدد الصفقات اليومية"""
        key = f"trades:daily:{user_id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        if self._redis:
            await self._redis.incr(key)
            await self._redis.expire(key, 86400)  # 24 ساعة
        else:
            self._local_cache[key] = self._local_cache.get(key, 0) + 1

    async def get_weekly_trades(self, user_id: int) -> int:
        """عدد الصفقات الأسبوعية"""
        now = datetime.now(timezone.utc)
        week_key = now.strftime('%Y%W')
        key = f"trades:weekly:{user_id}:{week_key}"
        if self._redis:
            count = await self._redis.get(key)
            return int(count) if count else 0
        return self._local_cache.get(key, 0)

    async def increment_weekly_trades(self, user_id: int):
        """زيادة عدد الصفقات الأسبوعية"""
        now = datetime.now(timezone.utc)
        week_key = now.strftime('%Y%W')
        key = f"trades:weekly:{user_id}:{week_key}"
        if self._redis:
            await self._redis.incr(key)
            await self._redis.expire(key, 604800)  # 7 أيام
        else:
            self._local_cache[key] = self._local_cache.get(key, 0) + 1

    async def get_monthly_trades(self, user_id: int) -> int:
        """عدد الصفقات الشهرية"""
        key = f"trades:monthly:{user_id}:{datetime.now(timezone.utc).strftime('%Y%m')}"
        if self._redis:
            count = await self._redis.get(key)
            return int(count) if count else 0
        return self._local_cache.get(key, 0)

    async def increment_monthly_trades(self, user_id: int):
        """زيادة عدد الصفقات الشهرية"""
        key = f"trades:monthly:{user_id}:{datetime.now(timezone.utc).strftime('%Y%m')}"
        if self._redis:
            await self._redis.incr(key)
            await self._redis.expire(key, 2592000)  # 30 يوم
        else:
            self._local_cache[key] = self._local_cache.get(key, 0) + 1

    # === Exposure Tracking ===

    async def get_open_exposure(self, user_id: int) -> float:
        """التعرض المفتوح (مجموع قيم الصفقات المفتوحة)"""
        key = f"exposure:open:{user_id}"
        if self._redis:
            val = await self._redis.get(key)
            return float(val) if val else 0.0
        return self._local_cache.get(key, 0.0)

    async def add_exposure(self, user_id: int, amount: float):
        """إضافة تعرض"""
        key = f"exposure:open:{user_id}"
        if self._redis:
            await self._redis.incrbyfloat(key, amount)
        else:
            self._local_cache[key] = self._local_cache.get(key, 0.0) + amount

    async def remove_exposure(self, user_id: int, amount: float):
        """إزالة تعرض"""
        key = f"exposure:open:{user_id}"
        if self._redis:
            await self._redis.decrbyfloat(key, amount)
        else:
            self._local_cache[key] = max(0, self._local_cache.get(key, 0.0) - amount)

    # === Weekly/Monthly Exposure ===

    async def get_weekly_exposure(self, user_id: int) -> float:
        """التعرض الأسبوعي"""
        now = datetime.now(timezone.utc)
        week_key = now.strftime('%Y%W')
        key = f"exposure:weekly:{user_id}:{week_key}"
        if self._redis:
            val = await self._redis.get(key)
            return float(val) if val else 0.0
        return self._local_cache.get(key, 0.0)

    async def add_weekly_exposure(self, user_id: int, amount: float):
        """إضافة تعرض أسبوعي"""
        now = datetime.now(timezone.utc)
        week_key = now.strftime('%Y%W')
        key = f"exposure:weekly:{user_id}:{week_key}"
        if self._redis:
            await self._redis.incrbyfloat(key, amount)
            await self._redis.expire(key, 604800)
        else:
            self._local_cache[key] = self._local_cache.get(key, 0.0) + amount

    async def get_monthly_exposure(self, user_id: int) -> float:
        """التعرض الشهري"""
        key = f"exposure:monthly:{user_id}:{datetime.now(timezone.utc).strftime('%Y%m')}"
        if self._redis:
            val = await self._redis.get(key)
            return float(val) if val else 0.0
        return self._local_cache.get(key, 0.0)

    async def add_monthly_exposure(self, user_id: int, amount: float):
        """إضافة تعرض شهري"""
        key = f"exposure:monthly:{user_id}:{datetime.now(timezone.utc).strftime('%Y%m')}"
        if self._redis:
            await self._redis.incrbyfloat(key, amount)
            await self._redis.expire(key, 2592000)
        else:
            self._local_cache[key] = self._local_cache.get(key, 0.0) + amount

    # === Limit Checks ===

    async def can_open_trade(self, user_id: int, amount: float, portfolio_value: float) -> Tuple[bool, str]:
        """
        التحقق من إمكانية فتح صفقة
        """
        tier = self.get_tier(user_id)
        config = TIERS.get(tier, TIERS["free"])

        # التحقق من الصفقات المفتوحة (لا صفقات جديدة إذا هناك صفقات مفتوحة — للمجاني)
        if tier == "free":
            open_count = await self.get_daily_trades(user_id)  # تقريبي
            # TODO: تحقق فعلي من عدد الصفقات المفتوحة من DB

        # التحقق من الحد اليومي
        daily_count = await self.get_daily_trades(user_id)
        if daily_count >= config.get("daily_trades", 999999):
            return False, f"❌ وصلت للحد اليومي ({config['daily_trades']} صفقات)"

        # التحقق من التعرض
        open_exposure = await self.get_open_exposure(user_id)
        new_exposure = open_exposure + amount
        max_pct = config.get("max_exposure_pct", 1.0)

        if tier == "diamond":
            # للماسي: فحص يومي/أسبوعي/شهري
            max_daily = config.get("max_daily_exposure_pct", 0.30)
            if new_exposure / portfolio_value > max_daily:
                return False, f"❌ التعرض اليومي وصل {max_daily*100:.0f}%"
        else:
            if new_exposure / portfolio_value > max_pct:
                return False, f"❌ التعرض المفتوح وصل {max_pct*100:.0f}%"

        return True, ""

    # === Approvals ===

    async def create_approval(self, user_id: int, plan_type: str, plan_data: dict) -> str:
        """إنشاء طلب موافقة"""
        approval_id = f"appr:{user_id}:{datetime.now(timezone.utc).timestamp()}"
        expires = datetime.now(timezone.utc) + timedelta(hours=24)

        data = {
            "plan_type": plan_type,
            "plan_data": plan_data,
            "status": "pending",
            "expires_at": expires.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self._redis:
            await self._redis.setex(approval_id, 86400, json.dumps(data))
        else:
            self._local_cache[approval_id] = data

        return approval_id

    async def get_approval(self, approval_id: str) -> Optional[dict]:
        """الحصول على طلب موافقة"""
        if self._redis:
            data = await self._redis.get(approval_id)
            return json.loads(data) if data else None
        return self._local_cache.get(approval_id)

    async def approve_plan(self, approval_id: str):
        """الموافقة على خطة"""
        if self._redis:
            data = await self._redis.get(approval_id)
            if data:
                parsed = json.loads(data)
                parsed["status"] = "approved"
                parsed["responded_at"] = datetime.now(timezone.utc).isoformat()
                await self._redis.setex(approval_id, 86400, json.dumps(parsed))
        else:
            if approval_id in self._local_cache:
                self._local_cache[approval_id]["status"] = "approved"
                self._local_cache[approval_id]["responded_at"] = datetime.now(timezone.utc).isoformat()

    # === Virtual Wallet Reset ===

    async def can_reset_wallet(self, user_id: int) -> Tuple[bool, str]:
        """التحقق من إمكانية إعادة ضبط المحفظة"""
        key = f"wallet:last_reset:{user_id}"

        if self._redis:
            last_reset = await self._redis.get(key)
        else:
            last_reset = self._local_cache.get(key)

        if last_reset:
            last_date = datetime.fromisoformat(last_reset)
            now = datetime.now(timezone.utc)
            days_since = (now - last_date).days
            if days_since < 30:
                remaining = 30 - days_since
                return False, f"❌ يمكنك إعادة الضبط بعد {remaining} يوم"

        return True, ""

    async def record_reset(self, user_id: int):
        """تسجيل إعادة الضبط"""
        key = f"wallet:last_reset:{user_id}"
        now = datetime.now(timezone.utc).isoformat()
        if self._redis:
            await self._redis.set(key, now)
        else:
            self._local_cache[key] = now


# Singleton
state_manager = StateManager()
