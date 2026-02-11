#Requires -RunAsAdministrator

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

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

function Install-ServiceWithNssm {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$AppPath,
        [Parameter(Mandatory = $true)][string]$AppArgs,
        [string]$AppDirectory,
        [string]$AppEnvironmentExtra
    )

    try {
        # Remove any existing service first so install is idempotent.
        & nssm remove $Name confirm 2>$null | Out-Null
    } catch {
        # Ignore cleanup failures for non-existent services.
    }

    # nssm install: registers the Windows service with executable path and arguments.
    & nssm install $Name $AppPath $AppArgs | Out-Null

    if ($AppDirectory) {
        # AppDirectory: working directory used when NSSM launches the process.
        & nssm set $Name AppDirectory $AppDirectory | Out-Null
    }

    if ($AppEnvironmentExtra) {
        # AppEnvironmentExtra: environment variables injected into the service process.
        & nssm set $Name AppEnvironmentExtra $AppEnvironmentExtra | Out-Null
    }

    # Start: configures startup type. SERVICE_AUTO_START means start automatically at boot.
    & nssm set $Name Start SERVICE_AUTO_START | Out-Null
}

Write-Step "Checking NSSM availability..."
$nssmCommand = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssmCommand) {
    Write-Fail "NSSM is not installed or not on PATH."
    Write-Host "Install NSSM and add it to PATH, then rerun this script."
    Write-Host "Download: https://nssm.cc/download"
    exit 1
}
Write-Ok "NSSM found: $($nssmCommand.Source)"

Write-Step "Locating Python executable for Streamlit service..."
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    Write-Fail "Python is not on PATH. Install Python and ensure 'python' is available in PATH."
    exit 1
}
$pythonExe = $pythonCommand.Source
Write-Ok "Python found: $pythonExe"

$ollamaEnv = @(
    'OLLAMA_HOST=0.0.0.0'
    'OLLAMA_ORIGINS=*'
    'OLLAMA_MAX_LOADED_MODELS=1'
    'OLLAMA_FLASH_ATTENTION=1'
    'OLLAMA_KEEP_ALIVE=-1'
    'OLLAMA_MODELS=C:\Ollama\models'
) -join "`n"

$tikaEnv = 'JAVA_TOOL_OPTIONS=-Xmx2g -Xms512m'

$appEnv = @(
    'LLM_BASE_URL=http://localhost:11434/v1'
    'LLM_MODEL_NAME=gemma3-prod'
    'TIKA_URL=http://localhost:9998'
    'TIKA_CLIENT_ONLY=true'
) -join "`n"

$services = @(
    @{
        Name = 'OllamaService'
        AppPath = 'C:\Ollama\ollama.exe'
        AppArgs = 'serve'
        AppDirectory = 'C:\Ollama'
        AppEnvironmentExtra = $ollamaEnv
    },
    @{
        Name = 'TikaService'
        AppPath = 'java'
        AppArgs = '-jar C:\Tika\tika-server-standard.jar --host 0.0.0.0 --port 9998'
        AppDirectory = 'C:\Tika'
        AppEnvironmentExtra = $tikaEnv
    },
    @{
        Name = 'EphemerAlApp'
        AppPath = $pythonExe
        AppArgs = '-m streamlit run C:\EphemerAl\ephemeral_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true'
        AppDirectory = 'C:\EphemerAl'
        AppEnvironmentExtra = $appEnv
    }
)

$installResults = @{}
foreach ($svc in $services) {
    try {
        Write-Step "Installing $($svc.Name)..."
        Install-ServiceWithNssm -Name $svc.Name -AppPath $svc.AppPath -AppArgs $svc.AppArgs -AppDirectory $svc.AppDirectory -AppEnvironmentExtra $svc.AppEnvironmentExtra
        $installResults[$svc.Name] = $true
        Write-Ok "$($svc.Name) installed and set to Automatic startup."
    } catch {
        $installResults[$svc.Name] = $false
        Write-Fail "Failed to install $($svc.Name): $($_.Exception.Message)"
    }
}

foreach ($svc in $services) {
    if ($installResults[$svc.Name]) {
        try {
            Write-Step "Starting $($svc.Name)..."
            # nssm start: starts the registered Windows service immediately.
            & nssm start $svc.Name | Out-Null
            Start-Sleep -Seconds 1
            $status = (Get-Service -Name $svc.Name -ErrorAction SilentlyContinue).Status
            if ($status -eq 'Running') {
                Write-Ok "$($svc.Name) is running."
            } else {
                Write-Fail "$($svc.Name) did not reach Running state (current: $status)."
            }
        } catch {
            Write-Fail "Failed to start $($svc.Name): $($_.Exception.Message)"
        }
    }
}

Write-Host ""
Write-Host "Installation complete."
