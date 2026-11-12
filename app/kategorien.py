"""Fraktionen, Rollen und Seite je Charakter aus app/daten/kategorien.json (erzeugt von tools/kategorien_erzeugen.py)."""
import json
import logging
from functools import lru_cache
from pathlib import Path

DATEI = Path(__file__).parent / "daten" / "kategorien.json"
log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _daten() -> dict:
    try:
        return json.loads(DATEI.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        log.warning("Kategorien nicht lesbar (%s) – Fraktionsfilter leer", e)
        return {"kategorien": {}, "einheiten": {}}


def von(basis_id: str) -> list[str]:
    return _daten()["einheiten"].get(basis_id, [])


def grundtempo(basis_id: str, stufe: int | None) -> int | None:
    """Tempo des Charakters auf seiner Ausrüstungsstufe, None wenn unbekannt."""
    stufen = _daten().get("grundtempo", {}).get(basis_id)
    if not stufen or stufe is None:
        return None
    return stufen.get(str(stufe))


def ausruestung_tempo(teile: list[str]) -> int:
    werte = _daten().get("ausruestung_tempo", {})
    return sum(werte.get(t, 0) for t in teile)


BILDER = Path(__file__).parent / "static" / "bilder"


def bild(basis_id: str) -> str | None:
    """URL des Porträts, None wenn (noch) nicht geladen (tools/bilder_laden.py)."""
    paket = _daten().get("bilder", {}).get(basis_id)
    if paket and (BILDER / f"{paket}.png").exists():
        return f"/static/bilder/{paket}.png"
    return None


def alle() -> dict:
    d = _daten()
    return {"kategorien": d["kategorien"], "stand": d.get("erzeugt"), "spielversion": d.get("spielversion")}
