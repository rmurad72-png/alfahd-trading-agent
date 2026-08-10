"""
⚙️ إعدادات الفهد
"""
import os
from typing import Set


class Settings:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    MASTER_KEY: str = os.getenv("MASTER_KEY", "")
    VAULT_SALT: str = os.getenv("VAULT_SALT", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///alfahd.db")
    PAPER_TRADING: bool = os.getenv("PAPER_TRADING", "true").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    _mods: str = os.getenv("MODERATOR_IDS", "")

    @property
    def MODERATOR_IDS(self) -> Set[int]:
        if not self._mods:
            return set()
        return {int(x.strip()) for x in self._mods.split(",") if x.strip().isdigit()}

    def is_moderator(self, user_id: int) -> bool:
        return user_id in self.MODERATOR_IDS


settings = Settings()
