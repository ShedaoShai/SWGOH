"""Deutsche Charakternamen aus der Übersetzungsdatei des Spiels (über Comlink, einmal je Spielversion)."""
import logging
import re
import threading

from app import comlink

log = logging.getLogger(__name__)

# Spielbare Charaktere, deren Namensschlüssel nicht UNIT_<id>_NAME lautet
SONDERFAELLE = {"VEERS": "UNIT_VEERS_GENERAL_NAME", "R2D2_LEGENDARY": "UNIT_R2D2_NAME"}
SPRACHE = "GER_DE"

_sperre = threading.Lock()
_namen: dict[str, str] = {}


def _bereinigen(text: str) -> str:
    """Formatierungen wie [c][FFFFFF]…[-][/c] entfernen."""
    return re.sub(r"\[[^\]]*\]", "", text).strip()


def laden(con) -> None:
    """Namen aus der Datenbank in den Speicher holen."""
    global _namen
    _namen = {z["schluessel"]: z["name"] for z in con.execute("SELECT schluessel, name FROM namen")}


def aktualisieren(con) -> bool:
    """Lädt die Übersetzungsdatei, wenn es eine neue Spielversion gibt. True bei Änderung."""
    with _sperre:
        version = comlink.metadaten()["latestLocalizationBundleVersion"]
        alt = con.execute("SELECT wert FROM meta WHERE schluessel='namen_version'").fetchone()
        if alt and alt["wert"] == version and _namen:
            return False
        dateien = comlink.uebersetzung(f"{version}:{SPRACHE}")
        text = dateien.get(f"Loc_{SPRACHE}.txt", "")
        neu = {}
        for zeile in text.splitlines():
            if zeile.startswith("UNIT_") and "|" in zeile:
                schluessel, name = zeile.split("|", 1)
                if schluessel.endswith("_NAME"):
                    neu[schluessel] = _bereinigen(name)
        if not neu:
            raise RuntimeError("Übersetzungsdatei ohne Charakternamen")
        con.execute("DELETE FROM namen")
        con.executemany("INSERT INTO namen(schluessel, name) VALUES (?,?)", neu.items())
        con.execute("INSERT INTO meta(schluessel, wert) VALUES ('namen_version', ?) "
                    "ON CONFLICT(schluessel) DO UPDATE SET wert=excluded.wert", (version,))
        con.commit()
        laden(con)
        log.info("%d Charakternamen geladen (Version %s)", len(neu), version)
        return True


def name(basis_id: str) -> str:
    schluessel = SONDERFAELLE.get(basis_id, f"UNIT_{basis_id}_NAME")
    return _namen.get(schluessel) or basis_id.replace("_", " ").title()
