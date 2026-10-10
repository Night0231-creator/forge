# Portable Windows distribution: use a ZIP rather than an Inno Setup temporary installer.
# One-dir PyInstaller avoids extracting the Python runtime as a temporary executable.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python nao encontrado na compilacao.' }
& python -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller indisponivel no interpretador de build.' }
& python -m PyInstaller --noconfirm --clean --noupx --onedir --contents-directory '_internal' --windowed --name AstronyxMiniForgeStudio --icon 'assets\astronyx.ico' --version-file 'installer\windows_version_info.txt' --add-data 'core\blender_pipeline.py;core' --add-data 'core\obj_vertex_budget.py;core' --add-data 'assets;assets' --distpath 'dist\portablebuild' --workpath 'build\portable' studio.py
if ($LASTEXITCODE -ne 0) { throw 'Falha na compilacao portatil.' }
$folder = Join-Path $root 'dist\portablebuild\AstronyxMiniForgeStudio'
$exe = Join-Path $folder 'AstronyxMiniForgeStudio.exe'
if (-not (Test-Path $exe) -or -not (Test-Path (Join-Path $folder '_internal'))) { throw 'Pacote portatil incompleto.' }
$report = Join-Path $root 'dist\validation-portable-onedir.json'
$process = Start-Process -FilePath $exe -ArgumentList ('--self-test "' + $report + '"') -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Autoteste da distribuicao portatil falhou.' }
$validation = Get-Content $report -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $validation.ok -or -not $validation.frozen) { throw 'Pacote portatil sem recursos embarcados.' }
$archive = Join-Path $root 'dist\AstronyxMiniForgeStudio-Portable-v2.2.9-Win10-Win11-x64.zip'
if (Test-Path $archive) { Remove-Item $archive -Force }
Compress-Archive -Path $folder -DestinationPath $archive -CompressionLevel Optimal -Force
if (-not (Test-Path $archive)) { throw 'ZIP portatil nao foi criado.' }
Write-Host "Distribuicao portatil pronta: $archive" -ForegroundColor Green
