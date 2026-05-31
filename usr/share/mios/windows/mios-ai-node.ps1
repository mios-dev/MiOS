<#
  mios-ai-node.ps1 -- MiOS Windows AI Node setup

  Turns the local Podman machine into an AI node that mirrors the MiOS AI
  inference stack and registers itself on the Tailscale swarm so MiOS-DEV's
  Hermes can fan out inference tasks to it.

  What it does
  ------------
  1.  Resizes the Podman machine RAM to the requested amount (default 8 GB).
      (WSL machines do not support --cpus; only --memory is changed.)
  2.  Installs nvidia-container-toolkit inside the Fedora machine so the RTX
      GPU is accessible to containers via CDI (same mechanism as MiOS-DEV).
  3.  Generates the CDI spec (nvidia.com/gpu=all device class).
  4.  Creates the mios.network bridge and /var/lib/ollama* volume directories.
  5.  Deploys mios-ollama (GPU :11434) and mios-ollama-cpu (CPU :11435) as
      systemd Quadlets inside the machine.
  6.  Pulls the initial model set.
  7.  Opens Tailscale-scoped Windows Firewall rules for ports 11434/11435.
  8.  Prints the /etc/mios/mios.toml snippet to paste on MiOS-DEV so Hermes
      registers this node as a swarm agent.

  Usage
  -----
    pwsh -File mios-ai-node.ps1                                 # full setup
    pwsh -File mios-ai-node.ps1 -SkipResize                     # skip RAM resize
    pwsh -File mios-ai-node.ps1 -SkipGpu                        # skip NVIDIA CTK
    pwsh -File mios-ai-node.ps1 -SkipModels                     # skip model pulls
    pwsh -File mios-ai-node.ps1 -Models "qwen3.5:4b,nomic-embed-text"
    pwsh -File mios-ai-node.ps1 -Uninstall                      # remove Quadlets + fw rules

  First run needs internet for: nvidia-container-toolkit RPM, Ollama image,
  and model weights.  Re-runs are fully offline (idempotent).
#>
[CmdletBinding()]
param(
    [string] $MachineName  = 'podman-machine-default',
    [int]    $MemoryMB     = 8192,
    # Default model set sized for 8 GB VRAM (RTX 3060 Ti).
    # qwen3.5:4b      = primary chat/code (~4 GB VRAM)
    # qwen3:1.7b      = CPU light-lane router/classifier
    # qwen3:0.6b      = always-on micro-LLM
    # nomic-embed-text = embeddings for RAG
    [string] $Models       = 'qwen3.5:4b,qwen3:1.7b,qwen3:0.6b,nomic-embed-text',
    [switch] $SkipResize,
    [switch] $SkipGpu,
    [switch] $SkipModels,
    [switch] $Uninstall
)

$ErrorActionPreference = 'Stop'
$QuadletSrc = Join-Path $PSScriptRoot 'quadlets'

function Info($m) { Write-Host "  [*] $m" -ForegroundColor Cyan    }
function Ok($m)   { Write-Host "  [+] $m" -ForegroundColor Green   }
function Warn($m) { Write-Host "  [!] $m" -ForegroundColor Yellow  }
function Fail($m) { Write-Host "  [X] $m" -ForegroundColor Red; throw $m }

# ── helpers ───────────────────────────────────────────────────────────────────

function Get-TailscaleIP {
    try {
        $ip = (& tailscale ip --4 2>$null).Trim()
        if ($ip -match '^\d+\.\d+\.\d+\.\d+$') { return $ip }
    } catch {}
    $ip = (Get-NetAdapter -ErrorAction SilentlyContinue |
           Where-Object { $_.InterfaceDescription -match 'Tailscale' } |
           Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
           Select-Object -First 1).IPAddress
    if ($ip) { return $ip }
    $ip = (Get-NetIPAddress -ErrorAction SilentlyContinue |
           Where-Object { $_.IPAddress -match '^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.' } |
           Select-Object -First 1).IPAddress
    return $ip
}

# Run a bash script on the machine.
# Passes the script as a bash -c argument (not stdin) to avoid PowerShell's
# pipeline adding \r to every line.  The script is base64-encoded so bash
# metacharacters inside it ($, >, |, etc.) are never seen by PowerShell.
function Invoke-Machine([string]$script) {
    $lf  = $script -replace "`r`n", "`n"
    $enc = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lf))
    # Pass as a single double-quoted string so PowerShell sends it as one arg and
    # the remote shell sees | and > as operators (not as separate CLI tokens).
    # Do NOT use -- bash -c "..." : podman machine ssh joins the separate args with
    # spaces before sending, which strips the inner quoting around the -c argument.
    podman machine ssh $MachineName "echo $enc | base64 -d | bash"
    if ($LASTEXITCODE -ne 0) { Fail "Remote script failed (see output above)" }
}

# Write a file into the machine using base64 to avoid CRLF/quoting issues.
function Write-MachineFile([string]$remotePath, [string]$content) {
    $lf  = $content -replace "`r`n", "`n"
    $enc = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lf))
    podman machine ssh $MachineName "echo $enc | base64 -d > $remotePath"
    if ($LASTEXITCODE -ne 0) { Fail "Failed to write $remotePath on machine" }
}

function Test-MachineCmd([string]$cmd) {
    $lf  = $cmd -replace "`r`n", "`n"
    $enc = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lf))
    $null = podman machine ssh $MachineName "echo $enc | base64 -d | bash" 2>$null
    return ($LASTEXITCODE -eq 0)
}

# ── uninstall ─────────────────────────────────────────────────────────────────

if ($Uninstall) {
    Info 'Stopping and removing MiOS AI Node Quadlets...'
    Invoke-Machine @'
systemctl stop   mios-ollama.service     2>/dev/null || true
systemctl disable mios-ollama.service    2>/dev/null || true
systemctl stop   mios-ollama-cpu.service 2>/dev/null || true
systemctl disable mios-ollama-cpu.service 2>/dev/null || true
rm -f /etc/containers/systemd/mios-ollama.container
rm -f /etc/containers/systemd/mios-ollama-cpu.container
rm -f /etc/containers/systemd/mios.network
systemctl daemon-reload
echo "[OK] Quadlets removed"
'@
    foreach ($port in @(11434, 11435)) {
        $name = "MiOS AI Node - ollama ($port/tcp)"
        Remove-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
        Ok "removed firewall rule: $name"
    }
    Ok 'Uninstall complete.'
    return
}

# ── preflight ─────────────────────────────────────────────────────────────────

Info 'MiOS AI Node setup starting...'
Info "Target machine: $MachineName"

if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
    Fail 'podman not found. Install Podman Desktop first: https://podman-desktop.io'
}
$machines = podman machine list --format '{{.Name}}' 2>$null
if ($machines -notcontains $MachineName) {
    Fail "Podman machine '$MachineName' not found."
}

$tsIp = Get-TailscaleIP
if (-not $tsIp) {
    Warn 'Tailscale IP not detected -- using placeholder in summary.'
    $tsIp = '<mios-win-tailscale-ip>'
} else {
    Ok "Tailscale IP: $tsIp"
}

# ── resize machine ─────────────────────────────────────────────────────────────

if (-not $SkipResize) {
    $info   = podman machine inspect $MachineName 2>$null | ConvertFrom-Json
    $curMem = [int]($info.Memory)   # already in MiB
    if ($curMem -lt $MemoryMB) {
        Warn "Machine RAM is ${curMem} MB. Requesting resize to ${MemoryMB} MB..."
        Warn '(WSL2 machines do not support podman machine set --memory; editing .wslconfig instead)'
        # For WSL2 machines, set memory via .wslconfig which WSL reads on restart.
        $wslCfg = "$env:USERPROFILE\.wslconfig"
        $existing = if (Test-Path $wslCfg) { Get-Content $wslCfg -Raw } else { '' }
        $memGb = [math]::Ceiling($MemoryMB / 1024)
        if ($existing -match '\[wsl2\]') {
            if ($existing -match 'memory\s*=') {
                $existing = $existing -replace 'memory\s*=\s*[^\r\n]+', "memory=${memGb}GB"
            } else {
                $existing = $existing -replace '(\[wsl2\])', "`$1`nmemory=${memGb}GB"
            }
        } else {
            $existing += "`n[wsl2]`nmemory=${memGb}GB`n"
        }
        Set-Content $wslCfg $existing
        # Restart the machine to apply.
        podman machine stop $MachineName
        podman machine start $MachineName
        Ok ".wslconfig: memory=${memGb}GB -- machine restarted."
    } else {
        Ok "Machine RAM OK: ${curMem} MB."
    }
} else {
    Info 'Skipping machine resize (-SkipResize).'
}

$state = (podman machine inspect $MachineName 2>$null | ConvertFrom-Json).State
if ($state -ne 'running') {
    Info 'Starting Podman machine...'
    podman machine start $MachineName
}

# ── remove unnamed Ollama container ───────────────────────────────────────────

Info 'Removing any existing unnamed Ollama container...'
Invoke-Machine @'
set -euo pipefail
for cname in $(podman ps -a --filter 'ancestor=docker.io/ollama/ollama:latest' --format '{{.Names}}' 2>/dev/null); do
    case "$cname" in mios-ollama|mios-ollama-cpu) continue ;; esac
    podman stop "$cname" 2>/dev/null || true
    podman rm   "$cname" 2>/dev/null || true
    echo "  removed: $cname"
done
echo "[OK] cleanup done"
'@

# ── NVIDIA Container Toolkit ──────────────────────────────────────────────────

if (-not $SkipGpu) {
    Info 'Checking NVIDIA Container Toolkit...'
    if (-not (Test-MachineCmd 'rpm -q nvidia-container-toolkit')) {
        Info 'Installing nvidia-container-toolkit (this may take a minute)...'
        Invoke-Machine @'
set -euo pipefail
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
    -o /etc/yum.repos.d/nvidia-container-toolkit.repo
dnf install -y nvidia-container-toolkit
echo "[OK] nvidia-container-toolkit installed"
'@
        Ok 'nvidia-container-toolkit installed.'
    } else {
        Ok 'nvidia-container-toolkit already present.'
    }

    Info 'Generating CDI spec...'
    Invoke-Machine @'
set -euo pipefail
mkdir -p /etc/cdi
# nvidia-ctk detects WSL2 and generates a spec covering /dev/dxg + /usr/lib/wsl.
nvidia-ctk cdi generate \
    --output=/etc/cdi/nvidia.yaml \
    --device-name-strategy=index 2>&1 \
|| {
    echo "[WARN] nvidia-ctk generate failed -- writing fallback WSL2 CDI spec"
    cat > /etc/cdi/nvidia.yaml << 'CDIYAML'
cdiVersion: "0.5.0"
kind: "nvidia.com/gpu"
devices:
  - name: "0"
    containerEdits:
      deviceNodes:
        - path: /dev/dxg
          type: c
      mounts:
        - hostPath: /usr/lib/wsl
          containerPath: /usr/lib/wsl
          options: [ro, bind]
  - name: "all"
    containerEdits:
      deviceNodes:
        - path: /dev/dxg
          type: c
      mounts:
        - hostPath: /usr/lib/wsl
          containerPath: /usr/lib/wsl
          options: [ro, bind]
containerEdits:
  env:
    - name: NVIDIA_VISIBLE_DEVICES
      value: void
CDIYAML
}
nvidia-ctk cdi list 2>/dev/null || true
echo "[OK] CDI spec ready"
'@
    Ok 'CDI spec ready.'
} else {
    Info 'Skipping GPU setup (-SkipGpu).'
}

# ── mios.network + volume directories ─────────────────────────────────────────

Info 'Creating mios network and volume directories...'
Invoke-Machine @'
set -euo pipefail
podman network exists mios 2>/dev/null || podman network create mios
mkdir -p /var/lib/ollama/models /var/lib/ollama-cpu
chmod 0755 /var/lib/ollama /var/lib/ollama/models /var/lib/ollama-cpu
echo "[OK] network + volumes ready"
'@

# ── deploy Quadlet files ──────────────────────────────────────────────────────

Info 'Deploying Quadlet files...'
Invoke-Machine 'mkdir -p /etc/containers/systemd'

foreach ($f in @('mios.network', 'mios-ollama.container', 'mios-ollama-cpu.container')) {
    $src = Join-Path $QuadletSrc $f
    if (-not (Test-Path $src)) { Fail "Quadlet source not found: $src" }
    $content = Get-Content $src -Raw
    Write-MachineFile "/etc/containers/systemd/$f" $content
    Ok "deployed: $f"
}

# ── enable units ──────────────────────────────────────────────────────────────

Info 'Reloading systemd and starting Quadlet units...'
Invoke-Machine @'
set -euo pipefail
systemctl daemon-reload
# Quadlet-generated units live in /run/systemd/generator/ and cannot be
# "enabled" via symlinks; use "start" instead.  WantedBy=multi-user.target
# in the container file is wired in by the generator on daemon-reload.
systemctl start mios-ollama.service     2>&1 | tail -3 || true
systemctl start mios-ollama-cpu.service 2>&1 | tail -3 || true
sleep 6
for svc in mios-ollama mios-ollama-cpu; do
    if systemctl is-active --quiet "$svc.service"; then
        echo "[OK] $svc running"
    else
        echo "[WARN] $svc not yet active (may still be pulling image)"
        systemctl status "$svc.service" --no-pager -l 2>&1 | tail -12 || true
    fi
done
'@

# ── pull models ───────────────────────────────────────────────────────────────

if (-not $SkipModels) {
    $modelList = $Models -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    Info "Pulling $($modelList.Count) model(s): $($modelList -join ', ')"
    Info 'Waiting for mios-ollama container to be running (up to 60 s)...'
    Invoke-Machine @'
for i in $(seq 1 12); do
    podman container inspect mios-ollama --format '{{.State.Status}}' 2>/dev/null \
        | grep -q running && break
    sleep 5
done
podman container inspect mios-ollama --format '{{.State.Status}}' 2>/dev/null \
    | grep -q running \
    || { echo "[WARN] mios-ollama not running -- run pull manually later"; exit 0; }
echo "[OK] mios-ollama container is running"
'@
    foreach ($model in $modelList) {
        Info "Pulling $model ..."
        Invoke-Machine "podman exec mios-ollama ollama pull $model"
        Ok "pulled: $model"
    }
} else {
    Info 'Skipping model pulls (-SkipModels).'
    Info "  Pull later: podman machine ssh $MachineName -- podman exec mios-ollama ollama pull qwen3.5:4b"
}

# ── firewall + portproxy ───────────────────────────────────────────────────────

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Info 'Configuring Windows Firewall (Tailscale CGNAT 100.64.0.0/10)...'
if ($isAdmin) {
    foreach ($entry in @(
        [pscustomobject]@{ Port = 11434; Name = 'MiOS AI Node - mios-ollama (11434/tcp)' },
        [pscustomobject]@{ Port = 11435; Name = 'MiOS AI Node - mios-ollama-cpu (11435/tcp)' }
    )) {
        $existing = Get-NetFirewallRule -DisplayName $entry.Name -ErrorAction SilentlyContinue
        if ($existing) {
            Set-NetFirewallRule -DisplayName $entry.Name -Enabled True -Action Allow -ErrorAction SilentlyContinue
            Ok "firewall: refreshed '$($entry.Name)'"
        } else {
            New-NetFirewallRule -DisplayName $entry.Name `
                -Direction Inbound -Action Allow -Protocol TCP `
                -LocalPort $entry.Port -RemoteAddress '100.64.0.0/10' `
                -Profile Any -ErrorAction SilentlyContinue | Out-Null
            Ok "firewall: created '$($entry.Name)'"
        }
    }

    # portproxy so Tailscale (Windows-side) can reach into the Podman machine.
    # wslrelay binds the forwarded ports on [::1] (IPv6 loopback), so use
    # v4tov6 to bridge IPv4 Tailscale traffic to IPv6 loopback.
    $svc = Get-Service iphlpsvc -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne 'Running') {
        Set-Service iphlpsvc -StartupType Automatic; Start-Service iphlpsvc
    }
    foreach ($port in @(11434, 11435)) {
        netsh interface portproxy delete v4tov6 listenaddress=0.0.0.0 listenport=$port 2>$null | Out-Null
        netsh interface portproxy add    v4tov6 listenaddress=0.0.0.0 listenport=$port `
              connectaddress=::1 connectport=$port | Out-Null
        Ok "portproxy 0.0.0.0:${port} -> [::1]:${port}"
    }
} else {
    Warn 'Not elevated -- firewall/portproxy skipped. Re-run as admin or run Setup-MiOSLanPortProxy.ps1.'
}

# ── summary ───────────────────────────────────────────────────────────────────

Write-Host ''
Write-Host '═══════════════════════════════════════════════════════════════' -ForegroundColor Green
Write-Host '  MiOS AI Node setup complete' -ForegroundColor Green
Write-Host '═══════════════════════════════════════════════════════════════' -ForegroundColor Green
Write-Host ''
Write-Host '  Services:' -ForegroundColor Cyan
Write-Host "    mios-ollama     GPU  :11434   http://${tsIp}:11434/v1"
Write-Host "    mios-ollama-cpu CPU  :11435   http://${tsIp}:11435/v1"
Write-Host ''
Write-Host '  Add to /etc/mios/mios.toml on MiOS-DEV:' -ForegroundColor Cyan
Write-Host ''
Write-Host "[agents.mios-win]"
Write-Host "endpoint    = `"http://${tsIp}:11434/v1`""
Write-Host 'model       = "qwen3.5:4b"'
Write-Host 'role        = "gpu"'
Write-Host 'job         = "RTX 3060 Ti GPU overflow node on MiOS-WIN."'
Write-Host 'default     = false'
Write-Host 'lane        = "gpu"'
Write-Host 'health_gate = true'
Write-Host 'fanout      = true'
Write-Host 'strengths   = ["gpu_inference", "code", "chat", "overflow_compute"]'
Write-Host ''
Write-Host '  Useful commands:' -ForegroundColor Cyan
Write-Host "  Status:  podman machine ssh $MachineName -- systemctl status mios-ollama"
Write-Host "  Logs:    podman machine ssh $MachineName -- journalctl -u mios-ollama -f"
Write-Host "  Models:  podman machine ssh $MachineName -- podman exec mios-ollama ollama list"
Write-Host ''
