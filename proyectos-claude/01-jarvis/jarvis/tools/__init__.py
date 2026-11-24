from anthropic import beta_tool

from .. import memory
from . import calendar, gmail, notion, whatsapp


@beta_tool
def remember(note: str) -> str:
    """Guarda en la memoria permanente un dato importante sobre el usuario (preferencias, personas, rutinas).

    Args:
        note: El dato a recordar, en una frase.
    """
    memory.add_note(note)
    return "Guardado en memoria"


ALL_TOOLS = [*gmail.TOOLS, *calendar.TOOLS, *notion.TOOLS, *whatsapp.TOOLS, remember]
