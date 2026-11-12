"""Kommandozeile.

    python -m app.cli dienst              Weboberfläche starten (Dauerbetrieb im Container)
    python -m app.cli abruf 123456789     Mods eines Spielers abrufen und Kurzübersicht ausgeben (Test)
"""
import argparse
import logging
import os
import sys
import threading
import time
from logging.handlers import RotatingFileHandler

from app import config


def logging_einrichten() -> None:
    handler: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        config.LOGDATEI.parent.mkdir(parents=True, exist_ok=True)
        handler.append(RotatingFileHandler(config.LOGDATEI, maxBytes=1_000_000, backupCount=3, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=handler)


def versionswaechter() -> None:
    """Beendet den Prozess, sobald das Sync-Skript eine neue VERSION geschrieben hat.
    Docker startet den Container dann neu (restart: unless-stopped)."""
    version = config.programmversion()
    while True:
        time.sleep(60)
        neu = config.programmversion()
        if neu != version:
            logging.info("Neue Programmversion %s – Neustart", neu or "unbekannt")
            os._exit(0)


def dienst() -> int:
    import uvicorn
    logging.info("Programmversion: %s, Comlink: %s, Port %d",
                 config.programmversion() or "unbekannt", config.COMLINK_URL, config.PORT)
    threading.Thread(target=versionswaechter, daemon=True).start()
    uvicorn.run("app.web:app", host="0.0.0.0", port=config.PORT, log_level="warning")
    return 0


def abruf(ally_code: str) -> int:
    from app import comlink, mods
    spieler = mods.spieler_lesen(comlink.spieler(comlink.ally_code_normalisieren(ally_code)))
    print(f"{spieler['name']}: {len(spieler['einheiten'])} Charaktere mit Mods, "
          f"{sum(len(e['mods']) for e in spieler['einheiten'].values())} Mods")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    unter = parser.add_subparsers(dest="befehl", required=True)
    unter.add_parser("dienst")
    a = unter.add_parser("abruf")
    a.add_argument("ally_code")
    args = parser.parse_args()
    logging_einrichten()
    if args.befehl == "dienst":
        return dienst()
    return abruf(args.ally_code)


if __name__ == "__main__":
    sys.exit(main())
