# Criar executavel Windows usando PyInstaller, a partir do mesmo motor da V1.7.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
Write-Host '=== ASTRONYX MINI FORGE STUDIO V2.1.0 ===' -ForegroundColor Magenta
$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -c 'import sys; assert sys.version_info >= (3, 10)'
    if ($LASTEXITCODE -eq 0) { $python = @('py', '-3') }
}
if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) {
    & python -c 'import sys; assert sys.version_info >= (3, 10)'
    if ($LASTEXITCODE -eq 0) { $python = @('python') }
}
if (-not $python) { throw 'Python 3.10+ necessario apenas neste PC de COMPILACAO.' }
$exe = $python[0]
$argsPrefix = @()
if ($python.Length -gt 1) { $argsPrefix = @($python[1]) }
& $exe @argsPrefix -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw 'Os testes falharam: a compilacao foi interrompida.' }
& $exe @argsPrefix -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller nao pode ser instalado.' }
& $exe @argsPrefix -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name AstronyxMiniForgeStudio --icon 'assets\astronyx.ico' --add-data 'core\blender_pipeline.py;core' `
    --add-data 'assets;assets' studio.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar executavel.' }
$bin = Join-Path $root 'dist\AstronyxMiniForgeStudio.exe'
if (-not (Test-Path $bin)) { throw 'Executavel nao encontrado ao final da compilacao.' }
Write-Host "Executavel pronto: $bin" -ForegroundColor Green
$exeReport = Join-Path $root 'dist\validation-portable.json'
$process = Start-Process -FilePath $bin -ArgumentList "--self-test `"$exeReport`"" -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path $exeReport)) { throw 'Falha no autoteste do EXE Windows.' }
$validation = Get-Content $exeReport -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $validation.ok -or -not $validation.frozen) { throw 'Recursos ou runtime Tcl ausentes no executavel compilado.' }
Write-Host 'Executavel validado: recursos e Tcl embarcados.' -ForegroundColor Green
$compilers = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
)
$compiler = $compilers | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($compiler) {
    & $compiler (Join-Path $root 'installer\AstronyxMiniForgeStudio.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup retornou erro.' }
    Write-Host 'Instalador criado na pasta dist\installer' -ForegroundColor Green
} else {
    Write-Host 'Para gerar Setup.exe instale Inno Setup 6 e execute novamente.' -ForegroundColor Yellow
    Write-Host 'O executavel portatil .exe foi criado normalmente.' -ForegroundColor Green
}
