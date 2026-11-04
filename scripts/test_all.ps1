$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& ./.venv/Scripts/python.exe -m ruff check backend src scripts tests
if ($LASTEXITCODE) { throw 'Ruff failed' }
& ./.venv/Scripts/python.exe -m pytest -q
if ($LASTEXITCODE) { throw 'pytest failed' }
Push-Location frontend
try {
    npm.cmd test
    if ($LASTEXITCODE) { throw 'Frontend tests failed' }
    npm.cmd run build
    if ($LASTEXITCODE) { throw 'Frontend build failed' }
} finally { Pop-Location }
