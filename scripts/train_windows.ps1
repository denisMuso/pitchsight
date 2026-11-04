param([string]$Dataset = '', [switch]$Smoke, [string]$Config = '', [string]$Resume = '', [string]$Output = '')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (!$Smoke -and !$Dataset) { throw 'Provide -Dataset for authorized SoccerNet data, or -Smoke for engineering tests' }
if (!$Config) { if ($Smoke) { $Config = 'configs/smoke.json' } else { $Config = 'configs/rtx3060.json' } }
$trainingArgs = @('-m', 'pitchsight.training.run', '--config', $Config)
if ($Smoke) { $trainingArgs += '--smoke' } else { $trainingArgs += @('--dataset', $Dataset) }
if ($Resume) { $trainingArgs += @('--resume', $Resume) }
if ($Output) { $trainingArgs += @('--output', $Output) }
& ./.venv/Scripts/python.exe @trainingArgs
exit $LASTEXITCODE
