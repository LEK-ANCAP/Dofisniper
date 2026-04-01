from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # DofiMall
    dofimall_email: str = ""
    dofimall_password: str = ""
    dofimall_base_url: str = "https://www.dofimall.com"

    # Scheduler
    check_interval_minutes: int = 5

    # Browser
    headless: bool = True

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_email: str = ""

    # WhatsApp
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_to: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # App
    secret_key: str = "dev-secret-key"
    database_url: str = "sqlite+aiosqlite:///./dofimall_sniper.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
