param([switch]$ML)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (!(Test-Path '.venv/Scripts/python.exe')) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE) { throw 'Python 3.12 virtual environment creation failed' }
}
& ./.venv/Scripts/python.exe -m pip install -e '.[dev]'
if ($LASTEXITCODE) { throw 'Dependency installation failed' }
if ($ML) {
    & ./.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu132
    if ($LASTEXITCODE) { throw 'CUDA wheel installation failed; consult official PyTorch selector' }
    & ./.venv/Scripts/python.exe -m pip install -e '.[ml]'
    if ($LASTEXITCODE) { throw 'ML dependencies failed' }
}
Push-Location frontend
try { npm.cmd ci; if ($LASTEXITCODE) { throw 'npm installation failed' } } finally { Pop-Location }
& ./.venv/Scripts/python.exe -m pitchsight.cli seed-demo
if ($LASTEXITCODE) { throw 'Database initialization failed' }
& ./.venv/Scripts/python.exe scripts/doctor.py
