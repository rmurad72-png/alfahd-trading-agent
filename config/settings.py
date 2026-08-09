"""
⚙️ الفهد — إعدادات النظام
Pydantic Settings v2 — validation + type safety
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # === Telegram ===
    TELEGRAM_BOT_TOKEN: str = Field(..., min_length=20)
    ADMIN_ID: int = Field(..., gt=0)
    MODERATOR_IDS: List[int] = Field(default_factory=list)

    # === Database ===
    DATABASE_URL: str = Field(..., pattern=r"^postgresql\+asyncpg://")
    REDIS_URL: str = Field(default="redis://localhost:6379")

    # === Security ===
    MASTER_KEY: str = Field(..., min_length=32)

    # === AI ===
    HF_API_TOKEN: Optional[str] = Field(default=None)
    COINGECKO_API_KEY: Optional[str] = Field(default=None)

    # === Railway ===
    RAILWAY_ENVIRONMENT: str = Field(default="development")
    PORT: int = Field(default=8080, ge=1000, le=65535)

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

    @property
    def is_admin(self, user_id: int) -> bool:
        return user_id == self.ADMIN_ID

    @property
    def is_moderator(self, user_id: int) -> bool:
        return user_id == self.ADMIN_ID or user_id in self.MODERATOR_IDS


# Singleton
settings = Settings()
