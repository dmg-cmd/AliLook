<#
.SYNOPSIS
Menú interactivo para elegir la IP/interfaz de red y levantar el servidor FastAPI.
#>
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Proyecto Ali - Servidor Probador Virtual (VTO)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (Test-Path $adb) {
    Write-Host "[USB] Configurando puente ADB (tcp:8000 -> tcp:8000)..." -ForegroundColor DarkGray
    & $adb -d reverse tcp:8000 tcp:8000 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[USB] Puente activo: en el celular puedes usar http://127.0.0.1:8000" -ForegroundColor Green
    } else {
        Write-Host "[USB] No se detecto celular USB activo (puedes usar Wi-Fi)." -ForegroundColor Yellow
    }
    Write-Host ""
}

$interfaces = @(
    Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object InterfaceAlias, IPAddress
)

Write-Host "Elige en que direccion IP quieres escuchar:" -ForegroundColor White
Write-Host "  [0] Todas las interfaces (0.0.0.0) [Recomendado]"
for ($i = 0; $i -lt $interfaces.Count; $i++) {
    $num = $i + 1
    $item = $interfaces[$i]
    Write-Host "  [$num] $($item.IPAddress)  ($($item.InterfaceAlias))"
}
Write-Host ""

$seleccion = Read-Host "Ingresa el numero (Enter = 0)"
if ([string]::IsNullOrWhiteSpace($seleccion) -or $seleccion -eq "0") {
    $hostElegido = "0.0.0.0"
} elseif ($seleccion -match '^\d+$' -and [int]$seleccion -ge 1 -and [int]$seleccion -le $interfaces.Count) {
    $hostElegido = $interfaces[[int]$seleccion - 1].IPAddress
} else {
    Write-Host "Opcion invalida, usando 0.0.0.0..." -ForegroundColor Yellow
    $hostElegido = "0.0.0.0"
}

Write-Host ""
if ($hostElegido -eq "0.0.0.0") {
    Write-Host "Servidor escuchando en todas las interfaces (puerto 8000)." -ForegroundColor Green
    foreach ($item in $interfaces) {
        Write-Host "  -> En la app Android ($($item.InterfaceAlias)): http://$($item.IPAddress):8000" -ForegroundColor Cyan
    }
} else {
    Write-Host "Servidor escuchando en: http://${hostElegido}:8000" -ForegroundColor Green
}
Write-Host "Presiona Ctrl+C para detener el servidor." -ForegroundColor DarkGray
Write-Host ""

$env:VTO_HOST_ANUNCIADO = $hostElegido
$uvicorn = Join-Path $raiz ".venv\Scripts\uvicorn.exe"
Set-Location (Join-Path $raiz "backend")
& $uvicorn app.main:app --host $hostElegido --port 8000
