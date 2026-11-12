"""Einstellungen ausschließlich über Umgebungsvariablen (Stack-Datei). Kein Ally-Code in der Konfiguration."""
import os
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent

COMLINK_URL = os.environ.get("COMLINK_URL", "http://localhost:3200").rstrip("/")
DATENBANK = Path(os.environ.get("SWGOH_DATENBANK", PROJEKT / "data" / "swgoh.db"))
LOGDATEI = Path(os.environ.get("SWGOH_LOG", DATENBANK.parent / "swgoh.log"))
PORT = int(os.environ.get("SWGOH_PORT", "8099"))
VERSION_DATEI = PROJEKT / "VERSION"


def programmversion() -> str:
    """Inhalt von VERSION (schreibt das Sync-Skript als letzte Datei), sonst leer."""
    try:
        return VERSION_DATEI.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
