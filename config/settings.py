"""
⚙️ الفهد — إعدادات النظام
Pydantic Settings v2 — مع قيم افتراضية للمرونة
Bitget Skill: write-safety, demo mode, retry config
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
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
    VAULT_SALT: str = Field(default="alfahd-salt-v1")  # Bitget Skill: salt for PBKDF2

    # === AI ===
    HF_API_TOKEN: Optional[str] = Field(default=None)
    COINGECKO_API_KEY: Optional[str] = Field(default=None)

    # === Exchange (Bitget Skill: demo/paper trading) ===
    DEFAULT_EXCHANGE: str = Field(default="okx")
    PAPER_TRADING: bool = Field(default=True)  # Demo mode by default
    DEMO_API_KEY: Optional[str] = Field(default=None)
    DEMO_SECRET_KEY: Optional[str] = Field(default=None)
    DEMO_PASSPHRASE: Optional[str] = Field(default=None)

    # === Rate Limiting ===
    COINGECKO_RATE_LIMIT: int = Field(default=10)  # calls per minute
    CCXT_RATE_LIMIT: int = Field(default=20)       # calls per minute

    # === Retry ===
    MAX_RETRIES: int = Field(default=3)
    RETRY_DELAY: float = Field(default=1.0)

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

    @model_validator(mode="after")
    def check_master_key(self):
        if not self.MASTER_KEY and self.RAILWAY_ENVIRONMENT.lower() == "production":
            raise ValueError("MASTER_KEY is required in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.RAILWAY_ENVIRONMENT.lower() == "production"

    def is_admin(self, user_id: int) -> bool:
        return user_id == self.ADMIN_ID

    def is_moderator(self, user_id: int) -> bool:
        return user_id == self.ADMIN_ID or user_id in self.MODERATOR_IDS

# Singleton
settings = Settings()
