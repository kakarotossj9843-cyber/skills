"""Web del segundo cerebro: grafo de notas + chat.  uvicorn cerebro.server:app --port 8001"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import agent, vault

TOKEN = os.getenv("CEREBRO_WEB_TOKEN", "").strip()
app = FastAPI(title="Segundo cerebro")


def _auth(request: Request) -> None:
    if TOKEN:
        if not secrets.compare_digest(request.headers.get("x-token", ""), TOKEN):
            raise HTTPException(401, "Token incorrecto")
    elif request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
        raise HTTPException(403, "Define CEREBRO_WEB_TOKEN para usarlo fuera de localhost")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/api/graph")
def graph(request: Request):
    _auth(request)
    return vault.graph()


@app.get("/api/note")
def note(path: str, request: Request):
    _auth(request)
    try:
        return {"path": path, "content": vault.read(path)}
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "No existe")


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []
    mode: str = "ask"  # ask | capture


@app.post("/api/chat")
async def chat(body: ChatIn, request: Request):
    _auth(request)
    hist = [m for m in body.history[-20:] if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    while hist and hist[0]["role"] != "user":
        hist.pop(0)
    try:
        if body.mode == "capture":
            reply = await run_in_threadpool(agent.capture, body.message)
        else:
            reply = await run_in_threadpool(agent.ask, body.message, hist)
    except Exception as e:  # noqa: BLE001
        reply = f"⚠️ Error: {e}"
    return {"reply": reply}
