# Startet Docker Desktop und räumt vorher liegengebliebene Unix-Sockets weg.
# Hintergrund: Docker Desktop lässt beim Beenden Socket-Dateien liegen, die Windows nicht löschen kann
# ("The file cannot be accessed by the system"). Beim nächsten Start bricht Docker dann ab.
# Umbenennen der Ordner geht, Docker legt sie neu an. Alte Ordner (*.alt-*) älter als 7 Tage werden entfernt,
# soweit Windows das zulässt.
#
# Aufruf:  pwsh -File tools/docker-starten.ps1

$ErrorActionPreference = 'Stop'
$lokal = $env:LOCALAPPDATA
$ordner = @("$lokal\Docker\run", "$lokal\docker-secrets-engine")

if (Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue) {
    docker version --format '{{.Server.Version}}' 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host 'Docker läuft bereits.'; exit 0 }
    Write-Host 'Docker Desktop hängt – wird beendet.'
    Get-Process | Where-Object { $_.Name -like '*docker*' } | Stop-Process -Force
    Start-Sleep 3
}

$stempel = Get-Date -Format 'yyyyMMdd-HHmmss'
foreach ($o in $ordner) {
    if (Test-Path $o) {
        Rename-Item $o "$(Split-Path $o -Leaf).alt-$stempel"
        Write-Host "aufgeräumt: $o"
    }
}
foreach ($basis in "$lokal\Docker", $lokal) {
    Get-ChildItem $basis -Directory -Filter '*.alt-*' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
        ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
}

Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
Write-Host 'Docker Desktop gestartet, warte auf die Engine …'
for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep 4
    $v = docker version --format '{{.Server.Version}}' 2>$null
    if ($LASTEXITCODE -eq 0 -and $v) { Write-Host "Docker-Engine läuft (Version $v)."; exit 0 }
}
Write-Host 'Docker-Engine nach 3 Minuten nicht erreichbar. Fehler:'
Get-Content "$lokal\Docker\backend.error.json" -ErrorAction SilentlyContinue
exit 1
