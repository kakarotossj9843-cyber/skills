"""Notion: tareas en una base de datos + búsqueda. Modo DEMO si no está configurado."""
from __future__ import annotations

import json

from anthropic import beta_tool

from .. import config

_DEMO_TASKS = [
    {"id": "t1", "title": "Enviar presupuesto a Marta", "done": False},
    {"id": "t2", "title": "Grabar vídeo", "done": False},
    {"id": "t3", "title": "Llamar a Carlos", "done": True},
]


def _demo() -> bool:
    return not config.notion_configured()


def _client():
    from notion_client import Client

    return Client(auth=config.NOTION_TOKEN)


_ds_id: str | None = None


def _data_source_id() -> str:
    """API de Notion 2025-09-03: las filas viven en el 'data source' de la base de datos."""
    global _ds_id
    if _ds_id is None:
        db = _client().databases.retrieve(database_id=config.NOTION_TASKS_DB_ID)
        _ds_id = db["data_sources"][0]["id"]
    return _ds_id


def _title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in prop["title"])
    return "(sin título)"


def _done(page: dict) -> bool | None:
    p = page.get("properties", {}).get(config.NOTION_STATUS_PROPERTY) if config.NOTION_STATUS_PROPERTY else None
    if not p:
        return None
    if p["type"] == "checkbox":
        return p["checkbox"]
    if p["type"] in ("status", "select") and p[p["type"]]:
        return p[p["type"]]["name"].lower() in ("done", "hecho", "completado", "completada", "listo")
    return None


def fetch_tasks(limit: int = 30) -> list[dict]:
    if _demo():
        return list(_DEMO_TASKS)
    res = _client().data_sources.query(data_source_id=_data_source_id(), page_size=min(limit, 100))
    return [{"id": p["id"], "title": _title(p), "done": _done(p), "url": p.get("url")} for p in res["results"]]


@beta_tool
def list_notion_tasks() -> str:
    """Lista las tareas de la base de datos de tareas de Notion."""
    return json.dumps({"demo": _demo(), "tasks": fetch_tasks()}, ensure_ascii=False)


@beta_tool
def create_notion_task(title: str, notes: str = "") -> str:
    """Crea una tarea nueva en la base de datos de tareas de Notion.

    Args:
        title: Título de la tarea.
        notes: Notas o contexto opcional (se añade como texto dentro de la página).
    """
    if _demo():
        _DEMO_TASKS.append({"id": f"t{len(_DEMO_TASKS) + 1}", "title": title, "done": False})
        return f"(DEMO) Tarea creada: {title}"
    children = []
    if notes:
        children = [{"object": "block", "type": "paragraph",
                     "paragraph": {"rich_text": [{"type": "text", "text": {"content": notes[:1900]}}]}}]
    page = _client().pages.create(
        parent={"type": "data_source_id", "data_source_id": _data_source_id()},
        properties={config.NOTION_TITLE_PROPERTY: {"title": [{"text": {"content": title}}]}},
        children=children,
    )
    return f"Tarea creada en Notion: {title} ({page.get('url', '')})"


@beta_tool
def complete_notion_task(task_id: str) -> str:
    """Marca una tarea de Notion como hecha.

    Args:
        task_id: Id de la tarea (de list_notion_tasks).
    """
    if _demo():
        for t in _DEMO_TASKS:
            if t["id"] == task_id:
                t["done"] = True
        return f"(DEMO) Tarea {task_id} completada"
    if not config.NOTION_STATUS_PROPERTY:
        return "No hay NOTION_STATUS_PROPERTY configurada; no puedo marcar tareas como hechas."
    c = _client()
    db = c.data_sources.retrieve(data_source_id=_data_source_id())
    ptype = db["properties"][config.NOTION_STATUS_PROPERTY]["type"]
    if ptype == "checkbox":
        value = {"checkbox": True}
    else:
        opts = db["properties"][config.NOTION_STATUS_PROPERTY][ptype]["options"]
        name = next((o["name"] for o in opts if o["name"].lower() in ("done", "hecho", "completado", "listo")),
                    opts[-1]["name"])
        value = {ptype: {"name": name}}
    c.pages.update(page_id=task_id, properties={config.NOTION_STATUS_PROPERTY: value})
    return f"Tarea {task_id} marcada como hecha"


@beta_tool
def search_notion(query: str) -> str:
    """Busca páginas en todo el Notion compartido con la integración.

    Args:
        query: Texto a buscar.
    """
    if _demo():
        return json.dumps({"demo": True, "results": [t for t in _DEMO_TASKS if query.lower() in t["title"].lower()]},
                          ensure_ascii=False)
    res = _client().search(query=query, page_size=10)
    return json.dumps({"demo": False, "results": [
        {"id": r["id"], "type": r["object"], "title": _title(r), "url": r.get("url")} for r in res["results"]
    ]}, ensure_ascii=False)


TOOLS = [list_notion_tasks, create_notion_task, complete_notion_task, search_notion]
