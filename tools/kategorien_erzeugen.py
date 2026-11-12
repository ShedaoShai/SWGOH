"""Erzeugt app/daten/kategorien.json aus den Spieldaten: Fraktionen, Rollen, Seite und Grundtempo je Charakter
sowie das Tempo der Ausrüstungsteile.

Läuft am PC gegen den lokalen Comlink (deploy/lokal), nicht auf der NAS: Die Spieldaten sind ca. 90 MB groß,
Comlink braucht dafür bis zu 700 MB Speicher. Die erzeugte Datei ist klein und wird mit dem Programm synchronisiert.

    python tools/kategorien_erzeugen.py [--comlink http://localhost:3200]
"""
import argparse
import json
import re
import urllib.request
from datetime import date
from pathlib import Path

ZIEL = Path(__file__).resolve().parent.parent / "app" / "daten" / "kategorien.json"

# Sichtbare Kategorien, die als Filter keinen Sinn ergeben
AUSLASSEN = {"eventonly", "shipclass_cargoship", "role_capital", "character_fleetcommander"}
SEITEN = {"alignment_light": "Helle Seite", "alignment_dark": "Dunkle Seite", "alignment_neutral": "Neutral"}


def post(url: str, pfad: str, nutzlast: dict) -> dict:
    anfrage = urllib.request.Request(url + pfad, data=json.dumps(nutzlast).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(anfrage, timeout=600) as antwort:
        return json.loads(antwort.read())


def gruppe(kid: str) -> str:
    if kid.startswith("role_"):
        return "Rolle"
    if kid.startswith("alignment_"):
        return "Seite"
    return "Fraktion"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--comlink", default="http://localhost:3200")
    url = p.parse_args().comlink.rstrip("/")

    meta = post(url, "/metadata", {})
    version = meta["latestGamedataVersion"]
    lokal = post(url, "/localization", {"payload": {"id": meta["latestLocalizationBundleVersion"] + ":GER_DE"},
                                        "unzip": True})["Loc_GER_DE.txt"]
    texte = dict(z.split("|", 1) for z in lokal.splitlines() if "|" in z and not z.startswith("#"))

    def daten(segment: int) -> dict:
        return post(url, "/data", {"payload": {"version": version, "includePveUnits": False,
                                               "requestSegment": segment}, "enums": False})

    segment1 = daten(1)
    kategorien = {}
    for k in segment1["category"]:
        if k.get("visible") and k["id"] not in AUSLASSEN:
            name = re.sub(r"\[[^\]]*\]", "", texte.get(k.get("descKey", ""), k["id"])).strip()
            kategorien[k["id"]] = {"name": name, "gruppe": gruppe(k["id"])}
    for kid, name in SEITEN.items():
        kategorien[kid] = {"name": name, "gruppe": "Seite"}

    def tempo(stats: list[dict]) -> int:
        return sum(int(s["unscaledDecimalValue"]) for s in stats if s["unitStatId"] == 5) // 10**8

    einheiten, grundtempo, bilder = {}, {}, {}
    for u in daten(3)["units"]:
        if u.get("combatType") != 1 or not u.get("obtainable") or u["baseId"] in grundtempo:
            continue
        ids = sorted(k for k in u.get("categoryId", []) if k in kategorien)
        if ids:
            einheiten[u["baseId"]] = ids
        # Tempo je Ausrüstungsstufe (enthält die Teile der niedrigeren Stufen; Sterne und Relikte ändern es nicht)
        grundtempo[u["baseId"]] = {str(t["tier"]): tempo(t["baseStat"]["stat"]) for t in u.get("unitTier", [])}
        # Porträt: thumbnailName 'tex.charui_vader' -> Grafikpaket 'charui_vader' (lädt tools/bilder_laden.py)
        if u.get("thumbnailName", "").startswith("tex."):
            bilder[u["baseId"]] = u["thumbnailName"][4:]

    ausruestung = {}
    for e in segment1["equipment"]:
        wert = tempo((e.get("equipmentStat") or {}).get("stat", []))
        if wert:
            ausruestung[e["id"]] = wert

    benutzt = {k for ids in einheiten.values() for k in ids}
    ergebnis = {
        "spielversion": version,
        "erzeugt": date.today().isoformat(),
        "kategorien": {k: v for k, v in sorted(kategorien.items()) if k in benutzt},
        "einheiten": dict(sorted(einheiten.items())),
        "grundtempo": dict(sorted(grundtempo.items())),
        "ausruestung_tempo": dict(sorted(ausruestung.items())),
        "bilder": dict(sorted(bilder.items())),
        "asset_version": meta.get("assetVersion"),
    }
    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ZIEL.write_text(json.dumps(ergebnis, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(einheiten)} Charaktere, {len(ergebnis['kategorien'])} Kategorien, {len(grundtempo)} Grundtempi, "
          f"{len(ausruestung)} Ausrüstungsteile mit Tempo -> {ZIEL} "
          f"({ZIEL.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
