#Requires -Version 7.0
<#
.SYNOPSIS  Dev Loop orchestrator — PowerShell 7+, git, python3. Mirrors devloop.sh exactly (same adapters.py code path).
.EXAMPLE   pwsh skills/dev-loop/scripts/DevLoop.ps1 -Lanes lanes.json [-Layout auto|wt_grid|detached|headless] [-DryRun] [-Keep] [-Check]
  Any harness can call this from its shell tool; each lane runs in the harness named by lane.worker.harness.
  Exit: 0 all merged; 1 lane failed/partial; 2 VACUOUS lane (never merged); 64 usage.
#>
[CmdletBinding()]
param([string] $Lanes, [ValidateSet('auto','wt_grid','tmux_grid','detached','headless')] [string] $Layout = 'auto',
      [switch] $DryRun, [switch] $Keep, [switch] $Check)
Set-StrictMode -Version Latest; $ErrorActionPreference = 'Stop'
$env:CI = '1'; $env:GIT_TERMINAL_PROMPT = '0'; $env:GIT_PAGER = 'cat'; $env:PAGER = 'cat'; $env:NO_COLOR = '1'
$SkillDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path; $AD = Join-Path $SkillDir 'scripts/adapters.py'
$PY = if ($env:PYTHON) { $env:PYTHON } elseif (Get-Command python3 -EA SilentlyContinue) { 'python3' } else { 'python' }

if ($Check) { foreach ($b in 'git',$PY,'wt.exe','claude','codex','gemini','agy','gitleaks') { '{0,-9} {1}' -f $b, ((Get-Command $b -EA SilentlyContinue).Source ?? '-') }; exit 0 }
if (-not $Lanes) { Write-Error 'usage: DevLoop.ps1 -Lanes lanes.json'; exit 64 }
$Root = (git rev-parse --show-toplevel); if ($LASTEXITCODE) { Write-Error 'not in a git repo'; exit 64 }
Set-Location $Root
$Run = Join-Path $Root ".devloop/run-$(Get-Date -Format yyyyMMdd-HHmmss)"; New-Item -ItemType Directory -Force $Run | Out-Null
$Spec = Join-Path $Run 'lanes.normalized.json'
& $PY $AD validate $Lanes --out $Spec; if ($LASTEXITCODE) { exit 64 }
$S = Get-Content $Spec -Raw | ConvertFrom-Json -AsHashtable
$Base = $S.base_ref; $WtRoot = $S.worktree_root ?? '.worktrees'
if ($Layout -eq 'auto') { $Layout = $S.terminal_layout ?? 'auto' }
if ($Layout -in 'auto','tmux_grid') { $Layout = if (Get-Command wt.exe -EA SilentlyContinue) { 'wt_grid' } else { 'detached' } }
$exclude = '.git/info/exclude'; foreach ($e in '.devloop/run-*/', "$WtRoot/") { if (-not (Test-Path $exclude) -or -not (Select-String -Path $exclude -SimpleMatch -Pattern $e -Quiet)) { Add-Content $exclude $e } }
if ((git status --porcelain | Measure-Object).Count) { Write-Error 'refusing: base tree is dirty'; exit 64 }
$Status = 0

function Field($file, $key) { $d = Get-Content $file -Raw | ConvertFrom-Json -AsHashtable; $v = $d; foreach ($k in $key.Split('.')) { $v = if ($v -is [hashtable]) { $v[$k] } else { $null } }; $v }
function Bump($n) { if ($script:Status -ne 2) { $script:Status = [Math]::Max($script:Status, $n) } elseif ($n -eq 2) { $script:Status = 2 } }

function Launch($Id) {
  $LJ = Join-Path $Run "lane-$Id.json"; & $PY $AD lane $Spec $Id --out $LJ | Out-Null
  $WT = (Field $LJ 'worktree'); if (-not $WT) { $WT = "$WtRoot/$Id" }; $WTA = Join-Path $Root $WT; $BR = "lane/$Id"
  Write-Host "== lane $Id [$(Field $LJ 'worker.harness')] -> $WT ($BR from $Base)"
  if ($DryRun) { return }
  if (Test-Path $WTA) { Write-Host '  worktree exists; reusing' }
  else { git show-ref --verify --quiet "refs/heads/$BR"
    if ($LASTEXITCODE -eq 0) { & $PY $AD git --wt $Root -- worktree add --quiet $WT $BR } else { & $PY $AD git --wt $Root -- worktree add --quiet $WT -b $BR $Base } }
  $Rep = Join-Path $Run "report-$Id.json"; $Log = Join-Path $Run "worker-$Id.log"; $Exit = Join-Path $Run "worker-$Id.exit"
  $Cmd = "& '$PY' '$AD' run --lane '$LJ' --wt '$WTA' --report '$Rep' --log '$Log' --skill '$SkillDir/SKILL.md' --shell pwsh; Set-Content -Path '$Exit' -Value `$LASTEXITCODE"
  switch ($Layout) {
    'headless' { & pwsh -NoProfile -NonInteractive -Command $Cmd }
    'wt_grid'  { $args = @('-w','devloop'); $args += if ($script:panes++ -eq 0) { @('nt') } else { @('sp', $(if ($script:panes % 2) {'-V'} else {'-H'})) }
                 $args += @('--title',"devloop-$Id",'-d',$WTA,'pwsh','-NoProfile','-NoExit','-Command',$Cmd); Start-Process wt.exe -ArgumentList $args }
    default    { Start-Process pwsh -ArgumentList @('-NoProfile','-NonInteractive','-Command',$Cmd) -WorkingDirectory $WTA -WindowStyle Hidden }
  }
}
$script:panes = 0
function WaitLane($Id) { $Exit = Join-Path $Run "worker-$Id.exit"; while (-not (Test-Path $Exit)) { Start-Sleep 20; Write-Host "  … waiting on $Id ($(Get-Date -Format T))" }; Write-Host "  $Id worker exit=$(Get-Content $Exit)" }

function GateMerge($Id) {
  $LJ = Join-Path $Run "lane-$Id.json"; $WT = (Field $LJ 'worktree'); if (-not $WT) { $WT = "$WtRoot/$Id" }; $WTA = Join-Path $Root $WT; $BR = "lane/$Id"; $Rep = Join-Path $Run "report-$Id.json"
  Write-Host "== gate $Id"
  if (-not (Test-Path $Rep)) { Write-Host '  NO REPORT — parking diff'; git -C $WTA diff | Set-Content (Join-Path $Run "lane-$Id.patch"); Bump 1; return }
  $RS = Field $Rep 'status'; Write-Host "  report status=$RS"
  & $PY $AD owned --lane $LJ --wt $WTA; if ($LASTEXITCODE) { git -C $WTA diff | Set-Content (Join-Path $Run "lane-$Id.patch"); Bump 1; return }
  & $PY $AD gate --lane $LJ --wt $WTA --run $Run --shell pwsh; $rc = $LASTEXITCODE
  if ($rc) { Bump $rc; return }
  if ($RS -ne 'done') { Write-Host "  gates hold but the lane says '$RS' — not merging; read $Rep"; Bump 1; return }
  foreach ($p in (Field $LJ 'owned_paths')) { git -C $WTA add -- $p 2>$null }
  if (-not (git -C $WTA diff --cached --name-only)) { Write-Host '  nothing staged — lane produced no change'; return }
  & $PY $AD secrets --wt $WTA; if ($LASTEXITCODE) { git -C $WTA reset -q; Bump 1; return }
  & $PY $AD deps --wt $WTA; if ($LASTEXITCODE) { git -C $WTA reset -q; Bump 1; return }
  $obj = [string](Field $LJ 'objective'); $sum = [string](Field $Rep 'summary'); $TID = [string](Field $LJ 'task_id')
  $msgs = @('-m', ("lane($Id): " + $obj.Substring(0, [Math]::Min(60, $obj.Length))), '-m', $sum.Substring(0, [Math]::Min(600, $sum.Length)),
            '-m', "Verified: positive=$(Field $LJ 'positive_cmd') ; negative=$(Field $LJ 'negative_control_cmd') (named: $(Field $LJ 'negative_expect'))")
  if ($TID) { $msgs += @('-m', "Task-Id: $TID") }
  git -C $WTA commit --quiet @msgs
  if ((git status --porcelain | Measure-Object).Count) { Write-Host '  base tree dirty before merge — halting'; Bump 1; return }
  & $PY $AD git --wt $Root -- merge --no-ff --no-edit $BR | Out-Null
  if ($LASTEXITCODE) { git merge --abort; Write-Host '  MERGE CONFLICT — aborted; worktree and branch kept for review'; Bump 1; return }
  Write-Host "  merged $BR"
  if (-not $Keep) { git worktree remove --force $WT; git branch -D $BR | Out-Null }
  if ($TID -and (Test-Path (Join-Path $Root '.devloop/tasks.jsonl'))) {
    $ART = Join-Path $SkillDir 'scripts/artifacts.py'
    & $PY $ART tasks set $TID done --evidence "lane $Id merged $(git rev-parse --short HEAD); see $Rep" --root $Root | Out-Null
    if (-not $LASTEXITCODE) { & $PY $ART tasks render --root $Root | Out-Null; git add -- .devloop/tasks.jsonl TASKS.md; git commit -q -m "chore(tasks): $TID done" -m "Task-Id: $TID" }
  }
}

foreach ($wave in (& $PY $AD waves $Spec)) {
  $ids = $wave -split ' '
  foreach ($id in $ids) { Launch $id }
  if ($DryRun) { continue }
  foreach ($id in $ids) { WaitLane $id }
  foreach ($id in $ids) { GateMerge $id }
}
if ($DryRun) { Write-Host 'dry run complete'; exit 0 }
if ($S.integration_cmd -and $Status -eq 0) { Write-Host "== integration: $($S.integration_cmd)"; & pwsh -NoProfile -NonInteractive -Command $S.integration_cmd; if ($LASTEXITCODE) { Write-Host '  integration FAILED on base'; $Status = 1 } }
git worktree prune
& $PY $AD ledger --root $Root --status "run-exit-$Status" --objective ([string]($S.objective ?? '')) --next "read $Run/report-*.json; re-plan non-done lanes" 2>$null | Out-Null
git add -- .devloop/LEDGER.md 2>$null; git commit -q -m "chore(devloop): ledger entry (run exit $Status)" 2>$null | Out-Null
Write-Host "== run artefacts: $Run ; exit $Status"; exit $Status
