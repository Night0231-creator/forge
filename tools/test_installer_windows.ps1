# Requires Windows + Inno Setup-generated installer. Smoke-test installation
# and the embedded Tcl/assets from the installed application.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$setup = Join-Path $root 'dist\installer\AstronyxMiniForgeStudio-Setup-v2.0.1.exe'
if (-not (Test-Path $setup)) { throw 'Instalador nao foi gerado.' }
$destination = Join-Path $env:TEMP 'Astronyx-Installer-Test-2_0_1'
$log = Join-Path $root 'dist\installer-smoke.log'
$process = Start-Process -FilePath $setup -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$destination`"", "/LOG=`"$log`"") -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Instalador falhou: exit $($process.ExitCode). Consulte $log" }
$installed = Join-Path $destination 'AstronyxMiniForgeStudio.exe'
if (-not (Test-Path $installed)) { throw 'EXE nao foi instalado no diretorio de teste.' }
$report = Join-Path $root 'dist\validation-installer.json'
$process = Start-Process -FilePath $installed -ArgumentList "--self-test `"$report`"" -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Autoteste do executavel instalado falhou.' }
$verification = Get-Content $report -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $verification.ok -or -not $verification.frozen) { throw 'Autoteste do instalador nao validou todos os recursos.' }
Write-Host 'Instalador smoke-test OK: instalacao, EXE empacotado, Tcl e assets.' -ForegroundColor Green
