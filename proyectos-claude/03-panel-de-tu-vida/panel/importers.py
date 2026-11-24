"""Importadores: CSV (de tu banco, Excel, Shopify…) y Stripe."""
from __future__ import annotations

import csv
import io
import os
import re
from datetime import date, datetime, timedelta

from . import db

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%m/%d/%Y", "%Y/%m/%d")
COLS = {
    "day": ("fecha", "date", "dia", "día", "created", "fecha operacion", "fecha operación", "fecha valor"),
    "amount": ("importe", "amount", "cantidad", "total", "precio", "valor", "net"),
    "client": ("cliente", "client", "customer", "nombre", "name", "customer email"),
    "concept": ("concepto", "concept", "descripcion", "descripción", "description", "detalle", "producto"),
    "category": ("categoria", "categoría", "category"),
    "currency": ("moneda", "currency", "divisa"),
}


def _num(s: str) -> float:
    s = re.sub(r"[^\d,.\-]", "", s.strip())
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def _date(s: str) -> str:
    s = s.strip()[:19]
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s[: len(datetime.now().strftime(f))], f).date().isoformat()
        except ValueError:
            continue
    return datetime.fromisoformat(s).date().isoformat()


def import_csv(content: str, kind: str, currency: str = "") -> dict:
    """kind: 'ventas' o 'banco'. En 'banco' los importes negativos son gastos y los positivos ingresos.
    currency: moneda del archivo (USD, PEN, BOB…); si el CSV tiene columna «moneda», manda esa."""
    sample = content[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(content), dialect=dialect)
    headers = {h: (h or "").strip().lower() for h in reader.fieldnames or []}
    col = {k: next((h for h, low in headers.items() if low in names), None) for k, names in COLS.items()}
    if not col["day"] or not col["amount"]:
        raise ValueError(f"No encuentro columnas de fecha e importe. Columnas: {list(headers.values())}")
    ok, errors = 0, 0
    for row in reader:
        try:
            day, amount = _date(row[col["day"]]), _num(row[col["amount"]])
            concept = row.get(col["concept"], "") if col["concept"] else ""
            cur = (row.get(col["currency"], "") if col["currency"] else "") or currency
            if kind == "ventas":
                db.add_sale(amount, row.get(col["client"], "") if col["client"] else "", concept, day, "csv", currency=cur)
            else:
                db.add_money("gasto" if amount < 0 else "ingreso", abs(amount), concept,
                             row.get(col["category"], "") if col["category"] else "", day, currency=cur)
            ok += 1
        except (ValueError, KeyError, TypeError):
            errors += 1
    return {"importadas": ok, "errores": errors}


def sync_stripe(days: int = 365) -> dict:
    """Importa los cobros correctos de Stripe como ventas (sin duplicar)."""
    import httpx

    key = os.getenv("STRIPE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Falta STRIPE_API_KEY en .env (usa una clave restringida de solo lectura)")
    since = int(datetime.combine(date.today() - timedelta(days=days), datetime.min.time()).timestamp())
    params = {"limit": 100, "created[gte]": since}
    n = 0
    with httpx.Client(base_url="https://api.stripe.com/v1", auth=(key, ""), timeout=30) as http:
        while True:
            r = http.get("/charges", params=params)
            r.raise_for_status()
            data = r.json()
            for ch in data["data"]:
                if ch["status"] != "succeeded" or ch.get("refunded"):
                    continue
                name = (ch.get("billing_details") or {}).get("name") or (ch.get("billing_details") or {}).get("email") or ""
                db.add_sale((ch["amount"] - ch.get("amount_refunded", 0)) / 100, name, ch.get("description") or "Stripe",
                            date.fromtimestamp(ch["created"]).isoformat(), "stripe", ch["id"], currency=ch["currency"].upper())
                n += 1
            if not data.get("has_more"):
                break
            params["starting_after"] = data["data"][-1]["id"]
    return {"cobros": n}
