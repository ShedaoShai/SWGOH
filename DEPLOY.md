# SWGoH Mod-Snapshots auf der NAS (DS423+, Portainer CE)

Gleiches Muster wie AktienHelper, MyWeather und Flashy: kein eigenes Image, sondern `python:3.13-slim` mit dem Programm von der Freigabe. Dazu kommt Comlink als zweiter Container im selben Stack.

## Aufbau
- Stack-Datei: `deploy/nas/docker-compose.yml` (in Portainer als Stack **swgoh**)
  - `SWGoH-Comlink`: `ghcr.io/swgoh-utils/swgoh-comlink`, liest öffentliche Spielerdaten, nur im Stack erreichbar
  - `SWGoH-Mods`: Weboberfläche und API
- Dateien auf der NAS: `/volume2/docker/swgoh/` (= `\\DS423plus\docker\swgoh`)
  - `app/` Programm und `VERSION` (kopiert `deploy/nas/sync-to-nas.ps1`)
  - `data/` Datenbank `swgoh.db` (Snapshots, letzter Abruf, Charakternamen) und Log `swgoh.log`. **Das ist der wichtige Teil fürs Backup.**
  - `venv/` installierte Python-Pakete (wird beim ersten Start angelegt)
- Weboberfläche: `http://192.168.178.34:8099` (nur Heimnetz/VPN, keine Portfreigabe im Router)
- Der Ally-Code steht nirgends in der Konfiguration. Er wird in der Oberfläche eingegeben und auf Wunsch nur im Browser gemerkt.

## Einmalige Einrichtung
1. Im Projektordner das Sync-Skript ausführen. Es legt die Ordner auf der NAS an und kopiert das Programm:
   ```powershell
   pwsh -File deploy/nas/sync-to-nas.ps1
   ```
2. Portainer → *Stacks* → *Add stack*, Name `swgoh`, *Web editor*.
3. Inhalt von `deploy/nas/docker-compose.yml` einfügen.
4. *Deploy the stack*.

Beim ersten Start dauert es 1–2 Minuten (Comlink-Image laden, Python-Pakete installieren). Die deutschen Charakternamen lädt der Dienst im Hintergrund nach. Bis dahin stehen interne Kürzel wie `VADER` da.

## Updates
```powershell
pwsh -File deploy/nas/sync-to-nas.ps1
```
Der laufende Dienst prüft jede Minute die Datei `VERSION`, beendet sich bei einer Änderung und wird von Docker neu gestartet. In Portainer ist nichts zu tun.

Nur wenn sich `deploy/nas/docker-compose.yml` ändert: Portainer → *Stacks* → *swgoh* → *Editor*, neuen Inhalt einfügen, *Update the stack*.

Comlink selbst aktualisieren (nötig, wenn das Spiel die Schnittstelle ändert und Abrufe fehlschlagen): Portainer → *Stacks* → *swgoh* → *Update the stack* mit *Re-pull image*.

## Prüfen
- Oberfläche: unten links stehen Version und ggf. „Comlink nicht erreichbar“
- Log: `\\DS423plus\docker\swgoh\data\swgoh.log` oder Portainer → *Containers* → *SWGoH-Mods* → *Logs*
- Erwartet beim Start: `Programmversion: …, Comlink: http://swgoh-comlink:3000, Port 8099` und kurz darauf `… Charakternamen geladen`
