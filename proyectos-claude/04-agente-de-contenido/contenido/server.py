"""Web + programador nocturno del agente de contenido.  uvicorn contenido.server:app --port 8003"""
from __future__ import annotations

import json
import logging
import re
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from . import config, pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
sched = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global sched
    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler(timezone=config.TIMEZONE)
    hh, mm = (int(x) for x in config.HORA.split(":"))
    sched.add_job(lambda: pipeline.run_night() if not pipeline.is_running() else None,
                  "cron", hour=hh, minute=mm, id="noche", misfire_grace_time=3 * 3600)
    sched.start()
    yield
    sched.shutdown(wait=False)


app = FastAPI(title="Agente de contenido", lifespan=lifespan)


@app.middleware("http")
async def auth(request: Request, call_next):
    path = request.scope["path"]
    root = request.scope.get("root_path", "")
    if root and path.startswith(root):  # montada dentro de servidor.py (p. ej. /panel/api/...)
        path = path[len(root):]
    if path.startswith("/api/"):
        if config.WEB_TOKEN:
            if not secrets.compare_digest(request.headers.get("x-token", ""), config.WEB_TOKEN):
                return JSONResponse({"detail": "Token incorrecto"}, status_code=401)
        elif request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
            return JSONResponse({"detail": "Define CONTENIDO_WEB_TOKEN para usarlo fuera de localhost"}, status_code=403)
    return await call_next(request)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "web" / "index.html")


def _days() -> list[str]:
    if not config.OUT.exists():
        return []
    return sorted((p.name for p in config.OUT.iterdir() if p.is_dir() and DAY_RE.match(p.name)), reverse=True)


@app.get("/api/info")
def info():
    job = sched.get_job("noche") if sched else None
    return {"nicho": config.NICHO, "plataforma": config.PLATAFORMA, "competidores": config.COMPETIDORES,
            "hora": config.HORA, "zona": config.TIMEZONE, "num_guiones": config.NUM_GUIONES,
            "proxima": job.next_run_time.isoformat() if job and job.next_run_time else None,
            "trabajando": pipeline.is_running(), "noches": _days()}


@app.get("/api/noche/{day}")
def night(day: str):
    if not DAY_RE.match(day):
        raise HTTPException(404)
    d = config.OUT / day
    if not d.exists():
        raise HTTPException(404)

    def read(name):
        p = d / name
        return p.read_text(encoding="utf-8") if p.exists() else None

    estado = read("estado.json")
    guiones = read("guiones.json")
    return {"dia": day, "estado": json.loads(estado) if estado else None,
            "competencia": read("competencia.md"), "noticias": read("noticias.md"),
            "guiones": json.loads(guiones) if guiones else None}


@app.post("/api/ejecutar")
def run_now():
    if pipeline.is_running():
        raise HTTPException(409, "Ya está trabajando")
    threading.Thread(target=pipeline.run_night, daemon=True).start()
    return {"ok": True}


# --- App instalable (PWA): ficha de la app, service worker e iconos ---
_PWA = {"manifest.webmanifest": "application/manifest+json", "sw.js": "text/javascript",
        "icon-192.png": "image/png", "icon-512.png": "image/png"}


@app.get("/{name}")
def pwa_file(name: str):
    if name not in _PWA:
        raise HTTPException(404)
    return FileResponse(Path(__file__).parent / "web" / name, media_type=_PWA[name],
                        headers={"Cache-Control": "no-cache"})
