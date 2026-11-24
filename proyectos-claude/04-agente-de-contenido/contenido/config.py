"""Configuración del agente de contenido (.env + marca.md)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


MODEL = _get("CONTENIDO_MODEL", "claude-opus-5-5")
NICHO = _get("NICHO", "inteligencia artificial para emprendedores")
COMPETIDORES = [c.strip() for c in _get("COMPETIDORES", "").split(",") if c.strip()]
PLATAFORMA = _get("PLATAFORMA", "TikTok e Instagram Reels")
IDIOMA = _get("IDIOMA", "español de España")
PAIS = _get("PAIS", "ES")
NUM_GUIONES = int(_get("NUM_GUIONES", "3") or 3)
HORA = _get("HORA", "03:00")  # a qué hora trabaja cada noche
TIMEZONE = _get("TIMEZONE", "Europe/Madrid")
NOTIFY_WEBHOOK = _get("NOTIFY_WEBHOOK")  # opcional: webhook de Slack/Discord para avisarte al terminar
WEB_TOKEN = _get("CONTENIDO_WEB_TOKEN")

MARCA_FILE = ROOT / "marca.md"
OUT = Path(_get("SALIDAS", str(ROOT / "salidas")))


def marca() -> str:
    return MARCA_FILE.read_text(encoding="utf-8") if MARCA_FILE.exists() else ""
