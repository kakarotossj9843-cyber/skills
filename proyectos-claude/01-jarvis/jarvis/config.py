"""Configuración de Jarvis: todo se lee de variables de entorno / archivo .env."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# --- Claude ---
MODEL = _get("JARVIS_MODEL", "claude-opus-5-5")
EFFORT = _get("JARVIS_EFFORT", "medium")  # low | medium | high | xhigh | max

# --- Identidad ---
OWNER_NAME = _get("OWNER_NAME", "jefe")
TIMEZONE = _get("TIMEZONE", "Europe/Madrid")
LANGUAGE = _get("JARVIS_LANGUAGE", "español")

# --- Google (Gmail + Calendar) ---
GOOGLE_CREDENTIALS_FILE = ROOT / _get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_TOKEN_FILE = ROOT / _get("GOOGLE_TOKEN_FILE", "token.json")
GOOGLE_CALENDAR_ID = _get("GOOGLE_CALENDAR_ID", "primary")

# --- Notion ---
NOTION_TOKEN = _get("NOTION_TOKEN")
NOTION_TASKS_DB_ID = _get("NOTION_TASKS_DB_ID")
NOTION_TITLE_PROPERTY = _get("NOTION_TITLE_PROPERTY", "Name")
NOTION_STATUS_PROPERTY = _get("NOTION_STATUS_PROPERTY", "")  # opcional, tipo "status" o "checkbox"

# --- WhatsApp (Twilio) ---
TWILIO_ACCOUNT_SID = _get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = _get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = _get("TWILIO_WHATSAPP_FROM")  # ej. whatsapp:+14155238886
OWNER_WHATSAPP = _get("OWNER_WHATSAPP")  # ej. whatsapp:+34600111222
PUBLIC_BASE_URL = _get("PUBLIC_BASE_URL")  # URL pública del servidor (para validar firma Twilio)

# --- Servidor / 24h ---
WEB_TOKEN = _get("JARVIS_WEB_TOKEN")  # protege el chat web; vacío = solo localhost
BRIEF_TIME = _get("BRIEF_TIME", "08:00")  # resumen diario por WhatsApp
INBOX_CHECK_MINUTES = int(_get("INBOX_CHECK_MINUTES", "30") or 0)
ALLOW_SEND_EMAIL = _get("ALLOW_SEND_EMAIL", "false").lower() == "true"

DB_FILE = ROOT / _get("JARVIS_DB", "jarvis.db")


def google_configured() -> bool:
    return GOOGLE_TOKEN_FILE.exists() or GOOGLE_CREDENTIALS_FILE.exists()


def notion_configured() -> bool:
    return bool(NOTION_TOKEN and NOTION_TASKS_DB_ID)


def whatsapp_configured() -> bool:
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM and OWNER_WHATSAPP)


def status() -> dict[str, bool]:
    return {
        "claude": bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")),
        "gmail": google_configured(),
        "calendar": google_configured(),
        "notion": notion_configured(),
        "whatsapp": whatsapp_configured(),
    }
