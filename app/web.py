"""Weboberfläche und JSON-API.

Der Ally-Code steht nirgends in der Konfiguration: Er wird in der Oberfläche eingegeben (und nur im Browser
gemerkt) und bei jeder Anfrage mitgeschickt. In der Datenbank sind Abrufe und Snapshots dem Ally-Code
zugeordnet, damit mehrere Accounts getrennt bleiben.
"""
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import comlink, config, db, kategorien, mods, namen, vergleich

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"


def _namen_aktualisieren() -> None:
    con = db.verbinden()
    try:
        namen.aktualisieren(con)
    except Exception as e:
        log.warning("Charakternamen konnten nicht geladen werden: %s", e)
    finally:
        con.close()


@asynccontextmanager
async def lebenszyklus(_app):
    con = db.verbinden()
    namen.laden(con)
    con.close()
    threading.Thread(target=_namen_aktualisieren, daemon=True).start()
    yield


app = FastAPI(title="SWGoH Mod-Snapshots", lifespan=lebenszyklus)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _ally(text: str) -> str:
    try:
        return comlink.ally_code_normalisieren(text)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


def _mit_namen(einheiten: dict) -> list[dict]:
    liste = [{**e, "name": namen.name(eid), "sets": mods.set_boni(e["mods"]), "bild": kategorien.bild(eid),
              "tempo": mods.tempo_gesamt(e["mods"], kategorien.grundtempo(eid, e.get("ausruestung")),
                                         kategorien.ausruestung_tempo(e.get("teile", []))),
              "kategorien": kategorien.von(eid)} for eid, e in einheiten.items()]
    return sorted(liste, key=lambda e: e["name"].lower())


def _spieler_antwort(spieler: dict) -> dict:
    return {
        "name": spieler["name"],
        "ally_code": spieler["ally_code"],
        "abgerufen": spieler.get("abgerufen"),
        "einheiten": _mit_namen(spieler["einheiten"]),
        "anzahl_mods": sum(len(e["mods"]) for e in spieler["einheiten"].values()),
    }


@app.exception_handler(comlink.ComlinkFehler)
async def comlink_fehler(_req, e: comlink.ComlinkFehler):
    return JSONResponse({"detail": str(e)}, status_code=502)


@app.get("/", response_class=HTMLResponse)
def startseite():
    # Versionskennung an CSS/JS hängen, damit der Browser nach einem Update nichts Veraltetes aus dem Cache nimmt
    kennung = str(max(int(p.stat().st_mtime) for p in STATIC.iterdir()))
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = html.replace("/static/style.css", f"/static/style.css?v={kennung}").replace(
        "/static/app.js", f"/static/app.js?v={kennung}")
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


@app.get("/api/status")
def status():
    return {"version": config.programmversion(), "comlink": comlink.erreichbar()}


@app.get("/api/kategorien")
def kategorien_liste():
    return kategorien.alle()


@app.post("/api/spieler/{ally_code}/abrufen")
def abrufen(ally_code: str):
    ally = _ally(ally_code)
    spieler = mods.spieler_lesen(comlink.spieler(ally))
    spieler["ally_code"] = spieler["ally_code"] or ally
    con = db.verbinden()
    try:
        spieler["abgerufen"] = db.abruf_speichern(con, spieler)
    finally:
        con.close()
    return _spieler_antwort(spieler)


@app.get("/api/spieler/{ally_code}")
def letzter_abruf(ally_code: str):
    con = db.verbinden()
    try:
        spieler = db.abruf_laden(con, _ally(ally_code))
    finally:
        con.close()
    if not spieler:
        raise HTTPException(404, "Noch kein Abruf für diesen Ally-Code")
    return _spieler_antwort(spieler)


class NeuerSnapshot(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    notiz: str = Field(default="", max_length=1000)
    einheiten: list[str] | None = None  # None = alle Charaktere mit Mods


class SnapshotAenderung(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    notiz: str = Field(default="", max_length=1000)


@app.get("/api/spieler/{ally_code}/snapshots")
def snapshots(ally_code: str):
    con = db.verbinden()
    try:
        return db.snapshots_liste(con, _ally(ally_code))
    finally:
        con.close()


@app.post("/api/spieler/{ally_code}/snapshots")
def snapshot_erstellen(ally_code: str, daten: NeuerSnapshot):
    """Snapshot aus dem letzten Abruf (die Oberfläche ruft vorher neu ab)."""
    ally = _ally(ally_code)
    con = db.verbinden()
    try:
        spieler = db.abruf_laden(con, ally)
        if not spieler:
            raise HTTPException(409, "Bitte zuerst die Mods abrufen")
        einheiten = spieler["einheiten"]
        if daten.einheiten is not None:
            einheiten = {k: v for k, v in einheiten.items() if k in set(daten.einheiten)}
        if not einheiten:
            raise HTTPException(400, "Keine Charaktere mit Mods ausgewählt")
        sid = db.snapshot_anlegen(con, ally, daten.name.strip(), daten.notiz.strip(), einheiten)
        return db.snapshot_laden(con, sid) | {"einheiten": None}
    finally:
        con.close()


def _snapshot(con, snapshot_id: int) -> dict:
    s = db.snapshot_laden(con, snapshot_id)
    if not s:
        raise HTTPException(404, "Snapshot nicht gefunden")
    return s


@app.get("/api/snapshots/{snapshot_id}")
def snapshot(snapshot_id: int):
    con = db.verbinden()
    try:
        s = _snapshot(con, snapshot_id)
    finally:
        con.close()
    return s | {"einheiten": _mit_namen(s["einheiten"])}


@app.put("/api/snapshots/{snapshot_id}")
def snapshot_aendern(snapshot_id: int, daten: SnapshotAenderung):
    con = db.verbinden()
    try:
        if not db.snapshot_aendern(con, snapshot_id, daten.name.strip(), daten.notiz.strip()):
            raise HTTPException(404, "Snapshot nicht gefunden")
    finally:
        con.close()
    return {"ok": True}


@app.delete("/api/snapshots/{snapshot_id}")
def snapshot_loeschen(snapshot_id: int):
    con = db.verbinden()
    try:
        if not db.snapshot_loeschen(con, snapshot_id):
            raise HTTPException(404, "Snapshot nicht gefunden")
    finally:
        con.close()
    return {"ok": True}


@app.get("/api/snapshots/{snapshot_id}/vergleich")
def snapshot_vergleich(snapshot_id: int):
    """Vergleich mit dem letzten Abruf (die Oberfläche ruft vorher neu ab)."""
    con = db.verbinden()
    try:
        s = _snapshot(con, snapshot_id)
        spieler = db.abruf_laden(con, s["ally_code"])
    finally:
        con.close()
    if not spieler:
        raise HTTPException(409, "Bitte zuerst die Mods abrufen")
    ergebnis = vergleich.vergleichen(s["einheiten"], spieler["einheiten"])
    for z in ergebnis["ziele"]:
        z["name"] = namen.name(z["id"])
        z["bild"] = kategorien.bild(z["id"])
        for schritt in z["schritte"]:
            if schritt["von"]:
                schritt["von_name"] = namen.name(schritt["von"])
    for v in ergebnis["verlierer"]:
        v["name"] = namen.name(v["id"])
        for m in v["mods"]:
            m["an_name"] = namen.name(m["an"])
    ergebnis["ziele"].sort(key=lambda z: (z["offen"] == 0, z["name"].lower()))
    return ergebnis | {"snapshot": {k: s[k] for k in ("id", "name", "erstellt")}, "abgerufen": spieler["abgerufen"]}
