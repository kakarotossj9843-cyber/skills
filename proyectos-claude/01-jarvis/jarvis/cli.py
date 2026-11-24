"""Chat con Jarvis en la terminal:  python -m jarvis.cli
Comandos: /estado  /resumen  /correo  /olvidar  /salir"""
from __future__ import annotations

from . import agent, config, memory, routines


def main() -> None:
    print("🤖 Jarvis listo. Integraciones:",
          ", ".join(f"{k} {'✅' if v else '⚪ demo'}" for k, v in config.status().items()))
    print("Comandos: /estado /resumen /correo /olvidar /salir\n")
    while True:
        try:
            text = input("Tú › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text in ("/salir", "/exit"):
            break
        if text == "/estado":
            print(config.status())
            continue
        if text == "/olvidar":
            memory.clear("cli")
            print("Historial borrado.")
            continue
        if text == "/resumen":
            print("Jarvis ›", routines.morning_brief(), "\n")
            continue
        if text == "/correo":
            print("Jarvis ›", routines.check_inbox() or "Nada importante nuevo.", "\n")
            continue
        print("Jarvis ›", agent.ask(text, chat="cli"), "\n")


if __name__ == "__main__":
    main()
