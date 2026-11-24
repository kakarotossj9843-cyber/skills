"""Ejecuta una vez para autorizar Gmail + Calendar:  python -m jarvis.setup_google"""
from . import config
from .tools.google_auth import get_credentials

if __name__ == "__main__":
    if not config.GOOGLE_CREDENTIALS_FILE.exists():
        raise SystemExit(
            f"Falta {config.GOOGLE_CREDENTIALS_FILE.name}. Descárgalo de Google Cloud Console "
            "(OAuth client ID tipo 'Desktop app') y ponlo en la carpeta del proyecto."
        )
    get_credentials(interactive=True)
    print(f"✅ Google autorizado. Token guardado en {config.GOOGLE_TOKEN_FILE}")
