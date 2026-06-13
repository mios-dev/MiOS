# AI-hint: Configures Claude Desktop and Claude Code to connect to the MiOS MCP server by dynamically resolving WSL distro names and ports to enable remote control and dispatch capabilities across both Anthropic clients.
# AI-related: /usr/libexec/mios/mios-mcp-server, mios-mcp-server, mios-claude-mcp-setup, mios-control
# AI-functions: Read-JsonObj, Ensure-Prop
<#
  mios-claude-mcp-setup.ps1 -- wire the MiOS MCP server (remote control +
  dispatch: the full MiOS verb catalog -> agent-pipe /v1/dispatch) into BOTH
  Anthropic desktop clients so EVERY chat has it on:

    * Claude Code   -> ~/.claude.json  (top-level mcpServers = user/global
                       scope = every project + chat) via the native HTTP
                       transport to the already-running MiOS MCP service.
    * Claude Desktop -> %APPDATA%\Claude\claude_desktop_config.json via a
                       version-independent stdio bridge (wsl.exe spawns the
                       MiOS MCP server inside the distro on demand).

  Operator binding 2026-05-29: "make sure Claude Code and Claude Desktop have
  remote control and dispatch on for every chat!!"

  NO HARDCODES: the WSL distro name + MCP port are resolved from the live
  environment (wsl.exe -l / MIOS_MCP_PORT), not baked in. Idempotent: re-running
  refreshes the entry without disturbing other servers. Run it again any time a
  client config gets reset.
#>
param(
  [string]$Distro = $null,
  [int]$Port = 0,
  [string]$ServerName = 'mios-control'
)
$ErrorActionPreference = 'Stop'

# ---- resolve the WSL distro generatively from the registry -------------------
# (wsl.exe -l emits UTF-16 that mangles under the default console encoding ->
# "p" instead of "podman-MiOS-DEV"; the Lxss registry is clean + null-free.)
# Prefer a distro whose name carries the MiOS product (that's where the MiOS
# MCP server lives), else the WSL default distro, else the first registered.
if (-not $Distro) {
  $lxss = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
  $all = @(Get-ChildItem $lxss -ErrorAction SilentlyContinue |
           ForEach-Object { (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DistributionName } |
           Where-Object { $_ })
  $Distro = ($all | Where-Object { $_ -match 'MiOS' } | Select-Object -First 1)
  if (-not $Distro) {
    $defGuid = (Get-ItemProperty $lxss -Name DefaultDistribution -ErrorAction SilentlyContinue).DefaultDistribution
    if ($defGuid) { $Distro = (Get-ItemProperty (Join-Path $lxss $defGuid) -ErrorAction SilentlyContinue).DistributionName }
  }
  if (-not $Distro -and $all.Count) { $Distro = $all[0] }
}
if (-not $Distro) { throw "could not resolve a WSL distro from the Lxss registry" }

# ---- resolve the MCP port generatively (MIOS_MCP_PORT in the distro, else 8765)
if ($Port -le 0) {
  $p = (wsl.exe -d $Distro -- bash -lc 'echo -n "${MIOS_MCP_PORT:-8765}"' 2>$null)
  if ($p -match '^\d+$') { $Port = [int]$p } else { $Port = 8765 }
}
$Url = "http://localhost:$Port/mcp"
Write-Host "MiOS MCP setup: distro=$Distro port=$Port url=$Url server='$ServerName'"

# ---- helper: load JSON file into an ordered hashtable (preserve unknown keys) -
function Read-JsonObj($path) {
  if (Test-Path $path) {
    $raw = Get-Content -Raw -Path $path
    if ($raw.Trim()) { return ($raw | ConvertFrom-Json) }
  }
  return [pscustomobject]@{}
}
function Ensure-Prop($obj, $name, $value) {
  if ($obj.PSObject.Properties.Name -contains $name) { $obj.$name = $value }
  else { $obj | Add-Member -NotePropertyName $name -NotePropertyValue $value }
}

# ================= Claude Code  (~/.claude.json, HTTP transport) =============
$ccPath = Join-Path $env:USERPROFILE '.claude.json'
$cc = Read-JsonObj $ccPath
if (-not ($cc.PSObject.Properties.Name -contains 'mcpServers') -or $null -eq $cc.mcpServers) {
  Ensure-Prop $cc 'mcpServers' ([pscustomobject]@{})
}
$ccEntry = [pscustomobject]@{ type = 'http'; url = $Url }
Ensure-Prop $cc.mcpServers $ServerName $ccEntry
if (Test-Path $ccPath) { Copy-Item $ccPath "$ccPath.mios.bak" -Force }
($cc | ConvertTo-Json -Depth 100) | Set-Content -Path $ccPath -Encoding UTF8
Write-Host "  [Claude Code]    +$ServerName (http) -> $ccPath"

# ============ Claude Desktop  (claude_desktop_config.json, stdio) ============
$cdDir  = Join-Path $env:APPDATA 'Claude'
$cdPath = Join-Path $cdDir 'claude_desktop_config.json'
if (-not (Test-Path $cdDir)) { New-Item -ItemType Directory -Force -Path $cdDir | Out-Null }
$cd = Read-JsonObj $cdPath
if (-not ($cd.PSObject.Properties.Name -contains 'mcpServers') -or $null -eq $cd.mcpServers) {
  Ensure-Prop $cd 'mcpServers' ([pscustomobject]@{})
}
$cdEntry = [pscustomobject]@{
  command = 'wsl.exe'
  args    = @('-d', $Distro, '--', '/usr/libexec/mios/mios-mcp-server')
}
Ensure-Prop $cd.mcpServers $ServerName $cdEntry
if (Test-Path $cdPath) { Copy-Item $cdPath "$cdPath.mios.bak" -Force }
($cd | ConvertTo-Json -Depth 100) | Set-Content -Path $cdPath -Encoding UTF8
Write-Host "  [Claude Desktop] +$ServerName (stdio via wsl.exe) -> $cdPath"

Write-Host "Done. Restart Claude Desktop to pick up the new server; Claude Code picks it up on the next session."
