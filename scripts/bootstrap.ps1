[CmdletBinding()]
param(
  [switch]$DryRun,
  [switch]$Yes,
  [switch]$Help
)

if ($Help) {
  @"
Usage: powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 [-DryRun] [-Yes] [-Help]

Bootstraps EphemerAl for Windows/PowerShell:
- checks prerequisites (Docker, Docker Compose, Python, Git)
- optionally runs setup wizard or creates .env from .env.example
- starts containers via docker compose
- creates/updates Ollama model alias
- runs doctor checks
"@ | Write-Host
  exit 0
}

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Say([string]$Msg) { Write-Host $Msg }
function Warn([string]$Msg) { Write-Warning $Msg }
function Fail([string]$Msg) { throw $Msg }
function Run-Step([string]$Cmd, [string[]]$Args) {
  if ($DryRun) {
    Write-Host "[dry-run] $Cmd $($Args -join ' ')"
    return
  }
  & $Cmd @Args
}
function Confirm-Step([string]$Prompt) {
  if ($Yes) { return $true }
  $answer = Read-Host "$Prompt [y/N]"
  return $answer -match '^[Yy]$'
}

Say "EphemerAl bootstrap will do the following:"
Say "  1) Validate local prerequisites"
Say "  2) Prepare .env if missing"
Say "  3) Run docker compose up -d --build"
Say "  4) Run scripts/create_ollama_model.sh"
Say "  5) Run python scripts/doctor.py"

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) { Fail 'Docker is not installed or not on PATH.' }
try { & docker info *> $null } catch { Fail 'Docker is installed but not running. Start Docker Desktop and retry.' }
try { & docker compose version *> $null } catch { Fail 'Docker Compose (docker compose) is unavailable.' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail 'Git is not installed or not on PATH.' }

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $pythonCmd = 'python' }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $pythonCmd = 'py'; }
else { Warn 'Python was not found. setup_wizard.py and doctor.py cannot run.' }

if (-not (Test-Path '.env')) {
  if ($pythonCmd -and (Confirm-Step '.env is missing. Run guided setup wizard now?')) {
    if ($pythonCmd -eq 'py') { Run-Step 'py' @('-3','scripts/setup_wizard.py') }
    else { Run-Step $pythonCmd @('scripts/setup_wizard.py') }
  } else {
    if (-not (Test-Path '.env.example')) { Fail '.env.example was not found, cannot create .env.' }
    if ($DryRun) { Say '[dry-run] Copy-Item .env.example .env' }
    else { Copy-Item '.env.example' '.env' }
    Say 'Created .env from .env.example. Please review and adjust .env for your environment.'
  }
}

if ((Test-Path '.env') -and ((Get-Content '.env' | Select-String -Pattern '^\s*OLLAMA_KV_CACHE_TYPE\s*=\s*q8').Count -gt 0)) {
  $nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
  $nvidiaCtk = Get-Command nvidia-ctk -ErrorAction SilentlyContinue
  if (-not $nvidiaSmi -and -not $nvidiaCtk) {
    Warn 'High-VRAM GPU profile detected (OLLAMA_KV_CACHE_TYPE=q8), but NVIDIA tooling was not found. GPU acceleration may fail.'
  }
}

Run-Step 'docker' @('compose','up','-d','--build')

if (Get-Command bash -ErrorAction SilentlyContinue) {
  Run-Step 'bash' @('scripts/create_ollama_model.sh')
} elseif (Get-Command wsl -ErrorAction SilentlyContinue) {
  Run-Step 'wsl' @('bash','-lc','cd "' + $repoRoot + '" && bash scripts/create_ollama_model.sh')
} else {
  Fail 'Could not run scripts/create_ollama_model.sh. Install Git Bash or enable WSL.'
}

if (-not $pythonCmd) {
  Warn 'Skipping doctor check because Python is unavailable.'
} elseif ($pythonCmd -eq 'py') {
  Run-Step 'py' @('-3','scripts/doctor.py')
} else {
  Run-Step $pythonCmd @('scripts/doctor.py')
}

Say ('Bootstrap completed' + ($(if ($DryRun) { ' (dry run).' } else { '.' })))
