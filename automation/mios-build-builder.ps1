#Requires -Version 7.1
<#
.SYNOPSIS
  MiOS builder - idempotent Podman machine provisioner for Windows.

.DESCRIPTION
  Creates or reconfigures a rootful Podman machine named 'mios-builder'
  with 100% of host CPU/RAM and GPU passthrough provisioning. Safe to re-run.

  - Detects host CPU/RAM via WMI and allocates maximum resources.
  - Filters out fake video adapters (Hyper-V, Parsec, DisplayLink) in GPU
    detection so WSL2 on Windows doesn't trip on Basic Render Driver.
  - If a machine named 'mios-builder' already exists AND is rootful AND
    has >= desired CPUs/RAM, it is left alone (pure idempotent no-op).
  - If misconfigured, tries `podman machine set` first (non-destructive).
  - Only resorts to destroy+recreate when `-Force` is passed or when
    `podman machine set` fails.
  - SSHs into the machine to install nvidia-container-toolkit and generate
    the CDI spec at /var/run/cdi/nvidia.yaml (WSL mode auto-detected).

.PARAMETER MachineName
  Podman machine name (default: mios-builder).

.PARAMETER MinMemReserveMiB
  RAM in MiB to leave for the Windows host (default: 4096).

.PARAMETER Force
  Destroy and recreate the machine even if it already looks correct.

.EXAMPLE
  pwsh .\mios-build-builder.ps1
  pwsh .\mios-build-builder.ps1 -MinMemReserveMiB 8192
  pwsh .\mios-build-builder.ps1 -Force
#>
[CmdletBinding()]
param(
  [string]$MachineName    = 'mios-builder',
  [int]   $MinMemReserveMiB = 4096,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Log ($m) { Write-Host "[mios-build-builder] $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "[mios-build-builder] $m" -ForegroundColor Yellow }
function Die ($m) { Write-Host "[mios-build-builder] FATAL: $m" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
  Die 'podman.exe not on PATH. Install Podman Desktop or Podman CLI first.'
}
try {
  $pv = (& podman version --format '{{.Client.Version}}') 2>$null
  Log "Podman client: $pv"
} catch { Warn 'Could not read Podman version; continuing.' }

# ---------------------------------------------------------------------------
# Host capacity detection (WMI / CIM)
# ---------------------------------------------------------------------------
$cs  = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor
$totalLogical = ($cpu | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum
$totalMiB     = [int]($cs.TotalPhysicalMemory / 1MB)
$allocMiB     = [Math]::Max(2048, $totalMiB - $MinMemReserveMiB)

Log ("Host: {0} logical CPUs, {1} MiB RAM; allocating {2} MiB ({3} MiB reserved for host)" `
     -f $totalLogical, $totalMiB, $allocMiB, $MinMemReserveMiB)

# ---------------------------------------------------------------------------
# GPU detection (filters fake adapters)
# ---------------------------------------------------------------------------
$gpus = Get-CimInstance Win32_VideoController |
  Where-Object {
    $_.PNPDeviceID -match '^PCI\\VEN_(10DE|1002|8086)' -and
    $_.Name -notmatch 'Microsoft Basic|Hyper-V|Remote Display|Parsec|DisplayLink'
  }

$hasNvidia = [bool]($gpus | Where-Object { $_.PNPDeviceID -match 'VEN_10DE' } | Select-Object -First 1)
$hasAmd    = [bool]($gpus | Where-Object { $_.PNPDeviceID -match 'VEN_1002' } | Select-Object -First 1)
$hasIntel  = [bool]($gpus | Where-Object { $_.PNPDeviceID -match 'VEN_8086' } | Select-Object -First 1)

foreach ($g in $gpus) { Log "  GPU: $($g.Name)" }
Log ("Detected: NVIDIA={0}  AMD={1}  Intel={2}" -f $hasNvidia, $hasAmd, $hasIntel)

# ---------------------------------------------------------------------------
# Idempotency: inspect existing machine
# ---------------------------------------------------------------------------
$existing = $null
try {
  $raw = & podman machine inspect $MachineName 2>$null
  if ($LASTEXITCODE -eq 0 -and $raw) {
    $parsed = $raw | ConvertFrom-Json
    if ($parsed -is [Array]) { $existing = $parsed[0] } else { $existing = $parsed }
  }
} catch { $existing = $null }

$needsRecreate = $false

if ($existing) {
  # Podman's inspect schema varies slightly across versions; try both shapes.
  $curCpus    = 0; $curMem = 0; $curRootful = $false
  try { $curCpus    = [int] $existing.Resources.CPUs }      catch { $null }
  try { $curMem     = [int] $existing.Resources.Memory }    catch { $null }
  try { $curRootful = [bool]$existing.Rootful }             catch { $null }
  if (-not $curCpus)    { try { $curCpus    = [int] $existing.CPUs }    catch { $null } }
  if (-not $curMem)     { try { $curMem     = [int] $existing.Memory }  catch { $null } }

  Log "Existing '$MachineName': CPUs=$curCpus Memory=${curMem}MiB Rootful=$curRootful State=$($existing.State)"

  if     ($Force)                               { $needsRecreate = $true; Warn '-Force set; will recreate' }
  elseif (-not $curRootful)                     { $needsRecreate = $true; Warn 'Machine is not rootful' }
  elseif ($curCpus -lt $totalLogical)           { $needsRecreate = $true; Warn "CPUs ($curCpus) below host ($totalLogical)" }
  elseif ($curMem  -lt ($allocMiB - 512))       { $needsRecreate = $true; Warn "RAM (${curMem} MiB) below target (~$allocMiB MiB)" }
  else                                          { Log 'Existing machine config acceptable; no recreate needed.' }
} else {
  Log "No existing machine '$MachineName'; will create."
}

# ---------------------------------------------------------------------------
# Create or reconfigure
# ---------------------------------------------------------------------------
if (-not $existing) {
  & podman machine init --cpus $totalLogical --memory $allocMiB --rootful $MachineName
  if ($LASTEXITCODE -ne 0) { Die 'podman machine init failed' }
}
elseif ($needsRecreate -and $Force) {
  Warn "Destroying and recreating '$MachineName'"
  & podman machine stop $MachineName 2>$null | Out-Null
  & podman machine rm -f $MachineName
  & podman machine init --cpus $totalLogical --memory $allocMiB --rootful $MachineName
  if ($LASTEXITCODE -ne 0) { Die 'podman machine init failed' }
}
elseif ($needsRecreate) {
  # Prefer non-destructive reconfigure. Podman 5.x supports --cpus/--memory
  # /--rootful on stopped machines.
  Log 'Reconfiguring existing machine via podman machine set (non-destructive)'
  & podman machine stop $MachineName 2>$null | Out-Null
  & podman machine set --cpus $totalLogical --memory $allocMiB --rootful $MachineName
  if ($LASTEXITCODE -ne 0) {
    Warn 'podman machine set failed; falling back to destroy+recreate'
    & podman machine rm -f $MachineName
    & podman machine init --cpus $totalLogical --memory $allocMiB --rootful $MachineName
    if ($LASTEXITCODE -ne 0) { Die 'podman machine init failed on fallback path' }
  }
}

# ---------------------------------------------------------------------------
# Start machine (idempotent: "already running" is not an error)
# ---------------------------------------------------------------------------
& podman machine start $MachineName 2>$null
Log 'Machine started (or was already running).'

# ---------------------------------------------------------------------------
# SSH-side provisioning
# Podman machine's Fedora root filesystem IS mutable on WSL (no rpm-ostree),
# so dnf installs persist across stop/start.
# ---------------------------------------------------------------------------
function Invoke-MachineSSH {
  param([Parameter(Mandatory)][string]$Bash)
  # The PowerShell | pipeline re-introduces \r\n when writing each line to a
  # child process stdin, even after -replace stripping. Bypass entirely by
  # base64-encoding the script and decoding inside the machine.
  # base64 charset (A-Za-z0-9+/=) contains no CRLFs or shell metacharacters.
  $Bash = $Bash -replace "`r`n", "`n" -replace "`r", "`n"
  $encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($Bash))
  & podman machine ssh $MachineName -- sudo bash -c "echo $encoded | base64 -d | bash"
  return $LASTEXITCODE
}

if ($hasNvidia) {
  Log 'Provisioning NVIDIA container toolkit inside machine'
  $nvScript = @'
set -euo pipefail
if ! rpm -q nvidia-container-toolkit >/dev/null 2>&1; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
    | tee /etc/yum.repos.d/nvidia-container-toolkit.repo >/dev/null
  dnf install -y nvidia-container-toolkit
fi
install -d -m 0755 /var/run/cdi /etc/cdi
# WSL mode is auto-detected, pass --mode=wsl explicitly for clarity; fall
# back to auto if the flag is unsupported on an older toolkit.
if ! nvidia-ctk cdi generate --mode=wsl --output=/var/run/cdi/nvidia.yaml 2>/dev/null; then
  nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml
fi
# Upstream refresh units (v1.18+) keep the spec current across machine restarts.
systemctl enable --now nvidia-cdi-refresh.path 2>/dev/null || true
echo "NVIDIA CDI ready:"
ls -l /var/run/cdi/
'@
  $rc = Invoke-MachineSSH $nvScript
  if ($rc -ne 0) { Warn "NVIDIA provisioning exited non-zero ($rc); see output above." }
}

if ($hasAmd) {
  Log 'AMD GPU detected on Windows host'
  Warn 'WSL2 does not expose /dev/kfd; ROCm-on-WSL requires librocdxg (ROCm 7.2+)'
  Warn 'Builder will fall back to CPU for AMD-specific builds. NVIDIA/Intel unaffected.'
}

if ($hasIntel -and -not $hasNvidia -and -not $hasAmd) {
  Log 'Intel GPU only — WSL2 GPU compute for Intel is not officially supported'
  Warn 'Builder will use CPU inference; this does not affect building bootc images.'
}

# ---------------------------------------------------------------------------
# Persist builder metadata
# ---------------------------------------------------------------------------
$meta = [ordered]@{
  machine     = $MachineName
  cpus        = $totalLogical
  memoryMiB   = $allocMiB
  gpu_nvidia  = $hasNvidia
  gpu_amd     = $hasAmd
  gpu_intel   = $hasIntel
  provisioned = (Get-Date).ToString('o')
} | ConvertTo-Json

$metaDir = Join-Path $env:LOCALAPPDATA 'MiOS'
New-Item -ItemType Directory -Force -Path $metaDir | Out-Null
# Write without BOM
[System.IO.File]::WriteAllText(
  (Join-Path $metaDir 'builder.json'),
  $meta,
  [System.Text.UTF8Encoding]::new($false)
)

Log ""
Log "Builder ready. Example usage:"
Log "  podman --connection ${MachineName}-root build -t mios:latest ."
Log "  podman --connection ${MachineName}-root run --rm --device nvidia.com/gpu=all \\"
Log "       docker.io/nvidia/cuda:10.1.1-base-ubi9 nvidia-smi"
# Explicit exit 0 — non-fatal warnings (NVIDIA CDI, AMD/Intel) leave
# $LASTEXITCODE non-zero; without this the caller sees a failure.
exit 0
