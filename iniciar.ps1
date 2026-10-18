$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$stePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $stePython)) {
    throw 'No se encuentra el entorno .venv. Sigue la instalación del README.md.'
}
& $stePython -m streamlit run (Join-Path $PSScriptRoot 'app.py')
exit $LASTEXITCODE
