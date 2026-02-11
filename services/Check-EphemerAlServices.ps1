Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$services = @('OllamaService', 'TikaService', 'EphemerAlApp')
$endpoints = @(
    @{ Name = 'Ollama'; Url = 'http://localhost:11434' },
    @{ Name = 'Tika'; Url = 'http://localhost:9998' },
    @{ Name = 'EphemerAl'; Url = 'http://localhost:8501' }
)

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

Write-Step 'Service status:'
foreach ($name in $services) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -eq 'Running') {
            Write-Ok "$name is Running"
        } else {
            Write-Fail "$name is $($svc.Status)"
        }
    } else {
        Write-Fail "$name is not installed"
    }
}

Write-Host ''
Write-Step 'HTTP health checks:'
foreach ($ep in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri $ep.Url -Method Get -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            Write-Ok "$($ep.Name) endpoint reachable: $($ep.Url) (HTTP $($response.StatusCode))"
        } else {
            Write-Fail "$($ep.Name) endpoint returned HTTP $($response.StatusCode): $($ep.Url)"
        }
    } catch {
        Write-Fail "$($ep.Name) endpoint check failed: $($ep.Url) - $($_.Exception.Message)"
    }
}
