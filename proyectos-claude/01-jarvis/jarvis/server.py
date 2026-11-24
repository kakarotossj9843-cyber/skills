"""Servidor 24h de Jarvis: chat web, webhook de WhatsApp y rutinas programadas.

Arranque:  uvicorn jarvis.server:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from . import agent, config, routines
from .tools.whatsapp import send_to_owner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("jarvis")
WEB = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(_: FastAPI):
    sched = routines.start_scheduler()
    yield
    sched.shutdown(wait=False)


app = FastAPI(title="Jarvis", lifespan=lifespan)


def _check_web_auth(request: Request) -> None:
    if config.WEB_TOKEN:
        token = request.headers.get("x-jarvis-token", "")
        if not secrets.compare_digest(token, config.WEB_TOKEN):
            raise HTTPException(401, "Token incorrecto")
    elif request.client and request.client.host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(403, "Define JARVIS_WEB_TOKEN para usar el chat fuera de localhost")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/status")
def status():
    return {"integrations": config.status(), "brief_time": config.BRIEF_TIME,
            "needs_token": bool(config.WEB_TOKEN)}


class ChatIn(BaseModel):
    message: str


@app.post("/api/chat")
async def chat(body: ChatIn, request: Request):
    _check_web_auth(request)
    try:
        reply = await run_in_threadpool(agent.ask, body.message, "web")
    except Exception as e:  # noqa: BLE001
        log.exception("Error en el chat")
        reply = f"⚠️ No he podido responder: {e}"
    return {"reply": reply}


@app.post("/api/brief")
async def brief(request: Request):
    _check_web_auth(request)
    return {"reply": await run_in_threadpool(routines.morning_brief)}


def _handle_whatsapp(text: str) -> None:
    try:
        reply = agent.ask(text, chat="whatsapp")
    except Exception as e:  # noqa: BLE001
        log.exception("Error procesando WhatsApp")
        reply = f"⚠️ Error: {e}"
    send_to_owner(reply)


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, background: BackgroundTasks):
    """Webhook de Twilio: configúralo en 'When a message comes in' → POST {PUBLIC_BASE_URL}/whatsapp"""
    form = dict(await request.form())
    if config.TWILIO_AUTH_TOKEN:
        from twilio.request_validator import RequestValidator

        url = (config.PUBLIC_BASE_URL.rstrip("/") + "/whatsapp") if config.PUBLIC_BASE_URL else str(request.url)
        valid = RequestValidator(config.TWILIO_AUTH_TOKEN).validate(
            url, form, request.headers.get("X-Twilio-Signature", ""))
        if not valid:
            raise HTTPException(403, "Firma de Twilio no válida")
    if form.get("From") != config.OWNER_WHATSAPP:
        log.warning("Mensaje ignorado de %s (no es el dueño)", form.get("From"))
        return Response("<Response/>", media_type="application/xml")
    text = str(form.get("Body", "")).strip()
    if text:
        background.add_task(_handle_whatsapp, text)  # Twilio corta a los 15 s: respondemos aparte
    return Response("<Response/>", media_type="application/xml")


# --- App instalable (PWA): ficha de la app, service worker e iconos ---
_PWA = {"manifest.webmanifest": "application/manifest+json", "sw.js": "text/javascript",
        "icon-192.png": "image/png", "icon-512.png": "image/png"}


@app.get("/{name}")
def pwa_file(name: str):
    if name not in _PWA:
        raise HTTPException(404)
    return FileResponse(Path(__file__).parent / "web" / name, media_type=_PWA[name],
                        headers={"Cache-Control": "no-cache"})
