"""Herramientas que Claude usa para leer y escribir en tu segundo cerebro."""
from __future__ import annotations

import json

from anthropic import beta_tool

from . import vault


@beta_tool
def list_notes() -> str:
    """Lista todas las notas del vault (rutas relativas). Úsalo para orientarte o elegir dónde archivar."""
    return vault.tree()


@beta_tool
def search_notes(query: str) -> str:
    """Busca notas por palabras clave y devuelve rutas con un fragmento. Haz varias búsquedas con sinónimos si hace falta.

    Args:
        query: Palabras clave a buscar.
    """
    return json.dumps(vault.search(query), ensure_ascii=False)


@beta_tool
def read_note(path: str) -> str:
    """Lee una nota completa.

    Args:
        path: Ruta relativa (ej. '20-Negocio/Clientes/Marta.md') o solo el título de la nota.
    """
    try:
        return vault.read(path)
    except FileNotFoundError:
        return f"No existe la nota {path}"


@beta_tool
def create_note(path: str, content: str) -> str:
    """Crea una nota NUEVA en Markdown. Enlaza conceptos relacionados con [[Título]] y añade #etiquetas.

    Args:
        path: Ruta relativa dentro del área adecuada, ej. '30-Areas/Salud/Rutina de gimnasio.md'.
        content: Contenido Markdown completo, empezando por '# Título'.
    """
    try:
        return "Creada: " + vault.write(path, content)
    except FileExistsError as e:
        return f"Ya existe {e}. Usa append_to_note para añadir información."
    except ValueError as e:
        return f"Error: {e}"


@beta_tool
def append_to_note(path: str, content: str) -> str:
    """Añade información nueva al final de una nota existente (con fecha). Si no existe, la crea.

    Args:
        path: Ruta relativa de la nota.
        content: Texto Markdown a añadir.
    """
    try:
        return "Actualizada: " + vault.append(path, content)
    except ValueError as e:
        return f"Error: {e}"


@beta_tool
def rewrite_note(path: str, content: str) -> str:
    """Reescribe por completo una nota existente (para reorganizarla o corregirla). Conserva la información valiosa.

    Args:
        path: Ruta relativa de la nota.
        content: Nuevo contenido Markdown completo.
    """
    try:
        return "Reescrita: " + vault.write(path, content, overwrite=True)
    except ValueError as e:
        return f"Error: {e}"


@beta_tool
def update_profile(content: str) -> str:
    """Reescribe PERFIL.md: el resumen de quién es el usuario que lees en cada conversación.
    Mantenlo conciso (máx. ~80 líneas): identidad, objetivos, negocio, personas clave, preferencias, cómo quiere que le hables.

    Args:
        content: Nuevo contenido completo de PERFIL.md.
    """
    return "Perfil actualizado: " + vault.write(vault.PROFILE, content, overwrite=True)


ALL_TOOLS = [list_notes, search_notes, read_note, create_note, append_to_note, rewrite_note, update_profile]
