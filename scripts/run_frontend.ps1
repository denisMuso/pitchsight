$ErrorActionPreference = 'Stop'
Set-Location (Join-Path (Split-Path $PSScriptRoot -Parent) 'frontend')
npm.cmd run dev -- --port 5173 --strictPort
exit $LASTEXITCODE
