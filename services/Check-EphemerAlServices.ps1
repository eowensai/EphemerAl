Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$services = @('OllamaService', 'TikaService', 'EphemerAlApp')
$endpoints = @(
    @{ Name = 'Ollama'; Url = 'http://127.0.0.1:11434' },
    @{ Name = 'Tika'; Url = 'http://127.0.0.1:9998' },
    @{ Name = 'EphemerAl'; Url = 'http://127.0.0.1:8501' }
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

Write-Host ''
Write-Step 'Streamlit listener check (port 8501):'
try {
    $streamlitListeners = Get-NetTCPConnection -State Listen -LocalPort 8501 -ErrorAction Stop |
        Select-Object LocalAddress, LocalPort, OwningProcess |
        Sort-Object LocalAddress -Unique

    if ($streamlitListeners) {
        foreach ($listener in $streamlitListeners) {
            $proc = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
            $procName = if ($proc) { $proc.ProcessName } else { 'unknown' }
            Write-Ok "Listening on $($listener.LocalAddress):$($listener.LocalPort) (PID $($listener.OwningProcess), Process $procName)"
        }

        $hasLocalOnly = $streamlitListeners | Where-Object { $_.LocalAddress -eq '127.0.0.1' -or $_.LocalAddress -eq '::1' }
        $hasNetworkBind = $streamlitListeners | Where-Object { $_.LocalAddress -eq '0.0.0.0' -or $_.LocalAddress -eq '::' }

        if ($hasLocalOnly -and -not $hasNetworkBind) {
            Write-Fail 'Streamlit appears to be bound only to localhost. Remote access will fail even if firewall rules are open.'
            Write-Host 'To fix, reinstall services so EphemerAlApp uses --server.address=0.0.0.0 or set address="0.0.0.0" in C:\EphemerAl\.streamlit\config.toml.'
        } else {
            Write-Ok 'Streamlit is listening on a network-accessible address.'
        }
    } else {
        Write-Fail 'No process is listening on TCP port 8501.'
    }
} catch {
    Write-Fail "Could not query listeners with Get-NetTCPConnection: $($_.Exception.Message)"
    Write-Host 'Fallback check command:'
    Write-Host '  netstat -ano | findstr :8501'
}
