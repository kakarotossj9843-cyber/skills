# 🤖 Proyecto 1/5 — Tu propio Jarvis

Asistente personal 24 h hecho con Claude. Conectado a **Correo (Gmail)**, **Calendario (Google Calendar)**,
**Notion** y **WhatsApp**, te resuelve el día a día:

- Le escribes por **WhatsApp** (o por el chat web / terminal) y actúa: lee y resume correos, redacta
  respuestas (como borrador), crea eventos, apunta tareas en Notion…
- **Resumen de la mañana** automático por WhatsApp (agenda + correos importantes + tareas + prioridades).
- **Vigila tu bandeja** cada 30 min y te avisa solo si llega algo importante.
- **Memoria**: recuerda personas, preferencias y rutinas que le cuentes.

Sin configurar nada funciona en **modo demo** (datos de ejemplo). Cada integración se activa al poner sus claves.

## 1. Instalación

```bash
cd 01-jarvis
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # y rellénalo
```

## 2. Claves (lo único que necesitas aportar tú)

| Integración | Qué necesitas | Dónde se consigue |
|---|---|---|
| **Claude** (obligatorio) | `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| **Gmail + Calendar** | `credentials.json` | Google Cloud Console → crea proyecto → activa *Gmail API* y *Google Calendar API* → Pantalla de consentimiento (tipo externo, añádete como *test user*) → Credenciales → *OAuth client ID* tipo **Desktop app** → descarga el JSON como `credentials.json` en esta carpeta. Luego: `python -m jarvis.setup_google` |
| **Notion** | `NOTION_TOKEN` + `NOTION_TASKS_DB_ID` | notion.so/my-integrations → nueva integración → copia el token. Crea una base de datos «Tareas», en `···` → *Conexiones* añade tu integración. El ID es el código de 32 caracteres de su URL |
| **WhatsApp** | Cuenta Twilio | twilio.com → Messaging → *Try WhatsApp* (sandbox gratis): copia SID, Auth Token y el número `whatsapp:+1415…`. En el sandbox pon como webhook *When a message comes in*: `https://TU_URL/whatsapp` (POST) |

> Para que WhatsApp llegue a tu ordenador necesitas una URL pública: `ngrok http 8000` y pon esa URL en
> `PUBLIC_BASE_URL` y en Twilio. Para 24 h reales, despliega en un servidor (Railway, Render, un VPS…).

## 3. Uso

```bash
# Chat en terminal (lo más rápido para probar)
python -m jarvis.cli

# Modo 24 h: chat web + WhatsApp + rutinas automáticas
uvicorn jarvis.server:app --host 0.0.0.0 --port 8000
# abre http://localhost:8000
```

Ejemplos de lo que puedes pedirle:
- «¿Qué tengo hoy?»
- «Resúmeme los correos sin leer y prepárame respuesta al de Marta»
- «Ponme una reunión con Carlos el jueves a las 12 una hora»
- «Apunta en Notion: mandar factura a Marta»
- «Recuerda que los lunes voy al gimnasio a las 19:00»

## Seguridad

- Por defecto **no envía correos**: crea borradores (`ALLOW_SEND_EMAIL=false`).
- Solo obedece a mensajes de WhatsApp de tu número (`OWNER_WHATSAPP`) y valida la firma de Twilio.
- Fuera de localhost, el chat web exige `JARVIS_WEB_TOKEN`.
- `.env`, `credentials.json` y `token.json` están en `.gitignore`: no los subas nunca.

## Estructura

```
jarvis/
  agent.py        cerebro: Claude + herramientas (tool runner)
  tools/          gmail, calendar, notion, whatsapp (+ modo demo)
  routines.py     resumen matinal y vigilancia del correo
  server.py       servidor 24 h: web, webhook WhatsApp, programador
  cli.py          chat en terminal
  memory.py       historial y memoria (SQLite)
  web/index.html  interfaz con el «orbe» de Jarvis
```
