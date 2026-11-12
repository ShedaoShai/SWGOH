"""Lädt die Charakterbilder (Porträts) nach app/static/bilder/ – nur fehlende, also schnell bei Updates.

Quelle: swgoh-ae2 (Community-Werkzeug, lädt Grafiken von den Spiel-Servern), lokal am PC per Docker:
    docker run -d --name swgoh-ae2-lokal -p 3201:8080 ghcr.io/swgoh-utils/swgoh-ae2:latest
Welche Grafik zu welchem Charakter gehört, steht in app/daten/kategorien.json (tools/kategorien_erzeugen.py).

Die Bilder gehören EA/Lucasfilm: nur privat nutzen (Heimnetz), nicht veröffentlichen, nicht in ein Repo einchecken.

    python tools/bilder_laden.py [--ae2 http://localhost:3201]
"""
import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent
DATEN = PROJEKT / "app" / "daten" / "kategorien.json"
ZIEL = PROJEKT / "app" / "static" / "bilder"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ae2", default="http://localhost:3201")
    url = p.parse_args().ae2.rstrip("/")

    daten = json.loads(DATEN.read_text(encoding="utf-8"))
    version = daten.get("asset_version")
    if not version:
        raise SystemExit("asset_version fehlt – zuerst tools/kategorien_erzeugen.py ausführen")
    ZIEL.mkdir(parents=True, exist_ok=True)

    neu, fehler = 0, []
    pakete = sorted(set(daten["bilder"].values()))
    for paket in pakete:
        datei = ZIEL / f"{paket}.png"
        if datei.exists():
            continue
        try:
            with urllib.request.urlopen(f"{url}/Asset/single?assetName={paket}&version={version}", timeout=180) as r:
                inhalt = r.read()
        except (urllib.error.URLError, TimeoutError) as e:
            fehler.append(f"{paket}: {e}")
            continue
        if not inhalt.startswith(b"\x89PNG"):
            fehler.append(f"{paket}: keine PNG-Datei")
            continue
        datei.write_bytes(inhalt)
        neu += 1
    groesse = sum(f.stat().st_size for f in ZIEL.glob("*.png")) // 1024
    print(f"{neu} neu geladen, {len(pakete) - neu - len(fehler)} schon vorhanden, {len(fehler)} Fehler "
          f"({groesse} KB in {ZIEL})")
    for f in fehler[:20]:
        print("  ", f)


if __name__ == "__main__":
    main()
