$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$runtimeDir = Join-Path $scriptDir "build_runtime"
$tempDir = Join-Path $scriptDir ".pip-temp"
New-Item -ItemType Directory -Force $tempDir | Out-Null
$env:TEMP = $tempDir
$env:TMP = $tempDir
$env:PIP_CACHE_DIR = Join-Path $scriptDir ".pip-cache"

if (!(Test-Path (Join-Path $runtimeDir "PyInstaller"))) {
    Write-Host "Instalando dependencias en una carpeta local..."
    New-Item -ItemType Directory -Force $runtimeDir | Out-Null
    python -m pip install --target $runtimeDir --cache-dir $env:PIP_CACHE_DIR -r requirements.txt pyinstaller
}

Write-Host "Limpiando compilaciones anteriores..."
if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
if (Test-Path ".\dist") { Remove-Item ".\dist" -Recurse -Force }

Write-Host "Generando MouseTextPaster.exe..."
$env:PYTHONPATH = $runtimeDir
python -m PyInstaller --clean --noconfirm ".\mouse_text_paster.spec"

if ((Test-Path ".\mouse_text_paster_config.json") -and (Test-Path ".\dist")) {
    Copy-Item ".\mouse_text_paster_config.json" ".\dist\mouse_text_paster_config.json" -Force
}

Write-Host ""
Write-Host "Listo: $scriptDir\dist\MouseTextPaster.exe"
