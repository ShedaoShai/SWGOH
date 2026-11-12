"""Zugriff auf swgoh-comlink (läuft als eigener Container im selben Stack).

Comlink liest nur öffentliche Spielerdaten. Es wird nichts im Spiel verändert.
"""
import json
import re
import urllib.error
import urllib.request

from app import config


class ComlinkFehler(Exception):
    pass


def ally_code_normalisieren(text: str) -> str:
    """'123-456-789' oder '123 456 789' -> '123456789'. Wirft ValueError bei ungültiger Eingabe."""
    ziffern = re.sub(r"[\s-]", "", text or "")
    if not re.fullmatch(r"\d{9}", ziffern):
        raise ValueError("Ally-Code muss aus 9 Ziffern bestehen (z. B. 123-456-789)")
    return ziffern


def _post(pfad: str, nutzlast: dict, timeout: float = 60) -> dict:
    anfrage = urllib.request.Request(
        f"{config.COMLINK_URL}{pfad}",
        data=json.dumps(nutzlast).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            return json.loads(antwort.read())
    except urllib.error.HTTPError as e:
        text = e.read().decode(errors="replace")[:300]
        if e.code in (400, 404) or "not found" in text.lower():
            raise ComlinkFehler(f"Spieler nicht gefunden oder Anfrage ungültig ({e.code}): {text}") from e
        raise ComlinkFehler(f"Comlink antwortet mit Fehler {e.code}: {text}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ComlinkFehler(f"Comlink nicht erreichbar unter {config.COMLINK_URL}: {e}") from e


def spieler(ally_code: str) -> dict:
    """Rohdaten des Spielers (inkl. rosterUnit mit equippedStatMod)."""
    return _post("/player", {"payload": {"allyCode": ally_code}, "enums": False})


def metadaten() -> dict:
    return _post("/metadata", {})


def uebersetzung(bundle_id: str) -> dict:
    """{'Loc_GER_DE.txt': '...'} – ca. 15 MB"""
    return _post("/localization", {"payload": {"id": bundle_id}, "unzip": True}, timeout=180)


def erreichbar() -> bool:
    try:
        with urllib.request.urlopen(f"{config.COMLINK_URL}/readyz", timeout=5) as antwort:
            return antwort.status == 200
    except Exception:
        return False
