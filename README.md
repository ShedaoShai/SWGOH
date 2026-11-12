# SWGoH Mod-Snapshots

Eigene Weboberfläche für Star Wars: Galaxy of Heroes. Sie liest die ausgerüsteten Mods eines Accounts über [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink), speichert sie als Snapshots und zeigt beim Wiederherstellen eine Umbau-Liste: welche Mod von welchem Charakter wohin wandert.

**Abgrenzung:** Das Tool liest nur öffentliche Spielerdaten. Es verändert nichts im Spiel. Das Umrüsten machst du selbst in der App, anhand der Liste. Ein automatisches Ausrüsten ist bewusst nicht eingebaut, weil es gegen die Nutzungsbedingungen von EA/CG verstößt und den Account gefährdet.

## Funktionen
- Ally-Code in der Oberfläche eingeben (wird nicht fest gespeichert, auf Wunsch nur im Browser gemerkt)
- Aktuelle Mods aller Charaktere ansehen und suchen, mit deutschen Namen aus der Spiel-Übersetzung
- Filter nach Fraktion, Rolle und Seite; „Angezeigte auswählen“ übernimmt alle gefilterten Charaktere in die Auswahl
- Mod-Bilder aus den Original-Spielgrafiken (Silberrahmen bei 5 Punkten, Goldrahmen bei 6; Kontur und Set-Symbol in der Stufenfarbe E grau … A gold); fehlen die Grafiken, zeigt die Oberfläche eigene Zeichnungen
- Gesamttempo je Charakter: Grundtempo + angelegte Ausrüstung + Mods + Tempo-Set (5 % bzw. 10 % bei Level 15); Aufschlüsselung per Klick auf den Wert
- Set-Boni je Charakter: vollständige Sets (grün; „½“ = noch nicht alle Mods auf Level 15) und übrige Mods ohne Bonus
- Snapshot aller Charaktere oder einer Auswahl speichern, mit Name und Notiz; umbenennen und löschen
- **Wiederherstellen:** Vergleich Snapshot ↔ aktueller Stand
  - je Charakter und Slot: passt / umsetzen (von wem) / nicht gefunden
  - Warnung, wenn Charaktere außerhalb des Snapshots Mods verlieren
  - geschätzte Credits für das Ausbauen
  - Schritte abhaken, danach mit „Neu abrufen & prüfen“ kontrollieren

**Grenze:** Über Comlink sind nur ausgerüstete Mods sichtbar. Mods im Inventar erscheinen als „nicht gefunden“.

## Aufbau
| Pfad | Inhalt |
|---|---|
| `app/comlink.py` | Zugriff auf Comlink (`/player`, `/metadata`, `/localization`) |
| `app/mods.py` | Rohdaten → schlanke Mod-Struktur (Set, Slot, Punkte, Werte) |
| `app/namen.py` | deutsche Charakternamen (einmal je Spielversion geladen) |
| `app/vergleich.py` | Umbau-Liste aus Snapshot und aktuellem Stand |
| `app/kategorien.py`, `app/daten/kategorien.json` | Fraktionen/Rollen/Seite je Charakter |
| `tools/kategorien_erzeugen.py` | erzeugt `kategorien.json` am PC aus den Spieldaten (lokaler Comlink) |
| `tools/docker-starten.ps1` | Docker Desktop starten und liegengebliebene Sockets wegräumen |
| `app/db.py` | SQLite: letzter Abruf je Ally-Code, Snapshots, Namen |
| `app/web.py` | FastAPI: JSON-API und Startseite |
| `app/static/` | Oberfläche (HTML/CSS/JS ohne Framework) |
| `deploy/nas/` | Portainer-Stack und Sync-Skript, siehe [DEPLOY.md](DEPLOY.md) |
| `deploy/lokal/` | Comlink für die Entwicklung am PC (Port 3200) |

## Entwicklung am PC
```powershell
docker compose -f deploy/lokal/docker-compose.yml up -d
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m app.cli dienst          # http://localhost:8099
```
Umgebungsvariablen: `COMLINK_URL` (Standard `http://localhost:3200`), `SWGOH_DATENBANK`, `SWGOH_PORT` (8099).

### Fraktionen aktualisieren (bei neuen Charakteren)
Die Spieldaten sind ca. 90 MB groß; Comlink bräuchte dafür auf der NAS bis zu 700 MB Speicher. Deshalb wird die kleine Datei `app/daten/kategorien.json` am PC erzeugt und mit dem Programm synchronisiert:
```powershell
python tools/kategorien_erzeugen.py
pwsh -File deploy/nas/sync-to-nas.ps1
```
Charaktere, die neuer sind als die Datei, stehen im Filter unter „ohne Zuordnung“.

### Charakterbilder
Die Porträts kommen aus dem Spiel über [swgoh-ae2](https://github.com/swgoh-utils/swgoh-ae2) (lokal am PC) und liegen in `app/static/bilder/` (ca. 6 MB, per `.gitignore` aus jedem Repo ausgeschlossen). Bei neuen Charakteren nach `kategorien_erzeugen.py`:
```powershell
docker start swgoh-ae2-lokal   # beim ersten Mal: docker run -d --name swgoh-ae2-lokal -p 3201:8080 ghcr.io/swgoh-utils/swgoh-ae2:latest
python tools/bilder_laden.py    # lädt nur fehlende Bilder
docker stop swgoh-ae2-lokal
```
**Die Bilder gehören EA/Lucasfilm:** nur privat im Heimnetz nutzen, nicht veröffentlichen.
### Mod-Grafiken
Rahmen, Konturen und Set-Symbole liegen im Spiel in Grafik-Atlanten des Pakets `shared_uicontainer`. swgoh-ae2 kann sie nicht einzeln ausgeben (Fehler 500), lädt das Paket dabei aber herunter. Das Skript kopiert es aus dem Container und zerlegt es mit UnityPy (in einem `python:3.13-slim`-Container) nach `app/static/mods/` (ca. 100 KB, ebenfalls per `.gitignore` ausgeschlossen):
```powershell
docker start swgoh-ae2-lokal
pwsh -File tools/mod_grafiken_laden.ps1
docker stop swgoh-ae2-lokal
```
Nur nötig, wenn das Spiel die Mod-Grafiken ändert. Gleiche Regel wie bei den Porträts: nur privat nutzen.

### Docker Desktop startet nicht („The file cannot be accessed by the system“)
Docker Desktop lässt beim Beenden Unix-Socket-Dateien liegen, die Windows nicht löschen kann; der nächste Start bricht dann ab. Docker deshalb über das Skript starten, es räumt die Reste vorher weg:
```powershell
pwsh -File tools/docker-starten.ps1
```
