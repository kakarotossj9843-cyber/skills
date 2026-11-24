"""Base de datos del panel (SQLite) y cálculo de todas las métricas."""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_FILE = Path(os.getenv("PANEL_DB", str(ROOT / "panel.db")))
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales   (id INTEGER PRIMARY KEY, day TEXT NOT NULL, amount REAL NOT NULL,
                                    client TEXT DEFAULT '', concept TEXT DEFAULT '', source TEXT DEFAULT 'manual',
                                    ext_id TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, since TEXT NOT NULL,
                                    active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS habits  (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS habit_log (habit_id INTEGER NOT NULL, day TEXT NOT NULL, PRIMARY KEY (habit_id, day));
CREATE TABLE IF NOT EXISTS tasks   (id INTEGER PRIMARY KEY, title TEXT NOT NULL, created TEXT NOT NULL,
                                    done_at TEXT);
CREATE TABLE IF NOT EXISTS money   (id INTEGER PRIMARY KEY, day TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('ingreso','gasto')),
                                    amount REAL NOT NULL, concept TEXT DEFAULT '', category TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""

DEFAULTS = {"sales_goal_month": "15000", "savings_goal_month": "3000", "currency": "€"}


@contextmanager
def conn():
    with _lock:
        c = sqlite3.connect(DB_FILE)
        c.row_factory = sqlite3.Row
        c.executescript(SCHEMA)
        try:
            yield c
            c.commit()
        finally:
            c.close()


def today() -> date:
    return date.today()


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


# ---------- escritura ----------

def add_sale(amount: float, client: str = "", concept: str = "", day: str | None = None,
             source: str = "manual", ext_id: str | None = None) -> int:
    with conn() as c:
        cur = c.execute("INSERT OR IGNORE INTO sales (day, amount, client, concept, source, ext_id) VALUES (?,?,?,?,?,?)",
                        (day or today().isoformat(), float(amount), client.strip(), concept.strip(), source, ext_id))
        if client.strip():
            c.execute("INSERT OR IGNORE INTO clients (name, since) VALUES (?,?)", (client.strip(), day or today().isoformat()))
        return cur.lastrowid


def add_client(name: str, since: str | None = None) -> None:
    with conn() as c:
        c.execute("INSERT INTO clients (name, since) VALUES (?,?) ON CONFLICT(name) DO UPDATE SET active=1",
                  (name.strip(), since or today().isoformat()))


def set_client_active(name: str, active: bool) -> bool:
    with conn() as c:
        return c.execute("UPDATE clients SET active=? WHERE lower(name)=lower(?)", (int(active), name.strip())).rowcount > 0


def add_habit(name: str) -> None:
    with conn() as c:
        c.execute("INSERT INTO habits (name) VALUES (?) ON CONFLICT(name) DO UPDATE SET active=1", (name.strip(),))


def remove_habit(habit_id: int) -> None:
    with conn() as c:
        c.execute("UPDATE habits SET active=0 WHERE id=?", (habit_id,))


def set_habit(habit_id: int, done: bool, day: str | None = None) -> None:
    d = day or today().isoformat()
    with conn() as c:
        if done:
            c.execute("INSERT OR IGNORE INTO habit_log VALUES (?,?)", (habit_id, d))
        else:
            c.execute("DELETE FROM habit_log WHERE habit_id=? AND day=?", (habit_id, d))


def habit_id_by_name(name: str) -> int | None:
    with conn() as c:
        r = c.execute("SELECT id FROM habits WHERE active=1 AND lower(name) LIKE lower(?)", (f"%{name.strip()}%",)).fetchone()
        return r["id"] if r else None


def add_task(title: str) -> int:
    with conn() as c:
        return c.execute("INSERT INTO tasks (title, created) VALUES (?,?)", (title.strip(), today().isoformat())).lastrowid


def set_task(task_id: int, done: bool) -> None:
    with conn() as c:
        c.execute("UPDATE tasks SET done_at=? WHERE id=?", (today().isoformat() if done else None, task_id))


def delete_task(task_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))


def add_money(kind: str, amount: float, concept: str = "", category: str = "", day: str | None = None) -> int:
    if kind not in ("ingreso", "gasto"):
        raise ValueError("kind debe ser 'ingreso' o 'gasto'")
    with conn() as c:
        return c.execute("INSERT INTO money (day, kind, amount, concept, category) VALUES (?,?,?,?,?)",
                         (day or today().isoformat(), kind, abs(float(amount)), concept, category)).lastrowid


def delete_row(table: str, row_id: int) -> None:
    if table not in ("sales", "money", "tasks"):
        raise ValueError("tabla no permitida")
    with conn() as c:
        c.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))


def get_settings() -> dict:
    with conn() as c:
        s = dict(DEFAULTS)
        s.update({r["key"]: r["value"] for r in c.execute("SELECT key, value FROM settings")})
        return s


def set_setting(key: str, value: str) -> None:
    if key not in DEFAULTS:
        raise ValueError("ajuste desconocido")
    with conn() as c:
        c.execute("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


# ---------- lectura / métricas ----------

def _pct(cur: float, prev: float) -> float | None:
    return None if not prev else round((cur - prev) / prev * 100, 1)


def dashboard() -> dict:
    t = today()
    m0 = _month_start(t)
    months = [_add_months(m0, -i) for i in range(11, -1, -1)]  # 12 meses, el último es el actual
    s = get_settings()
    with conn() as c:
        # Ventas por mes
        rows = {r["m"]: r["total"] for r in c.execute(
            "SELECT substr(day,1,7) m, SUM(amount) total FROM sales WHERE day >= ? GROUP BY m", (months[0].isoformat(),))}
        sales_months = [{"month": m.isoformat()[:7], "total": round(rows.get(m.isoformat()[:7], 0) or 0, 2)} for m in months]
        cur, prev = sales_months[-1]["total"], sales_months[-2]["total"]
        # mismo punto del mes anterior para un % justo
        prev_same = c.execute("SELECT COALESCE(SUM(amount),0) FROM sales WHERE day >= ? AND day <= ?",
                              (months[-2].isoformat(), (months[-2] + timedelta(days=t.day - 1)).isoformat())).fetchone()[0]
        recent_sales = [dict(r) for r in c.execute(
            "SELECT id, day, amount, client, concept FROM sales ORDER BY day DESC, id DESC LIMIT 8")]

        # Hábitos: hoy + últimas 12 semanas
        habits = [dict(r) for r in c.execute("SELECT id, name FROM habits WHERE active=1 ORDER BY id")]
        start = t - timedelta(days=83)
        logs = c.execute("SELECT habit_id, day FROM habit_log WHERE day >= ?", (start.isoformat(),)).fetchall()
        done_by_day: dict[str, int] = {}
        done_today = set()
        per_habit: dict[int, set] = {}
        for r in logs:
            done_by_day[r["day"]] = done_by_day.get(r["day"], 0) + 1
            per_habit.setdefault(r["habit_id"], set()).add(r["day"])
            if r["day"] == t.isoformat():
                done_today.add(r["habit_id"])
        for h in habits:
            h["done"] = h["id"] in done_today
            streak, d = 0, t if h["done"] else t - timedelta(days=1)
            while d.isoformat() in per_habit.get(h["id"], set()):
                streak, d = streak + 1, d - timedelta(days=1)
            h["streak"] = streak
        heat = [{"day": (start + timedelta(days=i)).isoformat(),
                 "done": done_by_day.get((start + timedelta(days=i)).isoformat(), 0)} for i in range(84)]

        # Tareas: pendientes + hechas hoy
        tasks = [dict(r) for r in c.execute(
            "SELECT id, title, done_at FROM tasks WHERE done_at IS NULL OR done_at >= ? ORDER BY done_at IS NOT NULL, id DESC",
            (t.isoformat(),))]
        tasks_done_week = c.execute("SELECT COUNT(*) FROM tasks WHERE done_at >= ?",
                                    ((t - timedelta(days=6)).isoformat(),)).fetchone()[0]

        # Negocio
        active = c.execute("SELECT COUNT(*) FROM clients WHERE active=1").fetchone()[0]
        new_rows = {r["m"]: r["n"] for r in c.execute(
            "SELECT substr(since,1,7) m, COUNT(*) n FROM clients WHERE active=1 AND since >= ? GROUP BY m", (months[0].isoformat(),))}
        clients_months = [{"month": m.isoformat()[:7], "new": new_rows.get(m.isoformat()[:7], 0)} for m in months]
        active_series, base = [], c.execute("SELECT COUNT(*) FROM clients WHERE active=1 AND since < ?",
                                            (months[0].isoformat(),)).fetchone()[0]
        acc = base
        for cm in clients_months:
            acc += cm["new"]
            active_series.append(acc)
        top_clients = [dict(r) for r in c.execute(
            "SELECT client, SUM(amount) total FROM sales WHERE client != '' AND day >= ? GROUP BY client "
            "ORDER BY total DESC LIMIT 5", ((t - timedelta(days=90)).isoformat(),))]
        ticket = c.execute("SELECT AVG(amount) FROM sales WHERE day >= ?", ((t - timedelta(days=90)).isoformat(),)).fetchone()[0]

        # Dinero: ahorro = ingresos - gastos por mes
        mrows = c.execute("SELECT substr(day,1,7) m, kind, SUM(amount) total FROM money WHERE day >= ? GROUP BY m, kind",
                          (months[0].isoformat(),)).fetchall()
        mm: dict[str, dict] = {}
        for r in mrows:
            mm.setdefault(r["m"], {"ingreso": 0, "gasto": 0})[r["kind"]] = r["total"]
        money_months = []
        for m in months:
            k = m.isoformat()[:7]
            inc, exp = mm.get(k, {}).get("ingreso", 0), mm.get(k, {}).get("gasto", 0)
            money_months.append({"month": k, "ingresos": round(inc, 2), "gastos": round(exp, 2), "ahorro": round(inc - exp, 2)})
        cum, savings_cum = 0, []
        for mmn in money_months:
            cum += mmn["ahorro"]
            savings_cum.append(round(cum, 2))
        top_exp = [dict(r) for r in c.execute(
            "SELECT COALESCE(NULLIF(category,''),'Otros') category, SUM(amount) total FROM money "
            "WHERE kind='gasto' AND day >= ? GROUP BY 1 ORDER BY 2 DESC LIMIT 5", (m0.isoformat(),))]
        recent_money = [dict(r) for r in c.execute(
            "SELECT id, day, kind, amount, concept, category FROM money ORDER BY day DESC, id DESC LIMIT 8")]

    return {
        "today": t.isoformat(),
        "settings": s,
        "ventas": {"mes": cur, "mes_anterior": prev, "pct_vs_mismo_punto": _pct(cur, prev_same),
                   "objetivo": float(s["sales_goal_month"]), "meses": sales_months, "recientes": recent_sales},
        "habitos": {"lista": habits, "hechos_hoy": len(done_today), "total": len(habits), "calor": heat},
        "tareas": {"lista": tasks, "pendientes": sum(1 for x in tasks if not x["done_at"]), "hechas_semana": tasks_done_week},
        "negocio": {"clientes_activos": active, "nuevos_mes": clients_months[-1]["new"],
                    "serie_activos": active_series, "meses": [m["month"] for m in clients_months],
                    "ticket_medio": round(ticket or 0, 2), "top_clientes": top_clients},
        "dinero": {"ahorro_mes": money_months[-1]["ahorro"], "objetivo_ahorro": float(s["savings_goal_month"]),
                   "meses": money_months, "acumulado": savings_cum, "gastos_top": top_exp, "recientes": recent_money},
    }
