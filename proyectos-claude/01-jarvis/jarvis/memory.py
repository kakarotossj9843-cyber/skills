"""Memoria persistente de Jarvis (SQLite): historial de chat, notas y correos ya vistos."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime

from . import config

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_FILE, check_same_thread=False)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, chat TEXT, role TEXT, content TEXT, ts TEXT)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, note TEXT, ts TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS seen_emails (id TEXT PRIMARY KEY, ts TEXT)")
    return conn


def add_message(chat: str, role: str, content: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO messages (chat, role, content, ts) VALUES (?,?,?,?)",
            (chat, role, content, datetime.now().isoformat(timespec="seconds")),
        )


def history(chat: str, limit: int = 20) -> list[dict]:
    """Últimos turnos (solo texto) en orden cronológico, empezando siempre por 'user'."""
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE chat=? ORDER BY id DESC LIMIT ?", (chat, limit)
        ).fetchall()
    msgs = [{"role": r, "content": t} for r, t in reversed(rows)]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


def clear(chat: str) -> None:
    with _lock, _conn() as c:
        c.execute("DELETE FROM messages WHERE chat=?", (chat,))


def add_note(note: str) -> None:
    with _lock, _conn() as c:
        c.execute("INSERT INTO notes (note, ts) VALUES (?,?)", (note, datetime.now().isoformat(timespec="seconds")))


def notes() -> list[str]:
    with _lock, _conn() as c:
        return [f"[{ts[:10]}] {n}" for n, ts in c.execute("SELECT note, ts FROM notes ORDER BY id")]


def mark_seen(ids: list[str]) -> None:
    with _lock, _conn() as c:
        c.executemany(
            "INSERT OR IGNORE INTO seen_emails (id, ts) VALUES (?,?)",
            [(i, datetime.now().isoformat(timespec="seconds")) for i in ids],
        )


def unseen(ids: list[str]) -> list[str]:
    if not ids:
        return []
    with _lock, _conn() as c:
        seen = {r[0] for r in c.execute(
            f"SELECT id FROM seen_emails WHERE id IN ({','.join('?' * len(ids))})", ids
        )}
    return [i for i in ids if i not in seen]
