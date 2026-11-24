"""WhatsApp vía Twilio. Jarvis solo puede escribir al número del dueño (OWNER_WHATSAPP)."""
from __future__ import annotations

from anthropic import beta_tool

from .. import config

MAX_LEN = 1500  # límite práctico por mensaje de WhatsApp en Twilio


def send_to_owner(text: str) -> str:
    if not config.whatsapp_configured():
        print(f"\n📱 (DEMO WhatsApp → {config.OWNER_NAME}): {text}\n")
        return "(DEMO) Mensaje mostrado en consola (WhatsApp no configurado)"
    from twilio.rest import Client

    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    chunks = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)] or [""]
    for chunk in chunks:
        client.messages.create(from_=config.TWILIO_WHATSAPP_FROM, to=config.OWNER_WHATSAPP, body=chunk)
    return "Mensaje de WhatsApp enviado"


@beta_tool
def send_whatsapp_to_owner(message: str) -> str:
    """Envía un mensaje de WhatsApp al dueño (avisos, recordatorios, resúmenes).

    Args:
        message: Texto del mensaje.
    """
    return send_to_owner(message)


TOOLS = [send_whatsapp_to_owner]
