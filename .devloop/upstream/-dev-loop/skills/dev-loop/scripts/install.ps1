#Requires -Version 7.0
# Install dev-loop into every harness found (or -All): all 7 skills (+scripts/references/assets) and every command shim. Project scope by default.
# Claude Code: prefer `claude plugin marketplace add <repo>` + `claude plugin install dev-loop@dev-loop-marketplace`, or `claude --plugin-dir <repo>`.
param([switch]$All, [switch]$User, [switch]$Global, [switch]$Project, [switch]$DryRun, [switch]$Scaffold, [string[]]$Harness)
if ($Global) { $User = $true }; if ($Project) { $User = $false }
$Src = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path; $Plug = (Resolve-Path (Join-Path $Src '../..')).Path
$Root = (git rev-parse --show-toplevel 2>$null); if (-not $Root) { $Root = (Get-Location).Path }; $H = $HOME
$Table = @(
  @{n='claude';      d='claude';   ps='.claude/skills';   us="$H/.claude/skills";               pc='.claude/commands';   uc="$H/.claude/commands";              x=@{}},
  @{n='antigravity'; d='agy';      ps='.agents/skills';   us="$H/.gemini/config/skills";        pc='.agent/workflows';   uc="$H/.gemini/antigravity/workflows"; x=@{}},
  @{n='gemini';      d='gemini';   ps='.gemini/skills';   us="$H/.gemini/skills";               pc='.gemini/commands';   uc="$H/.gemini/commands";              x=@{}},
  @{n='codex';       d='codex';    ps='.agents/skills';   us="$H/.agents/skills";               pc='.codex/prompts';     uc="$H/.codex/prompts";                x=@{}},
  @{n='cursor';      d='.cursor';  ps='.cursor/skills';   us="$H/.cursor/skills";               pc='.cursor/commands';   uc="$H/.cursor/commands";              x=@{'.mdc'='.cursor/rules'}},
  @{n='copilot';     d='.github';  ps='.github/skills';   us="$H/.copilot/skills";              pc='.github/prompts';    uc="$H/.copilot/prompts";              x=@{'.agent.md'='.github/agents'}},
  @{n='opencode';    d='opencode'; ps='.opencode/skills'; us="$H/.config/opencode/skills";      pc='.opencode/command';  uc="$H/.config/opencode/command";      x=@{}},
  @{n='hermes';      d='hermes';   ps="$H/.hermes/skills"; us="$H/.hermes/skills";              pc='-';                  uc='-';                                x=@{}}
)
foreach ($t in $Table) {
  if ($Harness -and $t.n -notin $Harness) { continue }
  $found = (Get-Command $t.d -EA SilentlyContinue) -or (Test-Path (Join-Path $Root $t.d)) -or (Test-Path (Join-Path $H $t.d))
  if (-not $All -and -not $Harness -and -not $found) { continue }
  $SK = if ($User -or [IO.Path]::IsPathRooted($t.ps)) { if ($User) { $t.us } else { $t.ps } } else { Join-Path $Root $t.ps }
  $CM = if ($t.pc -eq '-') { '-' } elseif ($User) { $t.uc } else { Join-Path $Root $t.pc }
  Write-Host "[$($t.n)] skills -> $SK ; commands -> $CM"; if ($DryRun) { continue }
  New-Item -ItemType Directory -Force $SK | Out-Null
  foreach ($s in Get-ChildItem (Join-Path $Plug 'skills') -Directory) { Remove-Item (Join-Path $SK $s.Name) -Recurse -Force -EA SilentlyContinue; Copy-Item $s.FullName (Join-Path $SK $s.Name) -Recurse -Force
    if ($t.n -ne 'claude') { & python3 (Join-Path $Src 'scripts/artifacts.py') strip-frontmatter (Join-Path $SK "$($s.Name)/SKILL.md") | Out-Null } }
  if ($CM -eq '-') { continue }
  foreach ($f in Get-ChildItem (Join-Path $Plug "shims/$($t.n)") -File) {
    $dest = $CM; foreach ($k in $t.x.Keys) { if ($f.Name.EndsWith($k)) { $dest = Join-Path $Root $t.x[$k] } }
    New-Item -ItemType Directory -Force $dest | Out-Null; Copy-Item $f.FullName (Join-Path $dest $f.Name) -Force
  }
}
if ($Scaffold -and -not $DryRun) { & python3 (Join-Path $Src 'scripts/artifacts.py') scaffold --root $Root; & python3 (Join-Path $Src 'scripts/artifacts.py') bridges --root $Root }
& python3 (Join-Path $Src 'scripts/adapters.py') probe
