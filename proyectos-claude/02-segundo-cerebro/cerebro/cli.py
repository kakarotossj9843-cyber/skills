"""Segundo cerebro en la terminal.

  python -m cerebro.cli                      chat (pregunta o cuéntale cosas)
  python -m cerebro.cli capturar "texto"     archiva una idea rápida
  python -m cerebro.cli importar ARCHIVO...  archiva archivos .md / .txt
  python -m cerebro.cli bandeja              procesa la carpeta 00-Bandeja
  python -m cerebro.cli conoceme             entrevista inicial para crear tu perfil
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import agent, vault


def chat(first: str | None = None) -> None:
    history: list[dict] = []
    print(f"🧠 Segundo cerebro ({len(vault.all_notes())} notas en {vault.VAULT}). /salir para terminar.\n")
    if first:
        print("Cerebro ›", first, "\n")
        history += [{"role": "user", "content": "Entrevístame para crear mi perfil."},
                    {"role": "assistant", "content": first}]
    while True:
        try:
            q = input("Tú › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not q:
            continue
        if q in ("/salir", "/exit"):
            return
        a = agent.ask(q, history[-20:])
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
        print("Cerebro ›", a, "\n")


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else ""
    if cmd == "capturar":
        print(agent.capture(" ".join(args[1:]) or sys.stdin.read()))
    elif cmd == "importar":
        for f in args[1:]:
            p = Path(f)
            print(f"📄 {p.name}:", agent.capture(p.read_text(encoding="utf-8", errors="replace"), source=p.name))
    elif cmd == "bandeja":
        print(agent.process_inbox())
    elif cmd == "conoceme":
        chat(agent.interview())
    else:
        chat()


if __name__ == "__main__":
    main()
