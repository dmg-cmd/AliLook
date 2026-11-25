<#
.SYNOPSIS
Incrementa la versión del proyecto siguiendo el estándar decimal base-10 (Mayor.Medio.Inferior)
y sincroniza VERSION, config.py, README.md, docs/MANUAL_USUARIO.md y docs/HISTORIAL.md.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Descripcion
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$archivoVersion = Join-Path $raiz "VERSION"

if (-not (Test-Path $archivoVersion)) {
    throw "No se encontró el archivo VERSION en $raiz"
}

$actual = (Get-Content $archivoVersion -Raw).Trim()
$partes = $actual.Split(".")
if ($partes.Count -ne 3) {
    throw "Formato de versión inválido: '$actual'. Se esperaba Mayor.Medio.Inferior"
}

[int]$mayor = $partes[0]
[int]$medio = $partes[1]
[int]$inferior = $partes[2]

$inferior += 1
if ($inferior -ge 10) {
    $inferior = 0
    $medio += 1
    if ($medio -ge 10) {
        $medio = 0
        $mayor += 1
    }
}

$nuevaVersion = "$mayor.$medio.$inferior"
Set-Content -Path $archivoVersion -Value $nuevaVersion -Encoding UTF8

# Sincronizar backend/app/core/config.py
$configPath = Join-Path $raiz "backend\app\core\config.py"
if (Test-Path $configPath) {
    (Get-Content $configPath -Raw) -replace 'APP_VERSION = "[^"]+"', "APP_VERSION = `"$nuevaVersion`"" |
        Set-Content $configPath -Encoding UTF8 -NoNewline
}

# Sincronizar README.md y docs/MANUAL_USUARIO.md
foreach ($rel in @("README.md", "docs\MANUAL_USUARIO.md")) {
    $p = Join-Path $raiz $rel
    if (Test-Path $p) {
        (Get-Content $p -Raw) -replace [regex]::Escape($actual), $nuevaVersion |
            Set-Content $p -Encoding UTF8 -NoNewline
    }
}

# Agregar entrada en docs/HISTORIAL.md
$historialPath = Join-Path $raiz "docs\HISTORIAL.md"
if (Test-Path $historialPath) {
    $fecha = Get-Date -Format "yyyy-MM-dd"
    $entrada = "`n## [$nuevaVersion] - $fecha`n### Cambios`n* $Descripcion`n"
    Add-Content -Path $historialPath -Value $entrada -Encoding UTF8
}

Write-Output "Versión actualizada: $actual -> $nuevaVersion"
