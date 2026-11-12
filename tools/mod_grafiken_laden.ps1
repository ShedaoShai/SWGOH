# Lädt die Original-Mod-Grafiken (Rahmen, Konturen, Set-Symbole) nach app/static/mods/.
# Voraussetzung: Docker läuft (tools/docker-starten.ps1) und swgoh-ae2 lokal:
#   docker start swgoh-ae2-lokal
# Ablauf: swgoh-ae2 holt das Spiel-Paket shared_uicontainer (die Anfrage selbst endet mit Fehler 500,
# weil ae2 Atlanten nicht ausgeben kann, das Paket liegt danach aber im Container). Es wird herauskopiert
# und mit UnityPy in einem python:3.13-Container zerlegt (tools/mod_grafiken_entpacken.py).
# Die Grafiken gehören EA/Lucasfilm: nur privat nutzen, nicht veröffentlichen, nicht ins Repo.
param([string]$Ae2 = "http://localhost:3201", [string]$Container = "swgoh-ae2-lokal")
$ErrorActionPreference = "Stop"
$projekt = Split-Path $PSScriptRoot -Parent
$version = (Get-Content "$projekt\app\daten\kategorien.json" -Raw | ConvertFrom-Json).asset_version
if (-not $version) { throw "asset_version fehlt – zuerst tools/kategorien_erzeugen.py ausführen" }

$paket = "shared_uicontainer"
Write-Host "Lade $paket (Asset-Version $version) über swgoh-ae2 …"
try { Invoke-WebRequest "$Ae2/Asset/single?assetName=$paket&version=$version" -TimeoutSec 600 -UseBasicParsing | Out-Null }
catch { }  # 500 ist hier normal, siehe oben

$arbeit = Join-Path ([IO.Path]::GetTempPath()) "swgoh-modgrafik"
New-Item -ItemType Directory -Force $arbeit | Out-Null
docker exec $Container sh -c "cp `"/app/\\AssetBundles\\/tmp/$paket.bundle`" /tmp/$paket.bundle"
if ($LASTEXITCODE) { throw "Paket $paket nicht im Container gefunden – läuft swgoh-ae2?" }
docker cp "${Container}:/tmp/$paket.bundle" "$arbeit\$paket.bundle"
if ($LASTEXITCODE) { throw "Kopieren aus dem Container fehlgeschlagen" }

$ziel = "$projekt\app\static\mods"
docker run --rm -v "${arbeit}:/b:ro" -v "${PSScriptRoot}:/w:ro" -v "${ziel}:/z" python:3.13-slim `
  sh -c "pip install -q --root-user-action=ignore --disable-pip-version-check UnityPy pillow && python /w/mod_grafiken_entpacken.py /b/$paket.bundle /z $version"
if ($LASTEXITCODE) { throw "Entpacken fehlgeschlagen" }
Remove-Item -Recurse -Force $arbeit
