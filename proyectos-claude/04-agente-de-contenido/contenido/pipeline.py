"""El trabajo nocturno: 1) investiga a la competencia, 2) mira las noticias del día, 3) escribe los guiones.

Cada paso guarda su resultado en salidas/AAAA-MM-DD/ y actualiza estado.json para que la web muestre el progreso.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from . import config

log = logging.getLogger("contenido")
client = anthropic.Anthropic()
_running = threading.Lock()

STEPS = [
    {"id": "competencia", "titulo": "Investiga a la competencia", "icono": "search"},
    {"id": "noticias", "titulo": "Mira las noticias del día", "icono": "news"},
    {"id": "guiones", "titulo": "Escribe los guiones", "icono": "doc"},
]

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 12,
     "user_location": {"type": "approximate", "country": config.PAIS, "timezone": config.TIMEZONE}},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 8, "max_content_tokens": 20000},
]

COMMON = dict(
    model=config.MODEL,
    betas=["server-side-fallback-2026-07-01"],
    fallbacks="default",
    thinking={"type": "adaptive"},
)

GUIONES_SCHEMA = {
    "type": "object",
    "properties": {
        "guiones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string"},
                    "formato": {"type": "string", "description": "ej. lista, tutorial, opinión, noticia, storytelling"},
                    "duracion_seg": {"type": "integer"},
                    "gancho": {"type": "string", "description": "primera frase, 2-3 segundos"},
                    "guion": {"type": "string", "description": "texto completo para leer a cámara, con [indicaciones visuales] entre corchetes"},
                    "cta": {"type": "string"},
                    "texto_pantalla": {"type": "string", "description": "título corto para la portada/miniatura"},
                    "descripcion": {"type": "string", "description": "copy para la publicación con hashtags"},
                    "por_que_funciona": {"type": "string"},
                    "fuentes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["titulo", "formato", "duracion_seg", "gancho", "guion", "cta", "texto_pantalla",
                             "descripcion", "por_que_funciona", "fuentes"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["guiones"],
    "additionalProperties": False,
}


def _now() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE))


class Night:
    """Una noche de trabajo: carpeta de salida + estado en vivo."""

    def __init__(self) -> None:
        self.day = _now().date().isoformat()
        self.dir = config.OUT / self.day
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state = {
            "dia": self.day, "inicio": _now().isoformat(timespec="seconds"), "fin": None, "estado": "trabajando",
            "pasos": [dict(s, progreso=0.0, estado="pendiente", detalle="", busquedas=0) for s in STEPS],
        }
        self.save()

    def step(self, sid: str) -> dict:
        return next(s for s in self.state["pasos"] if s["id"] == sid)

    _lock = threading.Lock()

    def update(self, sid: str, **kw) -> None:
        with self._lock:
            self.step(sid).update(kw)
        self.save()

    def save(self) -> None:
        with self._lock:  # dos pasos trabajan en paralelo: escrituras atómicas y en orden
            tmp = self.dir / "estado.json.tmp"
            tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.dir / "estado.json")

    def write(self, name: str, text: str) -> None:
        (self.dir / name).write_text(text, encoding="utf-8")


def _text(msg) -> str:
    return "\n".join(b.text for b in msg.content if b.type == "text").strip()


def _research(night: Night, sid: str, system: str, prompt: str, expected_searches: int) -> str:
    """Paso con búsqueda web; el progreso avanza con cada búsqueda/lectura que hace Claude."""
    night.update(sid, estado="trabajando", progreso=0.05, detalle="Pensando por dónde empezar…")
    runner = client.beta.messages.tool_runner(
        **COMMON, max_tokens=16000, output_config={"effort": "high"}, system=system, tools=WEB_TOOLS,
        messages=[{"role": "user", "content": prompt}], max_iterations=20,
    )
    uses, last = 0, None
    for msg in runner:
        last = msg
        for b in msg.content:
            if b.type == "server_tool_use":
                uses += 1
                q = (b.input or {}).get("query") or (b.input or {}).get("url") or ""
                night.update(sid, busquedas=uses, detalle=f"{'Buscando' if b.name == 'web_search' else 'Leyendo'}: {q}"[:140],
                             progreso=min(0.9, 0.05 + 0.85 * uses / expected_searches))
    if last is None or last.stop_reason == "refusal":
        raise RuntimeError("Claude no pudo completar este paso")
    return _text(last)


def investigar_competencia(night: Night) -> str:
    comp = ", ".join(config.COMPETIDORES) or "(no hay lista: encuentra tú los 5 creadores más relevantes del nicho)"
    out = _research(
        night, "competencia",
        system=("Eres analista de contenido para redes sociales. Investigas con búsquedas web reales y nunca inventas "
                "datos: si algo no lo encuentras, dilo."),
        prompt=(f"Nicho: {config.NICHO}. Plataforma: {config.PLATAFORMA}. Competidores: {comp}.\n\n"
                "Investiga qué están publicando estos creadores/marcas últimamente (últimas 1-2 semanas si es posible). "
                "Devuélveme un informe en Markdown con:\n"
                "## Qué están publicando\n(por competidor: temas, formatos, frecuencia)\n"
                "## Lo que mejor les funciona\n(ganchos, formatos y temas que se repiten o tienen más tracción)\n"
                "## Huecos y oportunidades\n(temas que nadie cubre bien y ángulos para diferenciarme)\n"
                "## Fuentes\n(enlaces)\nSé concreto y breve: máximo ~600 palabras."),
        expected_searches=10,
    )
    night.write("competencia.md", out)
    return out


def mirar_noticias(night: Night) -> str:
    out = _research(
        night, "noticias",
        system="Eres editor de actualidad. Solo das noticias verificadas con búsqueda web, con fecha y enlace.",
        prompt=(f"Hoy es {_now().strftime('%A %d/%m/%Y')}. Busca las noticias más importantes de las últimas 24-48 horas "
                f"sobre: {config.NICHO}. Prioriza lo que le interesaría a la audiencia de {config.PLATAFORMA} "
                f"en {config.IDIOMA}.\n\nDevuélveme en Markdown las 5-8 mejores, cada una así:\n"
                "### Titular\n- **Qué ha pasado:** 2 frases\n- **Por qué importa a mi audiencia:** 1 frase\n"
                "- **Ángulo para un vídeo:** 1 frase\n- **Fuente:** enlace (fecha)\n"),
        expected_searches=8,
    )
    night.write("noticias.md", out)
    return out


def escribir_guiones(night: Night, competencia: str, noticias: str) -> list[dict]:
    night.update("guiones", estado="trabajando", progreso=0.1, detalle=f"Escribiendo {config.NUM_GUIONES} guiones…")
    marca = config.marca() or "(sin guía de marca: tono cercano, directo y útil)"
    with client.beta.messages.stream(
        **COMMON, max_tokens=32000, output_config={"effort": "high", "format": {"type": "json_schema", "schema": GUIONES_SCHEMA}},
        system=(f"Eres guionista de vídeos cortos virales para {config.PLATAFORMA}, en {config.IDIOMA}. "
                "Escribes como habla una persona, frases cortas, sin relleno, con un gancho brutal en los primeros 2 "
                "segundos y un ritmo que retiene hasta el final. Nada de clickbait falso: todo dato debe venir de la "
                "investigación que te paso.\n\n<marca>\n" + marca + "\n</marca>"),
        messages=[{"role": "user", "content": (
            f"Escribe {config.NUM_GUIONES} guiones distintos para mañana (mezcla formatos: al menos uno basado en una "
            "noticia y otro en un hueco que deja la competencia).\n\n"
            f"<competencia>\n{competencia}\n</competencia>\n\n<noticias>\n{noticias}\n</noticias>")}],
    ) as stream:
        chars = 0
        for event in stream:
            if event.type == "content_block_delta" and getattr(event.delta, "type", "") == "text_delta":
                chars += len(event.delta.text)
                if chars % 400 < len(event.delta.text):
                    night.update("guiones", progreso=min(0.95, 0.1 + 0.85 * chars / (1800 * config.NUM_GUIONES)))
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError("Claude no pudo escribir los guiones")
    guiones = json.loads(_text(msg))["guiones"]
    night.write("guiones.json", json.dumps(guiones, ensure_ascii=False, indent=2))
    md = [f"# Guiones para {config.PLATAFORMA} — {night.day}\n"]
    for i, g in enumerate(guiones, 1):
        md.append(f"## {i}. {g['titulo']}\n*{g['formato']} · ~{g['duracion_seg']} s · Portada: «{g['texto_pantalla']}»*\n\n"
                  f"**Gancho:** {g['gancho']}\n\n{g['guion']}\n\n**CTA:** {g['cta']}\n\n**Descripción:** {g['descripcion']}\n\n"
                  f"> Por qué funciona: {g['por_que_funciona']}\n\nFuentes: " + ", ".join(g["fuentes"]) + "\n")
    night.write("guiones.md", "\n".join(md))
    return guiones


def _notify(night: Night, guiones: list[dict] | None, error: str | None) -> None:
    if not config.NOTIFY_WEBHOOK:
        return
    import httpx

    text = (f"🌙 Contenido listo ({night.day}): " + " | ".join(g["titulo"] for g in guiones)) if guiones else f"⚠️ El agente falló: {error}"
    try:
        httpx.post(config.NOTIFY_WEBHOOK, json={"text": text, "content": text}, timeout=10)
    except httpx.HTTPError as e:
        log.warning("No se pudo notificar: %s", e)


def run_night() -> dict:
    """Ejecuta la noche completa. Devuelve el estado final."""
    if not _running.acquire(blocking=False):
        raise RuntimeError("Ya hay una ejecución en marcha")
    night = Night()
    guiones, error = None, None
    try:
        # 1 y 2 son independientes: se ejecutan a la vez
        results: dict[str, str] = {}
        errors: dict[str, Exception] = {}

        def work(sid, fn):
            t0 = time.time()
            try:
                results[sid] = fn(night)
                night.update(sid, estado="hecho", progreso=1.0, detalle=f"Listo en {int(time.time() - t0)} s")
            except Exception as e:  # noqa: BLE001
                errors[sid] = e
                night.update(sid, estado="error", detalle=str(e)[:200])

        threads = [threading.Thread(target=work, args=a) for a in (("competencia", investigar_competencia), ("noticias", mirar_noticias))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if len(errors) == 2:
            raise RuntimeError(f"Fallaron la investigación y las noticias: {errors}")
        t0 = time.time()
        guiones = escribir_guiones(night, results.get("competencia", "(sin datos)"), results.get("noticias", "(sin datos)"))
        night.update("guiones", estado="hecho", progreso=1.0, detalle=f"{len(guiones)} guiones en {int(time.time() - t0)} s")
        night.state["estado"] = "hecho"
    except Exception as e:  # noqa: BLE001
        log.exception("La noche falló")
        error = str(e)
        night.state["estado"] = "error"
        night.state["error"] = error[:300]
        for s in night.state["pasos"]:
            if s["estado"] == "trabajando":
                s["estado"] = "error"
    finally:
        night.state["fin"] = _now().isoformat(timespec="seconds")
        night.save()
        _running.release()
    _notify(night, guiones, error)
    return night.state


def is_running() -> bool:
    return _running.locked()
