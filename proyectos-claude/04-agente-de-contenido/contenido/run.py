"""Ejecuta el trabajo nocturno ahora mismo:  python -m contenido.run
(Útil también para cron:  0 3 * * *  cd /ruta/04-agente-de-contenido && .venv/bin/python -m contenido.run)"""
from __future__ import annotations

import logging

from . import config, pipeline

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"🌙 Agente de contenido · nicho: {config.NICHO} · {config.PLATAFORMA}")
    state = pipeline.run_night()
    for s in state["pasos"]:
        print(f"  {'✅' if s['estado'] == 'hecho' else '❌'} {s['titulo']}: {s['detalle']}")
    print(f"\nResultados en {config.OUT / state['dia']}")
