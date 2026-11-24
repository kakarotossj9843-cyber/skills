"""Usar el equipo desde la terminal:  python -m equipo "Crea una landing para mi curso de IA" """
from __future__ import annotations

import sys
import threading
import time

from . import team
from .job import Job

NAMES = {"jefe": "👑 El jefe", "busca": "🔎 Busca", "escribe": "✍️ Escribe", "disena": "🎨 Diseña", "revisa": "✅ Revisa"}


def main() -> None:
    encargo = " ".join(sys.argv[1:]).strip() or input("¿Qué necesitas? › ").strip()
    if not encargo:
        raise SystemExit("Escribe un encargo.")
    job = Job(encargo)
    t = threading.Thread(target=team.run_job, args=(job,))
    t.start()
    seen = 0
    while t.is_alive() or seen < len(job.data["eventos"]):
        evs = job.data["eventos"][seen:]
        for e in evs:
            print(f"{NAMES.get(e['agente'], e['agente'])} · {e['texto'][:300]}")
        seen += len(evs)
        time.sleep(0.5)
    t.join()
    print(f"\n{'✅' if job.data['estado'] == 'hecho' else '❌'} {job.data.get('resumen') or job.data.get('error')}")
    print(f"Archivos en {job.files}:")
    for f in job.data["entregables"]:
        print("  -", f)


if __name__ == "__main__":
    main()
