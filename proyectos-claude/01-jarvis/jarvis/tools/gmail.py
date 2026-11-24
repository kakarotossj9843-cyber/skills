"""Correo (Gmail). Si Google no está configurado, funciona en modo DEMO con datos de ejemplo."""
from __future__ import annotations

import base64
import json
from email.mime.text import MIMEText

from anthropic import beta_tool

from .. import config

DEMO_EMAILS = [
    {"id": "demo1", "from": "Marta López <marta@cliente.com>", "subject": "¿Me mandas el presupuesto?",
     "date": "hoy 09:12", "snippet": "Hola, ¿podrías enviarme el presupuesto antes del viernes? Gracias."},
    {"id": "demo2", "from": "Banco <avisos@banco.es>", "subject": "Recibo domiciliado",
     "date": "hoy 07:40", "snippet": "Se ha cargado un recibo de 49,90 € en tu cuenta."},
    {"id": "demo3", "from": "Carlos <carlos@socio.com>", "subject": "Reunión del jueves",
     "date": "ayer 18:03", "snippet": "¿Movemos la reunión del jueves a las 12:00?"},
]


def _demo() -> bool:
    return not config.google_configured()


def _gmail():
    from .google_auth import service

    return service("gmail", "v1")


def _header(headers: list[dict], name: str) -> str:
    return next((h["value"] for h in headers if h["name"].lower() == name.lower()), "")


def _body(payload: dict) -> str:
    if payload.get("mimeType", "").startswith("text/plain") and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        text = _body(part)
        if text:
            return text
    return ""


def fetch_unread(max_results: int = 10) -> list[dict]:
    """Uso interno (también lo usa el vigilante de bandeja)."""
    if _demo():
        return DEMO_EMAILS[:max_results]
    gm = _gmail()
    res = gm.users().messages().list(userId="me", q="is:unread in:inbox", maxResults=max_results).execute()
    out = []
    for m in res.get("messages", []):
        msg = gm.users().messages().get(
            userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        h = msg["payload"]["headers"]
        out.append({"id": m["id"], "from": _header(h, "From"), "subject": _header(h, "Subject"),
                    "date": _header(h, "Date"), "snippet": msg.get("snippet", "")})
    return out


@beta_tool
def list_unread_emails(max_results: int = 10) -> str:
    """Lista los correos no leídos de la bandeja de entrada (remitente, asunto, fecha y extracto).

    Args:
        max_results: Número máximo de correos a devolver (1-25).
    """
    emails = fetch_unread(max(1, min(max_results, 25)))
    return json.dumps({"demo": _demo(), "emails": emails}, ensure_ascii=False)


@beta_tool
def search_emails(query: str, max_results: int = 10) -> str:
    """Busca correos con la sintaxis de búsqueda de Gmail (ej. 'from:marta presupuesto', 'newer_than:7d').

    Args:
        query: Consulta de búsqueda de Gmail.
        max_results: Número máximo de resultados (1-25).
    """
    if _demo():
        q = query.lower()
        hits = [e for e in DEMO_EMAILS if any(w in json.dumps(e, ensure_ascii=False).lower() for w in q.split())]
        return json.dumps({"demo": True, "emails": hits}, ensure_ascii=False)
    gm = _gmail()
    res = gm.users().messages().list(userId="me", q=query, maxResults=max(1, min(max_results, 25))).execute()
    out = []
    for m in res.get("messages", []):
        msg = gm.users().messages().get(
            userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        h = msg["payload"]["headers"]
        out.append({"id": m["id"], "from": _header(h, "From"), "subject": _header(h, "Subject"),
                    "date": _header(h, "Date"), "snippet": msg.get("snippet", "")})
    return json.dumps({"demo": False, "emails": out}, ensure_ascii=False)


@beta_tool
def read_email(email_id: str) -> str:
    """Lee el contenido completo de un correo por su id.

    Args:
        email_id: Id del correo (obtenido de list_unread_emails o search_emails).
    """
    if _demo():
        e = next((e for e in DEMO_EMAILS if e["id"] == email_id), None)
        return json.dumps(e or {"error": "no encontrado"}, ensure_ascii=False)
    msg = _gmail().users().messages().get(userId="me", id=email_id, format="full").execute()
    h = msg["payload"]["headers"]
    return json.dumps({
        "id": email_id, "thread_id": msg.get("threadId"), "from": _header(h, "From"),
        "to": _header(h, "To"), "subject": _header(h, "Subject"), "date": _header(h, "Date"),
        "body": _body(msg["payload"])[:8000],
    }, ensure_ascii=False)


def _raw(to: str, subject: str, body: str) -> str:
    mime = MIMEText(body, "plain", "utf-8")
    mime["to"], mime["subject"] = to, subject
    return base64.urlsafe_b64encode(mime.as_bytes()).decode()


@beta_tool
def create_email_draft(to: str, subject: str, body: str) -> str:
    """Crea un BORRADOR de correo en Gmail (no lo envía). Opción por defecto para responder correos.

    Args:
        to: Dirección del destinatario.
        subject: Asunto.
        body: Texto del correo.
    """
    if _demo():
        return f"(DEMO) Borrador creado para {to}: «{subject}»"
    d = _gmail().users().drafts().create(userId="me", body={"message": {"raw": _raw(to, subject, body)}}).execute()
    return f"Borrador creado (id {d['id']}) para {to}: «{subject}». Revísalo en Gmail."


@beta_tool
def send_email(to: str, subject: str, body: str) -> str:
    """ENVÍA un correo. Úsalo solo si el usuario ha pedido explícitamente enviarlo (no solo redactarlo).

    Args:
        to: Dirección del destinatario.
        subject: Asunto.
        body: Texto del correo.
    """
    if not config.ALLOW_SEND_EMAIL:
        return ("Envío directo desactivado (ALLOW_SEND_EMAIL=false). Crea un borrador con "
                "create_email_draft y avisa al usuario de que lo revise.")
    if _demo():
        return f"(DEMO) Correo enviado a {to}: «{subject}»"
    _gmail().users().messages().send(userId="me", body={"raw": _raw(to, subject, body)}).execute()
    return f"Correo enviado a {to}: «{subject}»"


@beta_tool
def mark_email_read(email_id: str) -> str:
    """Marca un correo como leído.

    Args:
        email_id: Id del correo.
    """
    if _demo():
        return f"(DEMO) {email_id} marcado como leído"
    _gmail().users().messages().modify(userId="me", id=email_id, body={"removeLabelIds": ["UNREAD"]}).execute()
    return f"{email_id} marcado como leído"


TOOLS = [list_unread_emails, search_emails, read_email, create_email_draft, send_email, mark_email_read]
