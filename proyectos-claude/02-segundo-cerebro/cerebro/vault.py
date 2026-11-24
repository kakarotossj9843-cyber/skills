"""Acceso al vault (carpeta de notas Markdown compatible con Obsidian)."""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "vault"))).expanduser().resolve()
PROFILE = "PERFIL.md"
IGNORED_FILES = {"CLAUDE.md", "00-Bandeja/LEEME.md"}
IGNORED_DIRS = {".obsidian", ".trash", ".git", ".procesadas", "90-Plantillas"}
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
WORD_RE = re.compile(r"\w+", re.UNICODE)


def _safe(rel: str) -> Path:
    """Resuelve una ruta relativa al vault impidiendo salir de él."""
    rel = rel.strip().lstrip("/\\")
    if not rel.endswith(".md"):
        rel += ".md"
    p = (VAULT / rel).resolve()
    if VAULT not in p.parents and p != VAULT:
        raise ValueError("Ruta fuera del vault")
    return p


def all_notes() -> list[Path]:
    out = []
    for p in VAULT.rglob("*.md"):
        r = p.relative_to(VAULT)
        if r.as_posix() in IGNORED_FILES:
            continue
        if not any(part in IGNORED_DIRS for part in r.parts):
            out.append(p)
    return sorted(out)


def rel(p: Path) -> str:
    return p.relative_to(VAULT).as_posix()


def read(path: str) -> str:
    p = _safe(path)
    if not p.exists():
        # permite buscar por título: "Marta" -> .../Marta.md
        title = Path(path).stem.lower()
        match = next((n for n in all_notes() if n.stem.lower() == title), None)
        if not match:
            raise FileNotFoundError(path)
        p = match
    return p.read_text(encoding="utf-8")


def write(path: str, content: str, overwrite: bool = False) -> str:
    p = _safe(path)
    if p.exists() and not overwrite:
        raise FileExistsError(rel(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.rstrip() + "\n", encoding="utf-8")
    return rel(p)


def append(path: str, content: str) -> str:
    p = _safe(path)
    if not p.exists():
        return write(path, f"# {p.stem}\n\n{content}")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"\n\n## {date.today().isoformat()}\n{content.rstrip()}\n")
    return rel(p)


def _tokens(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower()) if len(w) > 2]


def search(query: str, limit: int = 8) -> list[dict]:
    """Búsqueda por palabras clave con puntuación simple (título pesa más que el cuerpo)."""
    terms = set(_tokens(query))
    if not terms:
        return []
    results = []
    for p in all_notes():
        text = p.read_text(encoding="utf-8", errors="replace")
        low = text.lower()
        title = p.stem.lower()
        score = sum(low.count(t) for t in terms) + sum(5 for t in terms if t in title)
        if score:
            idx = min((low.find(t) for t in terms if t in low), default=0)
            snippet = text[max(0, idx - 120): idx + 240].replace("\n", " ").strip()
            results.append({"path": rel(p), "score": score, "snippet": snippet})
    results.sort(key=lambda r: -r["score"])
    return results[:limit]


def links(text: str) -> list[str]:
    return sorted({m.strip() for m in LINK_RE.findall(text)})


def tree() -> str:
    lines = []
    for p in all_notes():
        lines.append(rel(p))
    return "\n".join(lines) or "(vault vacío)"


def graph() -> dict:
    """Nodos y enlaces para el grafo visual."""
    notes = all_notes()
    by_title = {p.stem.lower(): rel(p) for p in notes}
    nodes, edges = [], []
    for p in notes:
        r = rel(p)
        area = r.split("/")[0] if "/" in r else "raíz"
        nodes.append({"id": r, "title": p.stem, "area": area})
        for l in links(p.read_text(encoding="utf-8", errors="replace")):
            target = by_title.get(Path(l).stem.lower())
            if target and target != r:
                edges.append({"source": r, "target": target})
    return {"nodes": nodes, "edges": edges}


def profile() -> str:
    p = VAULT / PROFILE
    return p.read_text(encoding="utf-8") if p.exists() else ""
