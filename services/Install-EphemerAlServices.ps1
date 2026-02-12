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
        # Stop any existing service first so removal succeeds when reinstalling.
        & nssm stop $Name 2>$null | Out-Null
    } catch {
        # Ignore stop failures for non-existent or already-stopped services.
    }

    try {
        # Remove any existing service first so install is idempotent.
        & nssm remove $Name confirm 2>$null | Out-Null
    } catch {
        # Ignore cleanup failures for non-existent services.
    }

    # nssm install: registers the Windows service with executable path and arguments.
    & nssm install $Name $AppPath $AppArgs | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "nssm install failed for $Name (exit code $LASTEXITCODE)"
    }

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
    if ($LASTEXITCODE -ne 0) {
        throw "nssm set Start failed for $Name (exit code $LASTEXITCODE)"
    }
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

Write-Step "Locating Java executable for Tika service..."
$javaExe = $null
$javaCommand = Get-Command java -ErrorAction SilentlyContinue
if ($javaCommand) {
    $javaExe = $javaCommand.Source
}

if (-not $javaExe) {
    Write-Fail "Could not resolve java.exe."
    Write-Host "Install Java 21+ and ensure java.exe is in PATH, then rerun this script."
    exit 1
}

if (-not (Test-Path $javaExe)) {
    Write-Fail "Resolved Java executable does not exist: $javaExe"
    exit 1
}
Write-Ok "Java found: $javaExe"

Write-Step "Locating Python executable for Streamlit service..."
$pythonExe = $null
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $pythonExe = $pythonCommand.Source
}

if ($pythonExe -and $pythonExe -like '*\WindowsApps\python.exe') {
    # Windows App Execution Alias often resolves to a shim and cannot run as a service account.
    $pythonExe = $null
}

if (-not $pythonExe) {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            $resolvedPython = (& py -3 -c "import sys; print(sys.executable)").Trim()
            if ($resolvedPython) {
                $pythonExe = $resolvedPython
            }
        } catch {
            # Keep null and fail with a user-friendly message below.
        }
    }
}

if (-not $pythonExe) {
    Write-Fail "Could not resolve a real Python executable for the service."
    Write-Host "Install Python for all users and disable the Windows App Execution Alias for python.exe if enabled."
    exit 1
}

if (-not (Test-Path $pythonExe)) {
    Write-Fail "Resolved Python executable does not exist: $pythonExe"
    exit 1
}
Write-Ok "Python found: $pythonExe"

$logDirectory = 'C:\EphemerAl\logs'
if (-not (Test-Path $logDirectory)) {
    Write-Step "Creating log directory: $logDirectory"
    New-Item -Path $logDirectory -ItemType Directory -Force | Out-Null
}
Write-Ok "Service logs directory: $logDirectory"

Write-Step "Validating required application files..."

$requiredPaths = @(
    @{ Label = 'Ollama executable'; Path = 'C:\Ollama\ollama.exe' },
    @{ Label = 'Tika server JAR'; Path = 'C:\Tika\tika-server-standard.jar' },
    @{ Label = 'EphemerAl app file'; Path = 'C:\EphemerAl\ephemeral_app.py' }
)

foreach ($item in $requiredPaths) {
    if (-not (Test-Path -Path $item.Path)) {
        Write-Fail "$($item.Label) not found at $($item.Path)"
        Write-Host "Verify installation paths or update this script before rerunning."
        exit 1
    }
    Write-Ok "$($item.Label) found: $($item.Path)"
}


Write-Step "Validating Streamlit module availability..."
try {
    & $pythonExe -c "import streamlit" | Out-Null
    $streamlitPath = (& $pythonExe -c "import streamlit; print(streamlit.__file__)" 2>$null).Trim()
    Write-Ok "Streamlit module is available for the resolved Python interpreter."
    if ($streamlitPath) {
        Write-Ok "Streamlit location: $streamlitPath"
    }
} catch {
    Write-Fail "Streamlit is not installed for: $pythonExe"
    Write-Host "From C:\EphemerAl run: python -m pip install -r requirements.txt"
    exit 1
}

# OLLAMA_FLASH_ATTENTION requires NVIDIA Turing architecture or newer (RTX 20-series+).
# If Ollama fails to load models on an older GPU, change the value to 0.
$ollamaEnv = @(
    'OLLAMA_HOST=127.0.0.1:11434'
    'OLLAMA_MAX_LOADED_MODELS=1'
    'OLLAMA_FLASH_ATTENTION=1'
    'OLLAMA_KEEP_ALIVE=-1'
    'OLLAMA_MODELS=C:\Ollama\models'
) -join "`n"

$tikaEnv = 'JAVA_TOOL_OPTIONS=-Xmx2g -Xms512m'

$appEnv = @(
    'LLM_BASE_URL=http://127.0.0.1:11434/v1'
    'LLM_MODEL_NAME=gemma3-prod'
    'TIKA_URL=http://127.0.0.1:9998'
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
        AppPath = $javaExe
        AppArgs = '-jar C:\Tika\tika-server-standard.jar --host 127.0.0.1 --port 9998'
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

        $stdoutPath = Join-Path $logDirectory "$($svc.Name).out.log"
        $stderrPath = Join-Path $logDirectory "$($svc.Name).err.log"
        & nssm set $svc.Name AppStdout $stdoutPath | Out-Null
        & nssm set $svc.Name AppStderr $stderrPath | Out-Null
        & nssm set $svc.Name AppRotateFiles 1 | Out-Null
        & nssm set $svc.Name AppRotateOnline 1 | Out-Null
        & nssm set $svc.Name AppRotateBytes 10485760 | Out-Null

        $installResults[$svc.Name] = $true
        Write-Ok "$($svc.Name) installed and set to Automatic startup."
    } catch {
        $installResults[$svc.Name] = $false
        Write-Fail "Failed to install $($svc.Name): $($_.Exception.Message)"
    }
}

if ($installResults['EphemerAlApp']) {
    Write-Step "Configuring EphemerAlApp service dependency order (OllamaService, TikaService)..."
    $dependencyOutput = & sc.exe config EphemerAlApp depend= OllamaService/TikaService
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "EphemerAlApp dependency order configured successfully."
    } else {
        Write-Fail "Failed to set EphemerAlApp dependencies. sc.exe output: $dependencyOutput"
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
