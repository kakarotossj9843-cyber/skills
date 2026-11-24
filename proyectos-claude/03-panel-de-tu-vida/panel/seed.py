"""Rellena el panel con datos de ejemplo realistas:  python -m panel.seed   (--borrar para empezar de cero)"""
from __future__ import annotations

import random
import sys
from datetime import timedelta

from . import db

CLIENTES = ["Marta López", "Carlos Ruiz", "Lucía Gómez", "Estudio Norte", "Pablo Díaz", "Ana Torres", "Grupo Sol",
            "Javier Moreno", "Clínica Vida", "Elena Martín", "Bar La Esquina", "Sara Vidal", "Hugo Sanz", "Nerea Gil",
            "Óscar Blanco", "Laura Prieto", "Tienda Verde", "Iván Castro", "Raquel León", "Diego Ortega", "Marina Paz",
            "Academia Uno", "Rubén Ríos", "Alba Cano", "Gimnasio Fit", "Teresa Rey", "Mario Vega", "Noelia Soto"]


def main() -> None:
    if "--borrar" in sys.argv and db.DB_FILE.exists():
        db.DB_FILE.unlink()
    random.seed(7)
    t = db.today()
    start = t - timedelta(days=364)

    for i, name in enumerate(CLIENTES):
        since = start + timedelta(days=int(i * 340 / len(CLIENTES)) + random.randint(0, 10))
        db.add_client(name, min(since, t).isoformat())
    db.set_client_active("Grupo Sol", False)

    d = start
    while d <= t:
        growth = 0.55 + 0.45 * (d - start).days / 364
        for _ in range(random.choice([0, 0, 1, 1, 1, 2])):
            db.add_sale(round(random.uniform(180, 900) * growth, 2), random.choice(CLIENTES[:max(3, int(len(CLIENTES) * growth))]),
                        random.choice(["Web", "Consultoría", "Mantenimiento", "Formación", "Diseño"]), d.isoformat())
        if d.day == 1:
            db.add_money("ingreso", 2800, "Sueldo autónomo", "Negocio", d.isoformat())
            db.add_money("gasto", 850, "Alquiler", "Casa", d.isoformat())
            db.add_money("gasto", 59.9, "Gimnasio + apps", "Suscripciones", d.isoformat())
        if d.day == 15:
            db.add_money("ingreso", round(random.uniform(400, 1400) * growth, 2), "Extra proyectos", "Negocio", d.isoformat())
        if random.random() < 0.5:
            db.add_money("gasto", round(random.uniform(8, 60), 2), random.choice(["Súper", "Restaurante", "Gasolina", "Cine"]),
                         random.choice(["Comida", "Ocio", "Transporte"]), d.isoformat())
        d += timedelta(days=1)

    for h in ["Gimnasio", "Leer 20 min", "Dormir 8 h"]:
        db.add_habit(h)
    for hid, p in [(1, 0.6), (2, 0.75), (3, 0.5)]:
        for k in range(1, 84):
            if random.random() < p + 0.25 * (84 - k) / 84:
                db.set_habit(hid, True, (t - timedelta(days=k)).isoformat())
    db.set_habit(1, True)

    for title in ["Enviar presupuesto", "Grabar vídeo", "Llamar a Marta", "Preparar factura de noviembre"]:
        db.add_task(title)
    db.set_task(1, True)
    print(f"✅ Datos de ejemplo cargados en {db.DB_FILE}")


if __name__ == "__main__":
    main()
