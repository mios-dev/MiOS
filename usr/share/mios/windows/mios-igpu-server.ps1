# AI-hint: Powershell script that hosts a llama.cpp Vulkan-backend inference server on Windows to provide a persistent, low-latency micro-LLM for the MiOS daemon and routing tasks via an OpenAI-compatible API.
# AI-related: mios-igpu-server, mios-daemon-agent, mios-model-router, mios-orchestrator, mios-igpu
# AI-functions: Info, Ok, Warn
<#
  mios-igpu-server.ps1  --  MiOS iGPU inference server (Windows host)

  WHY THIS EXISTS
  ---------------
  The MiOS dev VM is WSL2. WSL2 only exposes the GPU via /dev/dxg (the
  DirectX paravirt node). NVIDIA bridges dxg -> CUDA via its WSL driver, so
  the RTX 4090 works *inside* the VM's ollama container. AMD/Intel have no
  such dxg->compute bridge in WSL2: there is no /dev/kfd (ROCm) and no
  /dev/dri (Vulkan) in the VM, so the in-VM "iGPU" ollama (ollama:rocm at
  :11435) silently runs on CPU ("offloaded 0/29 layers to GPU").

  The only way to actually use the AMD iGPU is to run the inference server
  NATIVELY on Windows, where the iGPU has a real driver + a Vulkan ICD, and
  expose it over Tailscale so the in-VM agent-pipe can reach it. This script
  is that server: llama.cpp's OpenAI-compatible `llama-server` on the VULKAN
  backend (Vulkan supports AMD + Intel iGPUs; ROCm-on-Windows usually does
  NOT support integrated Radeon).

  The MiOS swarm node formerly named the in-VM :11435 ollama is repointed at
  http://<this-host-tailscale-ip>:<Port>/v1 (see mios.toml [agents]).

  USAGE
  -----
    pwsh -File mios-igpu-server.ps1                 # run in foreground (see Vulkan detect the iGPU)
    pwsh -File mios-igpu-server.ps1 -Install        # register a logon scheduled task (persistent, hidden)
    pwsh -File mios-igpu-server.ps1 -Uninstall      # remove the scheduled task
    pwsh -File mios-igpu-server.ps1 -Model C:\path\to\model.gguf

  First run needs internet ONCE to fetch the llama.cpp Vulkan binary + a
  default GGUF; after that it is fully offline.
#>
[CmdletBinding()]
param(
    [int]    $Port        = 11436,
    [string] $Model       = '',
    # The iGPU's ROLE is the ALWAYS-ON LIGHT-COMPUTE BRAIN (
    # "iGPU SHOULD BE THE MICRO LLM ... AND the always-on MiOS daemon background
    # agent"): it hosts the micro-LLM (router/refine/judge/web-expand, hit every
    # turn) + the mios-daemon-agent, so it is NEVER cold and the dGPU/CPU are
    # freed. It is NOT a heavy reasoning agent (it is ~7 tok/s -- too slow for big
    # facets). So serve a SMALL fast instruct GGUF, not the old 3B. Override with
    # -Model / -ModelUrl for a different micro/daemon brain (e.g. a Qwen3-1.7B
    # GGUF to match the daemon model exactly).
    [string] $ModelUrl    = 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf',
    # 64K ctx (iGPU is now ALSO the Hermes-desktop FRONT DOOR
    # via mios-model-router's mios-orchestrator lane). The front door must hold the
    # full ~17K-token MCP tool surface (113 tools) that Hermes sends EVERY turn --
    # at the old 8192 the tool defs were TRUNCATED, the model never saw open_app,
    # and it answered in prose (the recurring "FAILURE"). 65536 also matches the
    # router-advertised ctx + Hermes's 64K floor. KV for a 1.5B at 64K is ~1.9 GB
    # on the iGPU's shared system RAM -- cheap. (ctx-size only sizes the KV pool;
    # it does NOT slow prefill -- prefill cost scales with the ACTUAL prompt len.)
    [int]    $ContextSize = 65536,
    # Single inference slot (KV-paging). llama-server defaults
    # to 4 parallel slots, which (a) splits ctx-size 4 ways (16384 each) and (b)
    # makes the OpenAI /v1 endpoint land a request on ANY slot, so the agent-pipe's
    # per-slot KV save/restore (_kv_paging, slot 0) can't deterministically bracket
    # it. ONE slot = the full 65536 ctx + every request lands on slot 0, so demand-
    # paging the conversation's KV to/from disk is reliable. The iGPU front door
    # processes one user turn at a time anyway; delegated children that round-robin
    # back onto the iGPU simply queue, which is fine.
    [int]    $Parallel    = 1,
    [int]    $GpuLayers   = 99,            # 99 = offload all layers to the iGPU
    # Pin to a SINGLE Vulkan device so llama.cpp does NOT layer-split onto the
    # RTX 4090 (Vulkan also enumerates the 4090, and GPU-PV shares it with the
    # WSL VM where hermes runs -- spilling onto it would steal hermes's VRAM).
    # Vulkan device ENUMERATION ORDER IS NOT STABLE across processes (operator
    # the task-managed server got Vulkan0=RTX 4090 and ran the "iGPU"
    # model on the dGPU at 138 tok/s, stealing hermes's VRAM; standalone
    # --list-devices on the same host showed Vulkan0=AMD). So a fixed index is
    # unreliable. 'auto' (default) resolves the AMD/Radeon device by NAME at
    # launch (see below). Pass an explicit VulkanN to override.
    [string] $Device      = 'auto',
    [switch] $ShowDevices,
    [string] $LlamaTag    = 'latest',      # llama.cpp release tag, or 'latest'
    [switch] $Install,
    [switch] $Uninstall
)

$ErrorActionPreference = 'Stop'
$root      = Join-Path $env:LOCALAPPDATA 'mios\igpu'
$binDir    = Join-Path $root 'bin'
$modelsDir = Join-Path $root 'models'
$logDir    = Join-Path $root 'logs'
# KV-cache paging store ("VRAM can compress or write to disk
# ... clean state when agents/models load/unload"): --slot-save-path below makes
# llama-server expose POST /slots/{id}?action=save|restore, which writes a
# conversation's KV cache to a .bin in THIS dir and restores it near-instantly.
# The in-VM agent-pipe demand-pages per conversation against it (_kv_paging).
$slotDir   = Join-Path $root 'slots'
$exe       = Join-Path $binDir 'llama-server.exe'
$taskName  = 'MiOS-iGPU-Server'
$fwName    = "MiOS - igpu-llm ($Port/tcp)"

function Info($m){ Write-Host "  [*] $m" -ForegroundColor Cyan }
function Ok($m)  { Write-Host "  [+] $m" -ForegroundColor Green }
function Warn($m){ Write-Host "  [!] $m" -ForegroundColor Yellow }

# ---- scheduled-task install / uninstall -------------------------------------
if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Ok "removed scheduled task '$taskName'"
    return
}
if ($Install) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Warn 'Not elevated -- re-launching via UAC to register the logon task...'
        Start-Process -FilePath 'pwsh.exe' -Verb RunAs -ArgumentList @(
            '-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath,'-Install',
            '-Port',$Port,'-ContextSize',$ContextSize,'-GpuLayers',$GpuLayers)
        return
    }
    $argline = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" -Port $Port -ContextSize $ContextSize -GpuLayers $GpuLayers -Device $Device"
    if ($Model) { $argline += " -Model `"$Model`"" }
    # Task Scheduler CANNOT run a bare 'pwsh.exe' when PowerShell 7 is the MSIX
    # (Microsoft Store) build: the bare name is a per-user app-execution ALIAS
    # (a reparse point under %LOCALAPPDATA%\Microsoft\WindowsApps) that the task
    # service does not resolve -> the task fails 0x80070002 (ERROR_FILE_NOT_FOUND)
    # and the iGPU "never fires" (debug). Resolve a CONCRETE
    # interpreter path: prefer a real pwsh under Program Files, but NOT the
    # WindowsApps versioned path (it changes on every pwsh update -> re-breaks);
    # fall back to Windows PowerShell 5.1 at its FIXED System32 path -- this
    # launcher is 5.1-compatible (no ternary/??/-Parallel; only an if-expression
    # assignment), so 5.1 runs it identically.
    $psExe = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
    if (-not $psExe -or $psExe -like '*\WindowsApps\*' -or -not (Test-Path $psExe)) {
        $psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    }
    $action  = New-ScheduledTaskAction  -Execute $psExe -Argument $argline
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $set     = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    $prin    = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $set -Principal $prin -Force | Out-Null
    Ok "registered logon scheduled task '$taskName' (port $Port)"
    Info "starting it now..."
    Start-ScheduledTask -TaskName $taskName
    return
}

# ---- ensure dirs ------------------------------------------------------------
foreach ($d in @($root,$binDir,$modelsDir,$logDir,$slotDir)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

# ---- ensure llama.cpp Vulkan binary -----------------------------------------
if (-not (Test-Path $exe)) {
    Info 'llama-server not found -- fetching llama.cpp Vulkan release...'
    $headers = @{ 'User-Agent' = 'mios-igpu-server' }
    $relUrl  = if ($LlamaTag -eq 'latest') {
        'https://api.github.com/repos/ggml-org/llama.cpp/releases/latest'
    } else {
        "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$LlamaTag"
    }
    $rel   = Invoke-RestMethod -Uri $relUrl -Headers $headers
    $asset = $rel.assets | Where-Object { $_.name -match 'win-vulkan-x64\.zip$' } | Select-Object -First 1
    if (-not $asset) { throw "no win-vulkan-x64 asset in llama.cpp release '$($rel.tag_name)'" }
    $zip = Join-Path $env:TEMP $asset.name
    Info "downloading $($asset.name) ($([math]::Round($asset.size/1MB)) MB)..."
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -Headers $headers
    Info 'extracting...'
    Expand-Archive -Path $zip -DestinationPath $binDir -Force
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    # Some release zips nest the exe in a subfolder -- flatten if needed.
    if (-not (Test-Path $exe)) {
        $found = Get-ChildItem -Path $binDir -Recurse -Filter 'llama-server.exe' | Select-Object -First 1
        if ($found) { Copy-Item $found.FullName $binDir -Force; Get-ChildItem $found.DirectoryName -Filter '*.dll' | Copy-Item -Destination $binDir -Force }
    }
    if (-not (Test-Path $exe)) { throw "llama-server.exe not found after extraction in $binDir" }
    Ok "installed llama-server -> $exe ($($rel.tag_name))"
}

# ---- list Vulkan devices and exit (to pick the right -Device) ---------------
if ($ShowDevices) { & $exe --list-devices; return }

# ---- ensure a model ---------------------------------------------------------
if (-not $Model) {
    $existing = Get-ChildItem -Path $modelsDir -Filter '*.gguf' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($existing) {
        $Model = $existing.FullName
    } else {
        $Model = Join-Path $modelsDir (Split-Path $ModelUrl -Leaf)
        Info "no GGUF present -- downloading default model ($(Split-Path $ModelUrl -Leaf))..."
        Invoke-WebRequest -Uri $ModelUrl -OutFile $Model
        Ok "model -> $Model"
    }
}
if (-not (Test-Path $Model)) { throw "model not found: $Model" }

# ---- firewall: allow inbound on $Port, scoped to the Tailscale CGNAT range --
# 100.64.0.0/10 = the tailnet. Only Tailscale peers (the dev VM) can reach the
# iGPU server; it is NOT exposed to the wider LAN/Internet.
if (-not (Get-NetFirewallRule -DisplayName $fwName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $fwName -Direction Inbound -Action Allow -Protocol TCP `
        -LocalPort $Port -RemoteAddress '100.64.0.0/10' -Profile Any -ErrorAction SilentlyContinue | Out-Null
    Ok "firewall: allow tailnet -> :$Port"
}

# ---- resolve the AMD iGPU device by NAME (enumeration order is unstable) -----
# CRITICAL: Vulkan device INDICES are not stable across
# processes, so a fixed --device Vulkan0 sometimes pinned the RTX 4090 and ran
# the "iGPU" model on the dGPU (138 tok/s, stealing hermes's VRAM). Resolve the
# index by NAME here, in the SAME process context that will launch the server
# (so the enumeration it sees matches), picking the AMD/Radeon device and NEVER
# an NVIDIA one. `--list-devices` prints e.g. "  Vulkan1: AMD Radeon(TM) Graphics
# (..)". Only runs for -Device auto; an explicit VulkanN is honoured as-is.
if ($Device -eq 'auto') {
    $devTxt = (& $exe --list-devices 2>&1 | Out-String)
    $hit = [regex]::Matches($devTxt, '(?im)^\s*(Vulkan\d+)\s*:\s*(.+?)\s*\(') |
           Where-Object { $_.Groups[2].Value -match '(?i)AMD|Radeon' -and
                          $_.Groups[2].Value -notmatch '(?i)NVIDIA|GeForce|RTX' } |
           Select-Object -First 1
    if ($hit) {
        $Device = $hit.Groups[1].Value
        Ok "auto-selected iGPU by NAME: $Device = $($hit.Groups[2].Value.Trim())"
    } else {
        $Device = 'Vulkan0'
        Warn "no AMD/Radeon Vulkan device found in --list-devices; falling back to $Device"
        Warn "device list was:`n$devTxt"
    }
}

# ---- run llama-server (pinned to the resolved AMD iGPU device) ---------------
$tsIp = (Get-NetIPAddress -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -like '100.*' } | Select-Object -First 1).IPAddress
Info "model:    $Model"
Info "binding:  0.0.0.0:$Port   (tailnet -> http://$tsIp`:$Port/v1)"
Info "GPU:      Vulkan device $Device (resolved by name; expect the AMD iGPU, ~9 tok/s -- NOT the 4090)"
$logFile = Join-Path $logDir ("llama-server-{0:yyyyMMdd}.log" -f (Get-Date))
# llama-server logs to STDERR. Under Windows PowerShell 5.1 (which the scheduled
# task now uses for a STABLE interpreter path -- the MSIX pwsh alias is
# unresolvable by Task Scheduler, see -Install above), a native command writing
# to stderr with $ErrorActionPreference='Stop' + 2>&1 raises a terminating
# NativeCommandError and KILLS the server on its FIRST log line (operator
# task exited 1, port never bound). Relax to Continue for the exec
# so the server's normal logging flows into the Tee'd log instead of aborting.
# (pwsh 7 does not treat native stderr this way, so this is harmless there.)
$ErrorActionPreference = 'Continue'
Info "kv-paging: --slot-save-path $slotDir (agent-pipe pages conversations to/from disk)"
# CRITICAL ("iGPU NEVER fired -- not a single tick on Task
# Manager"): newer llama.cpp auto-fits params to device memory ("fitting params
# to device memory ...") and SILENTLY places all layers on the CPU -- it prefers
# the big Ryzen 9950X3D -- EVEN WITH --device VulkanN + --n-gpu-layers 99. So the
# "iGPU server" ran a 1.5B on CPU at 0% iGPU util. `-fit off` disables that
# auto-placement so the explicit iGPU offload is honoured. VERIFIED 0% -> 99.6%.
& $exe `
    --host 0.0.0.0 --port $Port `
    --model $Model `
    --ctx-size $ContextSize `
    --parallel $Parallel `
    --n-gpu-layers $GpuLayers `
    --device $Device `
    -fit off `
    --alias mios-igpu `
    --slot-save-path $slotDir `
    2>&1 | Tee-Object -FilePath $logFile
