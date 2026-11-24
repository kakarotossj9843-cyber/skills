"""Autenticación OAuth de Google compartida por Gmail y Calendar."""
from __future__ import annotations

from functools import lru_cache

from .. import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]


def get_credentials(interactive: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if config.GOOGLE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(config.GOOGLE_TOKEN_FILE), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif interactive:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(str(config.GOOGLE_CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
    else:
        raise RuntimeError("Google no autorizado. Ejecuta: python -m jarvis.setup_google")
    config.GOOGLE_TOKEN_FILE.write_text(creds.to_json())
    return creds


@lru_cache(maxsize=None)
def service(name: str, version: str):
    from googleapiclient.discovery import build

    return build(name, version, credentials=get_credentials(), cache_discovery=False)
