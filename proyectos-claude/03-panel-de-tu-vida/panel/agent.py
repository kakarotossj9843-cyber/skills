"""Claude en el panel: apunta cosas en lenguaje natural y analiza tu semana."""
from __future__ import annotations

import json
import os

import anthropic
from anthropic import beta_tool

from . import db

MODEL = os.getenv("PANEL_MODEL", "claude-opus-5-5")
client = anthropic.Anthropic()


@beta_tool
def registrar_venta(importe: float, cliente: str = "", concepto: str = "", fecha: str = "", moneda: str = "") -> str:
    """Registra una venta (ingreso del negocio). Si el cliente es nuevo, se añade a clientes activos.

    Args:
        importe: Importe sin símbolo, en la moneda indicada.
        moneda: Código ISO: USD (dólares, $), PEN (soles, S/), BOB (bolivianos, Bs), EUR. Vacío = moneda principal.
        cliente: Nombre del cliente (opcional).
        concepto: Qué se vendió (opcional).
        fecha: Fecha AAAA-MM-DD (vacío = hoy).
    """
    db.add_sale(importe, cliente, concepto, fecha or None, currency=moneda)
    return f"Venta de {importe} {db.norm_currency(moneda)} registrada"


@beta_tool
def registrar_movimiento(tipo: str, importe: float, concepto: str = "", categoria: str = "", fecha: str = "",
                         moneda: str = "") -> str:
    """Registra dinero personal: un ingreso (nómina, cobro) o un gasto (alquiler, comida…). Las VENTAS del negocio van con registrar_venta.

    Args:
        tipo: 'ingreso' o 'gasto'.
        importe: Importe positivo.
        concepto: Descripción breve.
        categoria: Categoría (Casa, Comida, Ocio, Transporte, Negocio, Suscripciones, Otros…).
        fecha: Fecha AAAA-MM-DD (vacío = hoy).
        moneda: Código ISO: USD (dólares, $), PEN (soles, S/), BOB (bolivianos, Bs), EUR. Vacío = moneda principal.
    """
    db.add_money(tipo, importe, concepto, categoria, fecha or None, currency=moneda)
    return f"{tipo} de {importe} {db.norm_currency(moneda)} registrado"


@beta_tool
def marcar_habito(nombre: str, hecho: bool = True, fecha: str = "") -> str:
    """Marca (o desmarca) un hábito como hecho. Si el hábito no existe, lo crea.

    Args:
        nombre: Nombre del hábito (ej. 'Gimnasio', 'Leer 20 min').
        hecho: True para marcarlo hecho, False para desmarcar.
        fecha: Fecha AAAA-MM-DD (vacío = hoy).
    """
    hid = db.habit_id_by_name(nombre)
    if hid is None:
        db.add_habit(nombre)
        hid = db.habit_id_by_name(nombre)
    db.set_habit(hid, hecho, fecha or None)
    return f"Hábito '{nombre}' {'hecho' if hecho else 'desmarcado'}"


@beta_tool
def anadir_tarea(titulo: str) -> str:
    """Añade una tarea pendiente.

    Args:
        titulo: La tarea, empezando por un verbo (ej. 'Enviar presupuesto a Marta').
    """
    db.add_task(titulo)
    return f"Tarea añadida: {titulo}"


@beta_tool
def completar_tarea(texto: str) -> str:
    """Marca como hecha la tarea pendiente que mejor coincida con el texto.

    Args:
        texto: Parte del título de la tarea.
    """
    tasks = [t for t in db.dashboard()["tareas"]["lista"] if not t["done_at"]]
    words = set(texto.lower().split())
    best = max(tasks, key=lambda t: len(words & set(t["title"].lower().split())), default=None)
    if not best or not (words & set(best["title"].lower().split())):
        return "No encuentro esa tarea. Pendientes: " + "; ".join(t["title"] for t in tasks)
    db.set_task(best["id"], True)
    return f"Tarea completada: {best['title']}"


@beta_tool
def cambiar_cliente(nombre: str, activo: bool) -> str:
    """Añade un cliente activo o lo marca como inactivo (baja).

    Args:
        nombre: Nombre del cliente.
        activo: True = alta/activo, False = baja.
    """
    if activo:
        db.add_client(nombre)
        return f"Cliente activo: {nombre}"
    return f"Cliente {nombre} dado de baja" if db.set_client_active(nombre, False) else f"No existe el cliente {nombre}"


TOOLS = [registrar_venta, registrar_movimiento, marcar_habito, anadir_tarea, completar_tarea, cambiar_cliente]


def _text(msg) -> str:
    if msg.stop_reason == "refusal":
        return "No puedo ayudar con eso."
    return "\n".join(b.text for b in msg.content if b.type == "text").strip()


def apuntar(texto: str) -> str:
    """'Hoy fui al gimnasio y vendí 450 € a Marta' → registra todo lo que corresponda."""
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=8000,
        system=("Eres el asistente del 'Panel de tu vida'. El usuario te dice en lenguaje natural cosas que han pasado "
                "(ventas, gastos, hábitos, tareas, clientes). Regístralo TODO con las herramientas, en paralelo si son "
                f"varias. Hoy es {db.today().isoformat()}. Hábitos actuales: "
                + ", ".join(h["name"] for h in db.dashboard()["habitos"]["lista"])
                + f". Moneda principal: {db.get_settings()['base_currency']}. Si el usuario dice soles o S/ usa PEN; "
                  "bolivianos o Bs, BOB; dólares o $, USD; euros, EUR. Si no dice moneda, usa la principal"
                + ". Después confirma en una o dos frases en español qué has apuntado. Si algo es ambiguo (p. ej. "
                  "importe sin número), pregunta en vez de inventar."),
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        tools=TOOLS,
        messages=[{"role": "user", "content": texto}],
        max_iterations=10,
    )
    return _text(runner.until_done()) or "Apuntado."


def analizar() -> str:
    """Análisis breve del panel: qué va bien, qué va mal y 3 acciones para esta semana."""
    data = db.dashboard()
    for k in ("recientes",):
        data["ventas"].pop(k, None)
        data["dinero"].pop(k, None)
    data["habitos"].pop("calor", None)
    msg = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=("Eres un coach de negocio y vida, directo y concreto. Analiza los datos del panel del usuario y "
                "responde en español con: 1) Lo mejor (1-2 líneas), 2) Lo que preocupa (1-2 líneas), "
                "3) Tres acciones concretas para esta semana. Usa números reales de los datos (los importes ya están "
                "convertidos a la moneda principal indicada en 'monedas.base'). Máximo 12 líneas, "
                "sin tablas."),
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": json.dumps(data, ensure_ascii=False)}],
    )
    return _text(msg)
