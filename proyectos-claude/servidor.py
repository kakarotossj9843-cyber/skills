"""Las 5 apps en UNA sola dirección, lista para subir a internet e instalar en el móvil.

    python servidor.py              → http://localhost:8080
    (en la nube: Dockerfile + render.yaml; ver GUIA-APK.md)

Rutas:  /  (inicio)   /jarvis/   /cerebro/   /panel/   /contenido/   /equipo/

Variables útiles (en .env o en el panel del servidor):
    ANTHROPIC_API_KEY   tu clave de Claude (obligatoria)
    APP_PASSWORD        contraseña para entrar a las apps (obligatoria fuera de tu ordenador)
    DATA_DIR            carpeta donde guardar los datos (p. ej. /data en un disco persistente)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# --- Datos persistentes en DATA_DIR (si se define) ---
DATA = os.getenv("DATA_DIR", "").strip()
if DATA:
    data = Path(DATA)
    data.mkdir(parents=True, exist_ok=True)
    for var, value in {
        "JARVIS_DB": data / "jarvis.db",
        "GOOGLE_TOKEN_FILE": data / "token.json",
        "GOOGLE_CREDENTIALS_FILE": data / "credentials.json",
        "VAULT_PATH": data / "vault",
        "PANEL_DB": data / "panel.db",
        "SALIDAS": data / "salidas",
        "TRABAJOS": data / "trabajos",
    }.items():
        os.environ.setdefault(var, str(value))
    vault = Path(os.environ["VAULT_PATH"])
    if not vault.exists():  # primera vez: copia la plantilla del segundo cerebro
        shutil.copytree(ROOT / "02-segundo-cerebro" / "vault", vault)

# --- Una contraseña para todas las apps ---
PASSWORD = os.getenv("APP_PASSWORD", "").strip()
if PASSWORD:
    for var in ("JARVIS_WEB_TOKEN", "CEREBRO_WEB_TOKEN", "PANEL_WEB_TOKEN", "CONTENIDO_WEB_TOKEN", "EQUIPO_WEB_TOKEN"):
        os.environ.setdefault(var, PASSWORD)

for folder in ("01-jarvis", "02-segundo-cerebro", "03-panel-de-tu-vida", "04-agente-de-contenido", "05-equipo-de-agentes"):
    sys.path.insert(0, str(ROOT / folder))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse  # noqa: E402

from cerebro.server import app as cerebro_app  # noqa: E402
from contenido.server import app as contenido_app  # noqa: E402
from equipo.server import app as equipo_app  # noqa: E402
from jarvis.server import app as jarvis_app  # noqa: E402
from panel.server import app as panel_app  # noqa: E402

APPS = {"jarvis": jarvis_app, "cerebro": cerebro_app, "panel": panel_app, "contenido": contenido_app, "equipo": equipo_app}
HUB = ROOT / "inicio"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Las apps montadas no arrancan solas sus tareas programadas (resumen de Jarvis, noche del agente de contenido)
    async with AsyncExitStack() as stack:
        for sub in APPS.values():
            await stack.enter_async_context(sub.router.lifespan_context(sub))
        yield


app = FastAPI(title="Mis apps con Claude", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/salud")
def health():
    return {"ok": True, "claude": bool(os.getenv("ANTHROPIC_API_KEY")), "contraseña": bool(PASSWORD),
            "datos_persistentes": bool(DATA)}


@app.get("/.well-known/assetlinks.json")
def assetlinks():
    """Para el APK de PWABuilder: quita la barra del navegador. Pega su assetlinks.json en ASSETLINKS_JSON o en DATA_DIR."""
    raw = os.getenv("ASSETLINKS_JSON", "").strip()
    if not raw:
        for p in ([Path(DATA) / "assetlinks.json"] if DATA else []) + [ROOT / "assetlinks.json"]:
            if p.exists():
                raw = p.read_text(encoding="utf-8")
                break
    if not raw:
        raise HTTPException(404)
    return JSONResponse(json.loads(raw))


for prefix, sub in APPS.items():
    app.add_api_route(f"/{prefix}", lambda prefix=prefix: RedirectResponse(f"/{prefix}/"), include_in_schema=False)
    app.mount(f"/{prefix}", sub)


_HUB_FILES = {"manifest.webmanifest": "application/manifest+json", "sw.js": "text/javascript",
              "icon-192.png": "image/png", "icon-512.png": "image/png"}


@app.get("/")
def hub():
    return FileResponse(HUB / "index.html")


@app.get("/{name}")
def hub_file(name: str):
    if name not in _HUB_FILES:
        raise HTTPException(404)
    return FileResponse(HUB / name, media_type=_HUB_FILES[name], headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    print(f"✳ Mis apps con Claude → http://localhost:{port}")
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=port, proxy_headers=True)
