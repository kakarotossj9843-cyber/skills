"""El cerebro de Jarvis: Claude + herramientas (correo, calendario, Notion, WhatsApp, memoria)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from . import config, memory
from .tools import ALL_TOOLS

client = anthropic.Anthropic()

SYSTEM_PROMPT = f"""Eres Jarvis, el asistente personal de {config.OWNER_NAME}. Trabajas 24 horas para \
resolverle el día a día: correo (Gmail), calendario (Google Calendar), tareas (Notion) y avisos por WhatsApp.

Cómo trabajas:
- Responde siempre en {config.LANGUAGE}, breve y directo, como un buen asistente ejecutivo. Tus respuestas \
suelen leerse en WhatsApp: frases cortas, listas con guiones, sin tablas ni markdown pesado.
- Usa las herramientas para consultar datos reales en vez de suponer. Si una herramienta devuelve "demo": true, \
avisa una sola vez de que esa integración está en modo demostración.
- Para contestar correos crea BORRADORES con create_email_draft. Usa send_email solo si {config.OWNER_NAME} \
ha dicho explícitamente "envíalo".
- Antes de borrar eventos o hacer algo irreversible, pide confirmación.
- Cuando {config.OWNER_NAME} te cuente algo útil para el futuro (personas, preferencias, rutinas), guárdalo \
con remember.
- Si detectas algo que requiere acción (un correo urgente, un hueco que choca en la agenda), propónlo \
proactivamente."""


def _context() -> str:
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    notes = memory.notes()
    ctx = f"Fecha y hora actual: {now.strftime('%A %d/%m/%Y %H:%M')} ({config.TIMEZONE})."
    if notes:
        ctx += "\nLo que recuerdas del usuario:\n" + "\n".join(f"- {n}" for n in notes[-50:])
    return ctx


def ask(text: str, chat: str = "default", save: bool = True) -> str:
    """Envía un mensaje a Jarvis y devuelve su respuesta final en texto."""
    messages = [*memory.history(chat), {"role": "user", "content": f"<contexto>{_context()}</contexto>\n\n{text}"}]

    runner = client.beta.messages.tool_runner(
        model=config.MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        output_config={"effort": config.EFFORT},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        tools=ALL_TOOLS,
        messages=messages,
        max_iterations=25,
    )
    final = runner.until_done()

    if final.stop_reason == "refusal":
        reply = "Lo siento, no puedo ayudar con esa petición."
    else:
        reply = "\n".join(b.text for b in final.content if b.type == "text").strip() or "Hecho."

    if save:
        memory.add_message(chat, "user", text)
        memory.add_message(chat, "assistant", reply)
    return reply
