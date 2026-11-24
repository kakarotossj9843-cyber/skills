"""Web del equipo de agentes.  uvicorn equipo.server:app --port 8004"""
from __future__ import annotations

import os
import secrets
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from . import team
from .job import JOBS_DIR, Job

TOKEN = os.getenv("EQUIPO_WEB_TOKEN", "").strip()
MAX_ACTIVE = int(os.getenv("EQUIPO_MAX_TRABAJOS", "2"))
app = FastAPI(title="Equipo de agentes")
_active: set[str] = set()
_lock = threading.Lock()

MIME = {".html": "text/html", ".svg": "image/svg+xml", ".md": "text/markdown", ".txt": "text/plain",
        ".json": "application/json", ".csv": "text/csv", ".css": "text/css"}


@app.middleware("http")
async def auth(request: Request, call_next):
    path = request.scope["path"]
    root = request.scope.get("root_path", "")
    if root and path.startswith(root):  # montada dentro de servidor.py (p. ej. /panel/api/...)
        path = path[len(root):]
    if path.startswith("/api/"):
        if TOKEN:
            sent = request.headers.get("x-token", "") or request.query_params.get("token", "")
            if not secrets.compare_digest(sent, TOKEN):
                return JSONResponse({"detail": "Token incorrecto"}, status_code=401)
        elif request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
            return JSONResponse({"detail": "Define EQUIPO_WEB_TOKEN para usarlo fuera de localhost"}, status_code=403)
    return await call_next(request)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "web" / "index.html")


class Encargo(BaseModel):
    encargo: str = Field(min_length=5, max_length=6000)


def _run(job: Job) -> None:
    try:
        team.run_job(job)
    finally:
        with _lock:
            _active.discard(job.id)


@app.post("/api/trabajos")
def create(e: Encargo):
    with _lock:
        if len(_active) >= MAX_ACTIVE:
            raise HTTPException(429, f"Ya hay {len(_active)} trabajos en marcha; espera a que terminen")
        job = Job(e.encargo.strip())
        _active.add(job.id)
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return {"id": job.id}


@app.get("/api/trabajos")
def list_jobs():
    return Job.all()


@app.get("/api/trabajos/{job_id}")
def get_job(job_id: str, desde: int = 0):
    d = Job.load(job_id)
    if not d:
        raise HTTPException(404)
    d["total_eventos"] = len(d["eventos"])
    d["eventos"] = d["eventos"][desde:]
    d["archivos"] = sorted(p.relative_to(JOBS_DIR / job_id / "archivos").as_posix()
                           for p in (JOBS_DIR / job_id / "archivos").rglob("*") if p.is_file())
    return d


@app.get("/api/trabajos/{job_id}/archivos/{name:path}")
def get_file(job_id: str, name: str):
    if not Job.load(job_id):
        raise HTTPException(404)
    base = (JOBS_DIR / job_id / "archivos").resolve()
    p = (base / name).resolve()
    if base not in p.parents or not p.is_file() or p.suffix.lower() not in MIME:
        raise HTTPException(404)
    # Las piezas las genera una IA: se sirven aisladas (sin scripts ni acceso a la app)
    headers = {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; sandbox",
               "X-Content-Type-Options": "nosniff"}
    return Response(p.read_bytes(), media_type=MIME[p.suffix.lower()] + "; charset=utf-8", headers=headers)


# --- App instalable (PWA): ficha de la app, service worker e iconos ---
_PWA = {"manifest.webmanifest": "application/manifest+json", "sw.js": "text/javascript",
        "icon-192.png": "image/png", "icon-512.png": "image/png"}


@app.get("/{name}")
def pwa_file(name: str):
    if name not in _PWA:
        raise HTTPException(404)
    return FileResponse(Path(__file__).parent / "web" / name, media_type=_PWA[name],
                        headers={"Cache-Control": "no-cache"})
