"""Un trabajo del equipo: carpeta de archivos, estado de cada agente y registro de eventos en vivo."""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
JOBS_DIR = Path(os.getenv("TRABAJOS", str(ROOT / "trabajos")))
AGENTS = ["jefe", "busca", "escribe", "disena", "revisa"]
ALLOWED_EXT = {".md", ".txt", ".html", ".svg", ".css", ".json", ".csv"}


class Job:
    def __init__(self, encargo: str, job_id: str | None = None) -> None:
        self.id = job_id or datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(2)
        self.dir = JOBS_DIR / self.id
        self.files = self.dir / "archivos"
        self.files.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.data = {
            "id": self.id, "encargo": encargo, "estado": "trabajando", "creado": datetime.now().isoformat(timespec="seconds"),
            "fin": None, "resumen": None, "entregables": [], "error": None,
            "agentes": {a: {"estado": "libre", "tarea": "", "trabajos": 0} for a in AGENTS},
            "eventos": [], "uso": {"entrada": 0, "salida": 0},
        }
        self.save()

    # ---- persistencia ----
    def save(self) -> None:
        with self._lock:
            tmp = self.dir / "job.json.tmp"
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(self.dir / "job.json")

    @staticmethod
    def load(job_id: str) -> dict | None:
        p = JOBS_DIR / job_id / "job.json"
        if not job_id.replace("-", "").isalnum() or not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def all() -> list[dict]:
        if not JOBS_DIR.exists():
            return []
        out = []
        for p in sorted(JOBS_DIR.glob("*/job.json"), reverse=True)[:50]:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({k: d[k] for k in ("id", "encargo", "estado", "creado")})
        return out

    # ---- eventos ----
    def event(self, agent: str, kind: str, text: str) -> None:
        with self._lock:
            self.data["eventos"].append({"t": round(time.time(), 2), "agente": agent, "tipo": kind, "texto": text[:600]})
            self.save()

    def set_agent(self, agent: str, estado: str, tarea: str = "") -> None:
        with self._lock:
            a = self.data["agentes"][agent]
            a["estado"] = estado
            if tarea:
                a["tarea"] = tarea[:200]
            if estado == "trabajando":
                a["trabajos"] += 1
            self.save()

    def add_usage(self, usage) -> None:
        if usage is None:
            return
        with self._lock:
            self.data["uso"]["entrada"] += (usage.input_tokens or 0) + (getattr(usage, "cache_read_input_tokens", 0) or 0)
            self.data["uso"]["salida"] += usage.output_tokens or 0

    def finish(self, estado: str, resumen: str | None = None, entregables: list[str] | None = None, error: str | None = None) -> None:
        with self._lock:
            self.data.update(estado=estado, fin=datetime.now().isoformat(timespec="seconds"),
                             resumen=resumen, entregables=entregables or self.list_files(), error=error)
            for a in self.data["agentes"].values():
                if a["estado"] == "trabajando":
                    a["estado"] = "libre"
            self.save()

    # ---- archivos (los agentes solo pueden tocar esta carpeta) ----
    def _path(self, name: str) -> Path:
        name = name.strip().lstrip("/\\")
        p = (self.files / name).resolve()
        if self.files.resolve() not in p.parents:
            raise ValueError("Ruta no permitida")
        if p.suffix.lower() not in ALLOWED_EXT:
            raise ValueError(f"Extensión no permitida. Usa: {', '.join(sorted(ALLOWED_EXT))}")
        return p

    def write_file(self, name: str, content: str) -> str:
        p = self._path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p.relative_to(self.files).as_posix()

    def read_file(self, name: str) -> str:
        return self._path(name).read_text(encoding="utf-8")

    def list_files(self) -> list[str]:
        return sorted(p.relative_to(self.files).as_posix() for p in self.files.rglob("*") if p.is_file())
