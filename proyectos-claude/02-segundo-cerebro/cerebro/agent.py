"""Claude conectado a tu segundo cerebro: pregunta, captura y organiza."""
from __future__ import annotations

import os
from datetime import date

import anthropic

from . import vault
from .tools import ALL_TOOLS

MODEL = os.getenv("CEREBRO_MODEL", "claude-opus-5-5")
EFFORT = os.getenv("CEREBRO_EFFORT", "medium")
client = anthropic.Anthropic()

INSTRUCTIONS = """Eres el segundo cerebro del usuario: una biblioteca infinita de contexto sobre su vida, su \
negocio y sus áreas personales, guardada como notas Markdown (estilo Obsidian) en un vault.

Estructura del vault:
- 00-Bandeja/  material sin procesar
- 10-Vida/     personas, familia, recuerdos, objetivos vitales, diario
- 20-Negocio/  empresa, clientes, productos, ideas, procesos, métricas
- 30-Areas/    Salud, Finanzas, Relaciones, Aprendizaje (y las que hagan falta)
- PERFIL.md    resumen de quién es el usuario (ya lo tienes abajo)

Reglas:
- Responde en español, claro y directo. Para responder, BUSCA y LEE notas antes de contestar; cita las notas \
que usas con [[Título]]. Si no hay información, dilo y pregunta.
- Cuando el usuario te cuente algo nuevo y duradero, guárdalo sin que te lo pida: en la nota existente si la hay \
(append_to_note) o en una nueva bien ubicada (create_note). Una idea por nota, títulos claros, enlaces [[...]] \
entre personas, proyectos y temas, y #etiquetas.
- Si aprendes algo importante sobre quién es (objetivos, negocio, personas clave, preferencias), actualiza \
PERFIL.md con update_profile manteniéndolo breve.
- Nunca borres información valiosa. No inventes datos."""


def _system() -> list[dict]:
    profile = vault.profile() or "(PERFIL.md vacío: aún no conoces al usuario. Ve aprendiendo.)"
    return [
        {"type": "text", "text": INSTRUCTIONS},
        {"type": "text", "text": f"<perfil>\n{profile}\n</perfil>", "cache_control": {"type": "ephemeral"}},
    ]


def run(messages: list[dict]) -> str:
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=_system(),
        thinking={"type": "adaptive"},
        output_config={"effort": EFFORT},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        tools=ALL_TOOLS,
        messages=messages,
        max_iterations=40,
    )
    final = runner.until_done()
    if final.stop_reason == "refusal":
        return "No puedo ayudar con eso."
    return "\n".join(b.text for b in final.content if b.type == "text").strip() or "Hecho."


def ask(question: str, history: list[dict] | None = None) -> str:
    """Conversación normal: pregunta o cuéntale cosas."""
    msgs = list(history or [])
    msgs.append({"role": "user", "content": f"(Hoy es {date.today().isoformat()})\n\n{question}"})
    return run(msgs)


def capture(raw: str, source: str = "nota rápida") -> str:
    """Archiva texto en bruto (ideas, notas de voz transcritas, apuntes) en las notas adecuadas."""
    return run([{"role": "user", "content": (
        f"(Hoy es {date.today().isoformat()}) Procesa este material ({source}) y archívalo en mi segundo cerebro: "
        "revisa qué notas existen, divide el contenido por temas, crea o amplía las notas adecuadas con enlaces "
        "[[...]] y actualiza PERFIL.md si aprendes algo importante de mí. Al final dime en 3-6 líneas qué has "
        f"guardado y dónde.\n\n<material>\n{raw}\n</material>"
    )}])


def process_inbox() -> str:
    """Procesa todo lo que haya en 00-Bandeja y lo mueve a su sitio."""
    pending = [p for p in vault.all_notes() if vault.rel(p).startswith("00-Bandeja/") and p.name != "LEEME.md"]
    if not pending:
        return "La bandeja está vacía."
    out = []
    for p in pending:
        out.append(f"• {p.name}: " + capture(p.read_text(encoding="utf-8"), source=p.name))
        archive = vault.VAULT / ".procesadas" / p.name
        archive.parent.mkdir(exist_ok=True)
        p.rename(archive)
    return "\n".join(out)


def interview() -> str:
    """Primera vez: Claude te hace preguntas para construir tu perfil."""
    return ask("Aún no me conoces bien. Hazme UNA a UNA las preguntas clave (empieza solo por la primera) para "
               "crear mi perfil: quién soy, a qué me dedico, mis objetivos, personas importantes, rutinas y cómo "
               "quiero que me hables. Ve guardando cada respuesta.")
