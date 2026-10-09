# Extract and smoke test the portable ZIP on Windows.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$archive = Join-Path $root 'dist\AstronyxMiniForgeStudio-Portable-v2.2.5-Win10-Win11-x64.zip'
if (-not (Test-Path $archive)) { throw 'ZIP portatil nao encontrado.' }
$destination = Join-Path $env:TEMP ('Astronyx-Portable-Smoke-' + [Guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Expand-Archive -Path $archive -DestinationPath $destination -Force
    $app = Join-Path $destination 'AstronyxMiniForgeStudio\AstronyxMiniForgeStudio.exe'
    $data = Join-Path $destination 'AstronyxMiniForgeStudio\_internal'
    if (-not (Test-Path $app) -or -not (Test-Path $data)) { throw 'ZIP nao contem aplicativo e _internal.' }
    $report = Join-Path $root 'dist\validation-portable-zip.json'
    $process = Start-Process -FilePath $app -ArgumentList ('--self-test "' + $report + '"') -Wait -PassThru
    if ($process.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Aplicativo extraido do ZIP falhou no autoteste.' }
    $verify = Get-Content $report -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $verify.ok -or -not $verify.frozen) { throw 'Autoteste portatil nao confirmou runtime e recursos.' }
    Write-Host 'Versao portatil OK: ZIP, runtime, executavel e Tcl.' -ForegroundColor Green
} finally {
    if (Test-Path $destination) { Remove-Item -LiteralPath $destination -Force -Recurse -ErrorAction SilentlyContinue }
}
