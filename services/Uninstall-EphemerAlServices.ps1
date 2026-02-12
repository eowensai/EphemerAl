#Requires -RunAsAdministrator

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$services = @('OllamaService', 'TikaService', 'EphemerAlApp')

function Write-Step {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

$nssmCommand = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmCommand) {
    Write-Fail "NSSM is not installed or not on PATH. Cannot uninstall NSSM-managed services."
    exit 1
}

foreach ($name in $services) {
    try {
        Write-Step "Stopping $name (if running)..."
        # nssm stop: requests service stop through NSSM.
        & nssm stop $name 2>$null | Out-Null
    } catch {
        # Ignore stop errors for services that are not present or already stopped.
    }

    try {
        Write-Step "Removing $name..."
        # nssm remove confirm: deletes the Windows service registration without prompt.
        & nssm remove $name confirm 2>$null | Out-Null
        Write-Ok "$name removed."
    } catch {
        Write-Fail "Failed to remove $name: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "Uninstall complete."
