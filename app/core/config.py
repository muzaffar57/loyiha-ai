"""Loyihaning barcha sozlamalari shu yerda joylashgan.

Barcha qiymatlar `.env` faylidan o'qiladi. Hech qanday maxfiy ma'lumot
(parol, token, kalit) to'g'ridan-to'g'ri kodga yozilmaydi.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Umumiy
    APP_NAME: str = "Yuk Tashish Platformasi (MVP)"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # Ma'lumotlar bazasi
    DATABASE_URL: str = "postgresql+asyncpg://logistics_user:logistics_pass_dev@localhost:5432/logistics_db"

    # Xavfsizlik / JWT
    SECRET_KEY: str = "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 kun

    # Telegram integratsiyasi
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHANNEL_ID: str = ""

    # Faqat lokal (development) muhitda WebApp'ni Telegram'siz sinash uchun.
    # Production'da bu albatta False bo'lishi kerak -- aks holda hech qanday
    # tekshiruvsiz istalgan foydalanuvchi nomidan kirish mumkin bo'lib qoladi.
    TELEGRAM_MOCK_AUTH_ENABLED: bool = False

    # Fayllar (rasm) uchun
    MEDIA_ROOT: str = "media"
    MAX_PHOTO_SIZE_MB: int = 5
    MAX_PHOTOS_PER_CARGO: int = 5

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = ["*"]

    # PenodecorPro narx jadvali. Qiymatlar bo‘sh bo‘lsa, hisoblash bazadagi
    # asl narxdan davom etadi va Google Sheets chaqirilmaydi.
    STORE_SHEETS_SPREADSHEET_ID: str = ""
    STORE_SHEETS_CREDENTIALS_FILE: str = ""
    STORE_SHEETS_SYNC_TOKEN: str = ""
    STORE_SHEETS_SYNC_INTERVAL_SECONDS: int = 0
    STORE_SHEETS_STALE_AFTER_SECONDS: int = 86_400

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Railway/Heroku kabi platformalar odatda `postgres://` yoki
        `postgresql://` formatida beradi, lekin bizga async ishlash uchun
        `postgresql+asyncpg://` kerak. Shuni avtomatik to'g'rilaymiz --
        deploy paytida qo'lda o'zgartirish kerak bo'lmaydi."""
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
