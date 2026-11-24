"""Rutinas automáticas 24h: resumen matinal y vigilancia de la bandeja de entrada."""
from __future__ import annotations

import logging

from . import agent, config, memory
from .tools import gmail
from .tools.whatsapp import send_to_owner

log = logging.getLogger("jarvis.routines")


def morning_brief() -> str:
    """Resumen del día: agenda, correos pendientes y tareas. Se envía por WhatsApp."""
    text = agent.ask(
        "Prepárame el resumen de la mañana: 1) mi agenda de hoy, 2) correos no leídos importantes "
        "(ignora publicidad y notificaciones automáticas) con lo que debería hacer con cada uno, "
        "3) mis tareas pendientes de Notion, 4) tu sugerencia de prioridades para hoy. "
        "Máximo 15 líneas. NO lo envíes tú por WhatsApp, solo devuélvemelo.",
        chat="rutinas",
        save=False,
    )
    send_to_owner("☀️ Buenos días\n\n" + text)
    return text


def check_inbox() -> str | None:
    """Mira correos nuevos; si alguno es importante, avisa por WhatsApp."""
    try:
        emails = gmail.fetch_unread(15)
    except Exception as e:  # noqa: BLE001
        log.warning("No se pudo leer el correo: %s", e)
        return None
    new_ids = memory.unseen([e["id"] for e in emails])
    if not new_ids:
        return None
    new = [e for e in emails if e["id"] in new_ids]
    listing = "\n".join(f"- [{e['id']}] {e['from']} | {e['subject']} | {e['snippet']}" for e in new)
    verdict = agent.ask(
        "Han llegado estos correos nuevos:\n" + listing + "\n\nSi ALGUNO es importante o urgente para mí "
        "(clientes, dinero, citas, personas cercanas), respóndeme con un aviso breve de qué es y qué propones. "
        "Si ninguno lo es, responde exactamente: NADA",
        chat="rutinas",
        save=False,
    )
    memory.mark_seen(new_ids)
    if verdict.strip().upper().startswith("NADA"):
        return None
    send_to_owner("📬 " + verdict)
    return verdict


def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler(timezone=config.TIMEZONE)
    hh, mm = (int(x) for x in config.BRIEF_TIME.split(":"))
    sched.add_job(morning_brief, "cron", hour=hh, minute=mm, id="brief", misfire_grace_time=3600)
    if config.INBOX_CHECK_MINUTES > 0:
        sched.add_job(check_inbox, "interval", minutes=config.INBOX_CHECK_MINUTES, id="inbox")
    sched.start()
    log.info("Rutinas activas: resumen a las %s, correo cada %s min", config.BRIEF_TIME, config.INBOX_CHECK_MINUTES)
    return sched
