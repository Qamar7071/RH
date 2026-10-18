"""Settings, read from environment variables (or a .env file next to this file)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    def __init__(self) -> None:
        g = os.getenv
        # Company
        self.COMPANY_NAME = g("COMPANY_NAME") or "RH Labs"
        self.CONTACT_WHATSAPP = g("CONTACT_WHATSAPP", "")
        self.CONTACT_EMAIL = g("CONTACT_EMAIL", "")

        # Database: SQLite by default, Postgres in production (DATABASE_URL=postgresql://...)
        self.DATABASE_URL = (g("DATABASE_URL") or "").strip() or f"sqlite:///{BASE_DIR / 'rh_labs.db'}"

        # Which websites may call the API (comma separated). Empty = same site only.
        self.ALLOWED_ORIGINS = [o.strip() for o in g("ALLOWED_ORIGINS", "").split(",") if o.strip()]
        self.TRUST_PROXY = _bool("TRUST_PROXY", True)

        # AI chatbot
        self.LLM_PROVIDER = (g("LLM_PROVIDER") or "gemini").strip().lower()
        self.LLM_API_KEY = g("LLM_API_KEY", "").strip()
        self.LLM_MODEL = g("LLM_MODEL", "").strip()
        self.LLM_BASE_URL = g("LLM_BASE_URL", "").strip()
        self.LLM_TIMEOUT = _int("LLM_TIMEOUT", 15)
        self.LLM_MAX_TOKENS = _int("LLM_MAX_TOKENS", 600)

        # Email alerts (Gmail: smtp.gmail.com + an App Password)
        self.SMTP_HOST = g("SMTP_HOST", "smtp.gmail.com")
        self.SMTP_PORT = _int("SMTP_PORT", 587)
        self.SMTP_USER = g("SMTP_USER", "").strip()
        self.SMTP_PASSWORD = g("SMTP_PASSWORD", "").replace(" ", "")
        self.NOTIFY_EMAIL = g("NOTIFY_EMAIL", "").strip()
        self.SEND_AUTO_REPLY = _bool("SEND_AUTO_REPLY", False)

        # Admin panel (/admin). Disabled until ADMIN_PASSWORD is set.
        self.ADMIN_USER = g("ADMIN_USER", "admin")
        self.ADMIN_PASSWORD = g("ADMIN_PASSWORD", "")

        # Rate limits (per visitor IP)
        self.RATE_LIMIT_STORAGE = g("RATE_LIMIT_STORAGE", "memory://")
        self.CONTACT_RATE_LIMIT = g("CONTACT_RATE_LIMIT", "5 per minute;30 per hour")
        self.CHAT_RATE_LIMIT = g("CHAT_RATE_LIMIT", "20 per minute;300 per day")