# Projekt: SWGoH Mod-Snapshots

## Arbeitsweise
- Kommunikation auf Deutsch.
- Betriebs- und Aufwandsfragen (Updates, manuelle Schritte, Konten) vor neuen Technikvorschlägen klären. Der Nutzer will möglichst wenig Handarbeit.
- Keine erfundenen Fakten: Comlink-Felder und Spielmechaniken an echten Daten prüfen.

## Ziel und Grenzen
Mods eines SWGoH-Accounts von außerhalb des Spiels ansehen, als Snapshots speichern und eine Umbau-Liste zum Wiederherstellen erzeugen.
- **Nur lesen.** Kein automatisches Ausrüsten, keine Nutzung der privaten Spiel-API mit Login-Token, keine Bot-Steuerung: Das verstößt gegen die Nutzungsbedingungen von EA/CG und gefährdet den Account. Der Nutzer hat HotUtils (kostenpflichtig, CG-Partner) bewusst abgelehnt.
- **Ally-Codes** (eigene und fremde) dürfen nie im Quellcode, in Konfiguration, Tests, Beispieldaten, Doku oder sonst irgendwo im Repo landen. Eingabe nur in der Oberfläche. Laufzeitdaten mit Ally-Codes (Datenbank, Exporte) sind per `.gitignore` ausgeschlossen; vor jedem Commit auf 9-stellige Ziffernfolgen prüfen. Tests nutzen offensichtliche Platzhalter (z. B. `123456789`). Der Hook `tools/git-hooks/pre-commit` sperrt 9-stellige Zahlen (Ausnahmen in `erlaubte-zahlen.txt`); nach neuem Klonen einmal `git config core.hooksPath tools/git-hooks` ausführen.
- Repo: privat, https://github.com/ShedaoShai/SWGOH (Branch `main`).

## Technik
- Python 3.13 (Container), FastAPI + uvicorn, SQLite, Oberfläche ohne Framework (`app/static`).
- Datenquelle: swgoh-comlink. Werte kommen als `unscaledDecimalValue` (× 1e8, Prozentwerte als Anteil). Mod-`definitionId` = Set, Punkte, Slot (geprüft am 12.11.2026 mit echten Daten).
- Deutsche Namen: `/localization` mit `<bundle>:GER_DE`, Schlüssel `UNIT_<baseId>_NAME`, Sonderfälle in `app/namen.py`. Die 89 MB große `/data`-Abfrage bewusst vermieden.
- Gesamttempo = Grundtempo der Ausrüstungsstufe (`unitTier.baseStat`, enthält Teile der niedrigeren Stufen) + angelegte Teile der aktuellen Stufe + Tempo aus Mods + Tempo-Set (5 %, bei allen 4 Mods auf Level 15 10 % vom Grundtempo, abgerundet; aus `statModSet` 4). Relikte und Sterne ändern das Tempo nicht. Vom Nutzer am 12.11.2026 im Spiel bestätigt.
- Fraktionen/Rollen/Seite und Grundtempo: `app/daten/kategorien.json`, erzeugt am PC mit `tools/kategorien_erzeugen.py` (die `/data`-Abfrage braucht in Comlink bis zu 700 MB, zu viel für die NAS). Bei Updates nach neuen Charakteren neu erzeugen.
- Mod-Bilder: Original-Spielgrafiken aus dem Paket `shared_uicontainer` (NGUI-Atlanten `charactermods_datacard_atlas`: `modchip_<form>_base/_6dot/_light`, `pip`; `misc_atlas`: `icon_buff_*`, `icon_tenacity`). ae2 liefert dafür 500, lädt das Paket aber in `/app/\AssetBundles\/tmp/`; `tools/mod_grafiken_laden.ps1` kopiert es heraus und zerlegt es mit UnityPy im python:3.13-Container (UnityPy baut nicht unter Python 3.15) nach `app/static/mods/` (privat, `.gitignore`). Kontur und Symbol sind weiß und werden per CSS-Maske in der Stufenfarbe (`tier`) eingefärbt, wie im Spiel. Farbe = Stufe, nicht Level (an echten Daten geprüft: Level-12-Mod mit Stufe E). Symbol-Lage: Das Spiel zentriert nicht, sondern zeichnet das Symbol mit Original-Leerraum (128er-Sprite, `voll`/`versatz` in mods.json) in ein festes Kästchen je Form. `SPIEL_KAESTCHEN` in app.js wird je Form aus Spiel-Screenshots kalibriert (Overlay mit Differenz-Mischung, am Silberrahmen ausgerichtet; Quadrat und Pfeil am 12.11.2026, Größe pixelgenau gemessen – nicht aus herunterskalierten Screenshots schätzen). Formen ohne Kalibrierung: Flächenschwerpunkt des schwarzen Felds plus `MOD_KORREKTUR` (Randabstand-Messung). Vom Nutzer am 12.11.2026 gewünscht.
- Ersatz ohne Originalgrafiken: eigene SVG-Zeichnungen in Spieloptik (Metallkörper, Rahmen-Verlauf je Stufe aus `#mod-defs` in index.html, leuchtendes Set-Symbol, Pip-Punkte; 6-Punkte-Mods weiße Punkte). swgoh.gg-Grafiken bewusst nicht verwendet: deren Nutzungsbedingungen (Abschnitt 11 und 16) verbieten automatisches Laden und Nutzung außerhalb der Seite.
- Charakterbilder: Original-Porträts per swgoh-ae2 (`tools/bilder_laden.py`, lokal Port 3201, Asset-Version aus Comlink-Metadaten) nach `app/static/bilder/`. Vom Nutzer genehmigt (Weg A: bei Updates am PC nachladen). Nur privat, nie veröffentlichen, nicht ins Repo (`.gitignore`).
- Update-Ablauf bei neuen Charakteren: `docker-starten.ps1` → Comlink und ae2 lokal starten → `kategorien_erzeugen.py` → `bilder_laden.py` → (bei geänderten Mod-Grafiken `mod_grafiken_laden.ps1`) → `sync-to-nas.ps1`.
- Docker am PC immer über `tools/docker-starten.ps1` starten (räumt liegengebliebene Sockets weg).
- Deployment wie AktienHelper: `python:3.13-slim` mit Programm von `\\DS423plus\docker\swgoh`, Stack `swgoh` per Portainer-Web-Editor, Updates über `deploy/nas/sync-to-nas.ps1` (Neustart über `VERSION`). Port **8099**. Details in DEPLOY.md.
