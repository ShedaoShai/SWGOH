"""SQLite-Speicher: letzter Abruf je Ally-Code und Snapshots."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS abrufe (
    ally_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    abgerufen TEXT NOT NULL,
    daten TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ally_code TEXT NOT NULL,
    name TEXT NOT NULL,
    notiz TEXT NOT NULL DEFAULT '',
    erstellt TEXT NOT NULL,
    anzahl_einheiten INTEGER NOT NULL,
    anzahl_mods INTEGER NOT NULL,
    daten TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS snapshots_ally ON snapshots(ally_code);
CREATE TABLE IF NOT EXISTS namen (schluessel TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta (schluessel TEXT PRIMARY KEY, wert TEXT NOT NULL);
"""


def verbinden(pfad: Path | None = None) -> sqlite3.Connection:
    pfad = Path(pfad or config.DATENBANK)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(pfad)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def jetzt() -> str:
    return datetime.now().isoformat(timespec="seconds")


def abruf_speichern(con, spieler: dict) -> str:
    zeit = jetzt()
    con.execute(
        "INSERT INTO abrufe(ally_code, name, abgerufen, daten) VALUES (?,?,?,?) "
        "ON CONFLICT(ally_code) DO UPDATE SET name=excluded.name, abgerufen=excluded.abgerufen, daten=excluded.daten",
        (spieler["ally_code"], spieler["name"], zeit, json.dumps(spieler, ensure_ascii=False)),
    )
    con.commit()
    return zeit


def abruf_laden(con, ally_code: str) -> dict | None:
    zeile = con.execute("SELECT abgerufen, daten FROM abrufe WHERE ally_code=?", (ally_code,)).fetchone()
    if not zeile:
        return None
    spieler = json.loads(zeile["daten"])
    spieler["abgerufen"] = zeile["abgerufen"]
    return spieler


def snapshot_anlegen(con, ally_code: str, name: str, notiz: str, einheiten: dict) -> int:
    anzahl_mods = sum(len(e["mods"]) for e in einheiten.values())
    cur = con.execute(
        "INSERT INTO snapshots(ally_code, name, notiz, erstellt, anzahl_einheiten, anzahl_mods, daten) "
        "VALUES (?,?,?,?,?,?,?)",
        (ally_code, name, notiz, jetzt(), len(einheiten), anzahl_mods, json.dumps(einheiten, ensure_ascii=False)),
    )
    con.commit()
    return cur.lastrowid


def _kopf(zeile) -> dict:
    return {k: zeile[k] for k in ("id", "ally_code", "name", "notiz", "erstellt", "anzahl_einheiten", "anzahl_mods")}


def snapshots_liste(con, ally_code: str) -> list[dict]:
    zeilen = con.execute(
        "SELECT id, ally_code, name, notiz, erstellt, anzahl_einheiten, anzahl_mods FROM snapshots "
        "WHERE ally_code=? ORDER BY erstellt DESC, id DESC", (ally_code,)
    ).fetchall()
    return [_kopf(z) for z in zeilen]


def snapshot_laden(con, snapshot_id: int) -> dict | None:
    zeile = con.execute("SELECT * FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
    if not zeile:
        return None
    return {**_kopf(zeile), "einheiten": json.loads(zeile["daten"])}


def snapshot_aendern(con, snapshot_id: int, name: str, notiz: str) -> bool:
    cur = con.execute("UPDATE snapshots SET name=?, notiz=? WHERE id=?", (name, notiz, snapshot_id))
    con.commit()
    return cur.rowcount > 0


def snapshot_loeschen(con, snapshot_id: int) -> bool:
    cur = con.execute("DELETE FROM snapshots WHERE id=?", (snapshot_id,))
    con.commit()
    return cur.rowcount > 0
