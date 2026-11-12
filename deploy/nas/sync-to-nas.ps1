# Kopiert das Programm auf die NAS nach /volume2/docker/swgoh/app.
# Voraussetzung: Die Freigabe \\DS423plus\docker ist erreichbar.
# Aufruf (im Projektordner):  pwsh -File deploy/nas/sync-to-nas.ps1
# Ein Neustart in Portainer ist nicht nötig: Der laufende Dienst erkennt die neue VERSION-Datei
# innerhalb einer Minute, beendet sich und wird von Docker neu gestartet.

param([string]$Target = '\\DS423plus\docker\swgoh')

$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$app = Join-Path $Target 'app'

# Ordner über die Freigabe anlegen, damit sie dem NAS-Benutzer gehören (Container läuft als 1026:100)
foreach ($dir in 'app', 'data', 'venv') {
    New-Item -ItemType Directory -Force (Join-Path $Target $dir) | Out-Null
}

# Programm spiegeln (veraltete Dateien im Ziel werden entfernt); VERSION bleibt bis zum Schluss stehen
robocopy (Join-Path $root 'app') (Join-Path $app 'app') /MIR /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy app fehlgeschlagen (Code $LASTEXITCODE)" }
Copy-Item (Join-Path $root 'requirements.txt') $app -Force

# VERSION als letzte Datei schreiben: Der Dienst startet erst neu, wenn alles kopiert ist
$commit = 'lokal'
if (Test-Path (Join-Path $root '.git')) {
    $commit = git -C $root rev-parse --short HEAD 2>$null
    if (-not $commit) { $commit = 'ohne-commit' }
    elseif (git -C $root status --porcelain) { $commit += '-geaendert' }
}
$version = "$commit $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
[IO.File]::WriteAllText((Join-Path $app 'VERSION'), $version)

Write-Host "Fertig: Version $version liegt in $app"
Write-Host "Log: $(Join-Path $Target 'data\swgoh.log')"
