"""El equipo: un jefe que planifica y delega, y cuatro subagentes especialistas.

Jefe ──┬── Busca    (investiga en internet)
       ├── Escribe  (redacta textos)
       ├── Diseña   (crea piezas visuales en HTML/SVG)
       └── Revisa   (control de calidad)
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, TypedDict

import anthropic
from anthropic import beta_tool

from .job import Job

MODEL_JEFE = os.getenv("EQUIPO_MODELO_JEFE", "claude-opus-5-5")
MODEL_SUB = os.getenv("EQUIPO_MODELO_SUBAGENTES", "claude-opus-5-5")
MAX_ROUNDS = int(os.getenv("EQUIPO_MAX_RONDAS", "6"))
client = anthropic.Anthropic()

COMMON = dict(betas=["server-side-fallback-2026-07-01"], fallbacks="default", thinking={"type": "adaptive"})

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 10},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 6, "max_content_tokens": 20000},
]

SUBAGENTS = {
    "busca": {
        "nombre": "Busca", "effort": "medium", "web": True,
        "system": ("Eres «Busca», el investigador del equipo. Buscas en internet información actual y fiable, contrastas "
                   "fuentes y nunca inventas. Guarda tu investigación en un archivo .md (con enlaces a las fuentes) con "
                   "guardar_archivo y termina con un resumen de 3-6 líneas de lo más importante y el nombre del archivo."),
    },
    "escribe": {
        "nombre": "Escribe", "effort": "medium", "web": False,
        "system": ("Eres «Escribe», el redactor del equipo. Escribes textos claros, persuasivos y sin relleno, en el idioma "
                   "y tono que pida el encargo. Lee primero los archivos que te indiquen (investigación, borradores, "
                   "correcciones). Guarda tu trabajo con guardar_archivo (.md) y termina diciendo qué archivo has creado "
                   "y en 2-3 líneas qué contiene."),
    },
    "disena": {
        "nombre": "Diseña", "effort": "medium", "web": False,
        "system": ("Eres «Diseña», el diseñador del equipo. Creas piezas visuales como archivos HTML autocontenidos "
                   "(CSS en <style>, sin JavaScript externo, sin imágenes externas: usa SVG inline, degradados y "
                   "tipografía del sistema). Diseño moderno, con jerarquía clara, buen contraste y que se vea bien en "
                   "móvil. Lee los textos que te indiquen y úsalos tal cual (no inventes otros). Guarda con "
                   "guardar_archivo (.html o .svg) y termina diciendo qué archivo has creado."),
    },
    "revisa": {
        "nombre": "Revisa", "effort": "medium", "web": False,
        "system": ("Eres «Revisa», el control de calidad del equipo. Lees los archivos que te indiquen y los compruebas "
                   "contra el encargo original: errores, datos sin fuente, faltas de ortografía, tono, claridad, que el "
                   "diseño use los textos correctos y sea legible. Responde SIEMPRE empezando por «VEREDICTO: APROBADO» o "
                   "«VEREDICTO: CAMBIOS», seguido de una lista corta y concreta de cambios necesarios (archivo y qué "
                   "cambiar). Sé exigente pero justo: no pidas cambios cosméticos menores."),
    },
}

JEFE_SYSTEM = """Eres «El jefe»: diriges un equipo de 4 subagentes para cumplir el encargo del usuario con calidad profesional.

Tu equipo:
- busca: investiga en internet (datos actuales, competencia, referencias) y guarda la investigación en .md
- escribe: redacta textos (copys, artículos, guiones, emails, landing) y los guarda en .md
- disena: crea piezas visuales como HTML/SVG autocontenido (landing, carrusel, infografía, post, presentación)
- revisa: control de calidad; responde VEREDICTO: APROBADO o VEREDICTO: CAMBIOS con la lista de cambios

Cómo trabajas:
1. Divide el encargo en tareas. Usa `delegar` con varias tareas a la vez cuando sean independientes (se ejecutan en paralelo).
2. Cada subagente empieza de cero: en cada tarea dale TODO el contexto que necesita (objetivo, público, tono, idioma,
   formato, nombres exactos de archivos a leer y a crear).
3. Antes de entregar, manda SIEMPRE el resultado a `revisa`. Si pide cambios, delega las correcciones y vuelve a revisar
   (máximo 2 rondas de corrección).
4. Termina llamando a `entregar` con un resumen para el usuario y la lista de archivos finales. No hagas tú el trabajo
   de los especialistas: tú planificas, coordinas y decides.
5. Escribe tus mensajes al usuario en español, breves."""


class Tarea(TypedDict):
    subagente: Literal["busca", "escribe", "disena", "revisa"]
    tarea: str


def _file_tools(job: Job, can_write: bool):
    @beta_tool
    def listar_archivos() -> str:
        """Lista los archivos del trabajo."""
        return json.dumps(job.list_files(), ensure_ascii=False)

    @beta_tool
    def leer_archivo(nombre: str) -> str:
        """Lee un archivo del trabajo.

        Args:
            nombre: Nombre del archivo (ej. 'investigacion.md').
        """
        try:
            return job.read_file(nombre)
        except (ValueError, FileNotFoundError) as e:
            return f"Error: {e}. Archivos: {job.list_files()}"

    @beta_tool
    def guardar_archivo(nombre: str, contenido: str) -> str:
        """Crea o reemplaza un archivo del trabajo (.md, .html, .svg, .txt, .json, .csv, .css).

        Args:
            nombre: Nombre del archivo, ej. 'landing.html' o 'textos/copy.md'.
            contenido: Contenido completo del archivo.
        """
        try:
            return "Guardado: " + job.write_file(nombre, contenido)
        except ValueError as e:
            return f"Error: {e}"

    return [listar_archivos, leer_archivo] + ([guardar_archivo] if can_write else [])


def _describe(block) -> str | None:
    if block.type == "server_tool_use":
        i = block.input or {}
        return ("🔎 " + i.get("query", "")) if block.name == "web_search" else ("🌐 " + i.get("url", ""))
    if block.type == "tool_use":
        i = block.input or {}
        if block.name == "guardar_archivo":
            return "💾 " + str(i.get("nombre", ""))
        if block.name == "leer_archivo":
            return "📖 " + str(i.get("nombre", ""))
    return None


def run_subagent(job: Job, key: str, tarea: str) -> str:
    spec = SUBAGENTS[key]
    job.set_agent(key, "trabajando", tarea)
    job.event(key, "inicio", tarea)
    try:
        tools = _file_tools(job, can_write=key != "revisa") + (WEB_TOOLS if spec["web"] else [])
        runner = client.beta.messages.tool_runner(
            **COMMON, model=MODEL_SUB, max_tokens=16000, output_config={"effort": spec["effort"]},
            system=spec["system"] + f"\n\nEncargo original del usuario (contexto): {job.data['encargo']}",
            tools=tools, messages=[{"role": "user", "content": tarea}], max_iterations=25,
        )
        last = None
        for msg in runner:
            last = msg
            job.add_usage(msg.usage)
            for b in msg.content:
                d = _describe(b)
                if d:
                    job.event(key, "accion", d)
        if last is None or last.stop_reason == "refusal":
            raise RuntimeError("no pudo completar la tarea")
        result = "\n".join(b.text for b in last.content if b.type == "text").strip() or "Hecho."
        job.event(key, "resultado", result)
        job.set_agent(key, "hecho")
        return result
    except Exception as e:  # noqa: BLE001
        job.event(key, "error", str(e))
        job.set_agent(key, "error")
        return f"ERROR de {spec['nombre']}: {e}"


def run_job(job: Job) -> None:
    """El jefe dirige al equipo hasta entregar."""
    delivered: dict = {}

    @beta_tool
    def delegar(tareas: list[Tarea]) -> str:
        """Encarga tareas a los subagentes. Las tareas de la lista se ejecutan EN PARALELO; si una depende de otra,
        delégala en una llamada posterior. Devuelve el resultado de cada subagente.

        Args:
            tareas: Lista de {subagente, tarea}. La tarea debe ser autosuficiente: objetivo, contexto, formato y
                nombres exactos de archivos a leer/crear.
        """
        tareas = [t for t in tareas if t["subagente"] in SUBAGENTS][:6]
        for t in tareas:
            job.event("jefe", "delega", f"→ {SUBAGENTS[t['subagente']]['nombre']}: {t['tarea']}")
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda t: run_subagent(job, t["subagente"], t["tarea"]), tareas))
        return "\n\n".join(f"## {SUBAGENTS[t['subagente']]['nombre']}\n{r}" for t, r in zip(tareas, results))

    @beta_tool
    def entregar(resumen: str, archivos: list[str]) -> str:
        """Entrega el trabajo terminado al usuario. Úsalo solo cuando Revisa lo haya aprobado (o tras 2 rondas).

        Args:
            resumen: Resumen para el usuario (qué se ha hecho, decisiones clave, cómo usarlo). Máx. 8 líneas.
            archivos: Archivos finales a entregar, en orden de importancia.
        """
        existing = set(job.list_files())
        delivered.update(resumen=resumen, archivos=[a for a in archivos if a in existing] or sorted(existing))
        job.event("jefe", "entrega", resumen)
        return "Entregado. Termina aquí."

    job.set_agent("jefe", "trabajando", "Planificando el encargo")
    job.event("jefe", "inicio", job.data["encargo"])
    try:
        runner = client.beta.messages.tool_runner(
            **COMMON, model=MODEL_JEFE, max_tokens=16000, output_config={"effort": "high"},
            system=JEFE_SYSTEM, tools=[delegar, entregar, *_file_tools(job, can_write=False)],
            messages=[{"role": "user", "content": job.data["encargo"]}], max_iterations=MAX_ROUNDS * 3,
        )
        for msg in runner:
            job.add_usage(msg.usage)
            text = "\n".join(b.text for b in msg.content if b.type == "text").strip()
            if text:
                job.event("jefe", "mensaje", text)
            if delivered:
                break
        job.set_agent("jefe", "hecho")
        if delivered:
            job.finish("hecho", delivered["resumen"], delivered["archivos"])
        else:
            job.finish("hecho", "El equipo terminó sin una entrega formal. Revisa los archivos generados.")
    except Exception as e:  # noqa: BLE001
        job.event("jefe", "error", str(e))
        job.set_agent("jefe", "error")
        job.finish("error", error=str(e))
