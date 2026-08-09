"""
⚙️ الفهد — إعدادات النظام
Pydantic Settings v2 — مع قيم افتراضية للمرونة
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # === Telegram ===
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    ADMIN_ID: int = Field(default=0)
    MODERATOR_IDS: List[int] = Field(default_factory=list)

    # === Database ===
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./alfahd.db")
    REDIS_URL: str = Field(default="")

    # === Security ===
    MASTER_KEY: str = Field(default="")

    # === AI ===
    HF_API_TOKEN: Optional[str] = Field(default=None)
    COINGECKO_API_KEY: Optional[str] = Field(default=None)

    # === Railway ===
    RAILWAY_ENVIRONMENT: str = Field(default="development")
    PORT: int = Field(default=8080)

    # === Logging ===
    LOG_LEVEL: str = Field(default="INFO")

    @field_validator("MODERATOR_IDS", mode="before")
    @classmethod
    def parse_mod_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        return v or []

    @property
    def is_production(self) -> bool:
        return self.RAILWAY_ENVIRONMENT.lower() == "production"

    def is_admin(self, user_id: int) -> bool:
        return user_id == self.ADMIN_ID

    def is_moderator(self, user_id: int) -> bool:
        return user_id == self.ADMIN_ID or user_id in self.MODERATOR_IDS


# Singleton
settings = Settings()
