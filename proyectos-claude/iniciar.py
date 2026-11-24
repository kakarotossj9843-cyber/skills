"""Arranca las 5 aplicaciones a la vez:  python iniciar.py

Pon tu ANTHROPIC_API_KEY en un archivo .env en esta carpeta (sirve para las cinco) o en el .env de cada proyecto.
Ctrl+C para pararlas todas."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APPS = [
    ("01-jarvis", "jarvis.server:app", 8000, "🤖 Tu propio Jarvis"),
    ("02-segundo-cerebro", "cerebro.server:app", 8001, "🧠 Segundo cerebro"),
    ("03-panel-de-tu-vida", "panel.server:app", 8002, "📊 Panel de tu vida"),
    ("04-agente-de-contenido", "contenido.server:app", 8003, "🌙 Agente de contenido"),
    ("05-equipo-de-agentes", "equipo.server:app", 8004, "👑 Equipo de agentes"),
]


def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.split(" #")[0].strip().strip('"').strip("'")
    return env


def _term(*_):
    raise KeyboardInterrupt


def main() -> None:
    signal.signal(signal.SIGTERM, _term)
    base_env = {**os.environ, **load_env(ROOT / ".env")}
    if not (base_env.get("ANTHROPIC_API_KEY") or all((ROOT / d / ".env").exists() for d, *_ in APPS)):
        print("⚠️  No encuentro ANTHROPIC_API_KEY. Crea proyectos-claude/.env con:  ANTHROPIC_API_KEY=sk-ant-...\n"
              "   (las apps arrancan igual, pero Claude no responderá)\n")
    procs = []
    for folder, app, port, name in APPS:
        log = open(ROOT / folder / "servidor.log", "a", encoding="utf-8")
        procs.append(subprocess.Popen([sys.executable, "-m", "uvicorn", app, "--port", str(port)],
                                      cwd=ROOT / folder, env=base_env, stdout=log, stderr=subprocess.STDOUT))
        print(f"  {name:28} → http://localhost:{port}")
    print("\nLos registros están en servidor.log de cada carpeta. Ctrl+C para parar.")
    try:
        while True:
            time.sleep(2)
            for (folder, _, port, name), p in zip(APPS, procs):
                if p.poll() is not None:
                    print(f"❌ {name} se ha parado (mira {folder}/servidor.log)")
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        for p in procs:
            if p.poll() is None:
                p.send_signal(signal.SIGINT)
        for p in procs:
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
        print("\nTodas paradas. ¡Hasta luego!")


if __name__ == "__main__":
    main()
