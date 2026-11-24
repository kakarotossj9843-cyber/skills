"""Panel de tu vida.  uvicorn panel.server:app --port 8002"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import agent, db, importers

TOKEN = os.getenv("PANEL_WEB_TOKEN", "").strip()
app = FastAPI(title="Panel de tu vida")


@app.middleware("http")
async def auth(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        if TOKEN:
            if not secrets.compare_digest(request.headers.get("x-token", ""), TOKEN):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Token incorrecto"}, status_code=401)
        elif request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Define PANEL_WEB_TOKEN para usarlo fuera de localhost"}, status_code=403)
    return await call_next(request)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/api/dashboard")
def dashboard():
    return db.dashboard()


class Sale(BaseModel):
    amount: float = Field(gt=0)
    currency: str = ""
    client: str = ""
    concept: str = ""
    day: str | None = None


@app.post("/api/ventas")
def add_sale(s: Sale):
    db.add_sale(s.amount, s.client, s.concept, s.day, currency=s.currency)
    return {"ok": True}


class Money(BaseModel):
    kind: str
    amount: float = Field(gt=0)
    currency: str = ""
    concept: str = ""
    category: str = ""
    day: str | None = None


@app.post("/api/dinero")
def add_money(m: Money):
    try:
        db.add_money(m.kind, m.amount, m.concept, m.category, m.day, currency=m.currency)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


class Name(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@app.post("/api/habitos")
def add_habit(h: Name):
    db.add_habit(h.name)
    return {"ok": True}


@app.delete("/api/habitos/{hid}")
def remove_habit(hid: int):
    db.remove_habit(hid)
    return {"ok": True}


class Toggle(BaseModel):
    done: bool
    day: str | None = None


@app.post("/api/habitos/{hid}")
def toggle_habit(hid: int, t: Toggle):
    db.set_habit(hid, t.done, t.day)
    return {"ok": True}


@app.post("/api/tareas")
def add_task(t: Name):
    db.add_task(t.name)
    return {"ok": True}


@app.post("/api/tareas/{tid}")
def toggle_task(tid: int, t: Toggle):
    db.set_task(tid, t.done)
    return {"ok": True}


@app.delete("/api/{table}/{rid}")
def delete(table: str, rid: int):
    mapping = {"tareas": "tasks", "ventas": "sales", "dinero": "money"}
    if table not in mapping:
        raise HTTPException(404)
    db.delete_row(mapping[table], rid)
    return {"ok": True}


@app.post("/api/clientes")
def add_client(c: Name):
    db.add_client(c.name)
    return {"ok": True}


class Setting(BaseModel):
    key: str
    value: str


@app.post("/api/ajustes")
def set_setting(s: Setting):
    try:
        db.set_setting(s.key, s.value)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/importar")
async def import_csv(kind: str = Form(...), file: UploadFile = File(...), currency: str = Form("")):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    try:
        return importers.import_csv(text, "ventas" if kind == "ventas" else "banco", currency)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/tipos-de-cambio")
async def update_rates():
    try:
        return {"tasas": await run_in_threadpool(db.update_rates_online)}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"No se pudieron descargar los tipos de cambio: {e}")


@app.post("/api/stripe")
async def stripe():
    try:
        return await run_in_threadpool(importers.sync_stripe)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, str(e))


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@app.post("/api/claude/apuntar")
async def apuntar(t: Text):
    try:
        return {"reply": await run_in_threadpool(agent.apuntar, t.text)}
    except Exception as e:  # noqa: BLE001
        return {"reply": f"⚠️ {e}"}


@app.post("/api/claude/analisis")
async def analisis():
    try:
        return {"reply": await run_in_threadpool(agent.analizar)}
    except Exception as e:  # noqa: BLE001
        return {"reply": f"⚠️ {e}"}
