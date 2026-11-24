"""Calendario (Google Calendar). Modo DEMO si Google no está configurado."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from anthropic import beta_tool

from .. import config

_DEMO_EVENTS: list[dict] = [
    {"id": "ev1", "title": "Llamada con Marta", "start": "10:00", "end": "10:30", "day_offset": 0},
    {"id": "ev2", "title": "Gimnasio", "start": "19:00", "end": "20:00", "day_offset": 0},
    {"id": "ev3", "title": "Reunión con Carlos", "start": "11:00", "end": "12:00", "day_offset": 2},
]


def _tz() -> ZoneInfo:
    return ZoneInfo(config.TIMEZONE)


def _demo() -> bool:
    return not config.google_configured()


def _cal():
    from .google_auth import service

    return service("calendar", "v3")


def fetch_events(days: int = 1) -> list[dict]:
    now = datetime.now(_tz())
    if _demo():
        out = []
        for e in _DEMO_EVENTS:
            if e["day_offset"] < days:
                d = (now + timedelta(days=e["day_offset"])).date().isoformat()
                out.append({"id": e["id"], "title": e["title"], "start": f"{d} {e['start']}", "end": f"{d} {e['end']}"})
        return out
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    res = _cal().events().list(
        calendarId=config.GOOGLE_CALENDAR_ID, timeMin=start.isoformat(),
        timeMax=(start + timedelta(days=days)).isoformat(), singleEvents=True, orderBy="startTime",
    ).execute()
    return [{
        "id": e["id"], "title": e.get("summary", "(sin título)"),
        "start": e["start"].get("dateTime", e["start"].get("date")),
        "end": e["end"].get("dateTime", e["end"].get("date")),
        "location": e.get("location", ""),
    } for e in res.get("items", [])]


@beta_tool
def list_calendar_events(days: int = 1) -> str:
    """Lista los eventos del calendario desde hoy hasta dentro de N días.

    Args:
        days: Número de días a mirar (1 = solo hoy, 7 = semana).
    """
    return json.dumps({"demo": _demo(), "timezone": config.TIMEZONE,
                       "events": fetch_events(max(1, min(days, 31)))}, ensure_ascii=False)


@beta_tool
def create_calendar_event(title: str, start: str, end: str, description: str = "", attendees: str = "") -> str:
    """Crea un evento en el calendario.

    Args:
        title: Título del evento.
        start: Inicio en formato ISO local, ej. '2026-11-25T10:00'.
        end: Fin en formato ISO local, ej. '2026-11-25T11:00'.
        description: Descripción opcional.
        attendees: Emails de invitados separados por comas (opcional).
    """
    if _demo():
        _DEMO_EVENTS.append({"id": f"ev{len(_DEMO_EVENTS) + 1}", "title": title,
                             "start": start[-5:], "end": end[-5:], "day_offset": 0})
        return f"(DEMO) Evento «{title}» creado de {start} a {end}"
    body = {
        "summary": title, "description": description,
        "start": {"dateTime": datetime.fromisoformat(start).isoformat(), "timeZone": config.TIMEZONE},
        "end": {"dateTime": datetime.fromisoformat(end).isoformat(), "timeZone": config.TIMEZONE},
    }
    if attendees.strip():
        body["attendees"] = [{"email": a.strip()} for a in attendees.split(",") if a.strip()]
    ev = _cal().events().insert(calendarId=config.GOOGLE_CALENDAR_ID, body=body).execute()
    return f"Evento «{title}» creado: {ev.get('htmlLink', '')}"


@beta_tool
def delete_calendar_event(event_id: str) -> str:
    """Borra un evento del calendario. Confirma con el usuario antes de usarlo.

    Args:
        event_id: Id del evento (de list_calendar_events).
    """
    if _demo():
        _DEMO_EVENTS[:] = [e for e in _DEMO_EVENTS if e["id"] != event_id]
        return f"(DEMO) Evento {event_id} borrado"
    _cal().events().delete(calendarId=config.GOOGLE_CALENDAR_ID, eventId=event_id).execute()
    return f"Evento {event_id} borrado"


TOOLS = [list_calendar_events, create_calendar_event, delete_calendar_event]
