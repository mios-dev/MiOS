# MiOS PowerShell profile -- PSReadLine reload + fastfetch MOTD +
# oh-my-posh init.
# Source of truth: this file lives on M:\ and is dot-sourced from
# $PROFILE.CurrentUserAllHosts AND from the WT MiOS profile's
# explicit -Command preamble (so it ALWAYS runs in MiOS terminals,
# even when the operator's C:\Users\mios\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1 has its own broken oh-my-posh
# init that would otherwise override ours).
# Self-heals every artifact (mios.omp.json, fastfetch config.jsonc,
# mios.txt ASCII logo) from embedded base64 blobs if the canonical
# disk copy is missing.

# ONCE-PER-SESSION GUARD. This script is dot-sourced from BOTH
# (a) the redirector in $PROFILE.CurrentUserAllHosts AND
# (b) the WT MiOS profile's -Command preamble.
# Without this guard, both pathways fire Show-MiosDashboard +
# oh-my-posh init -- the operator sees TWO stacked framed
# dashboards. Session-scoped flag short-circuits subsequent calls.
if ($Global:MiosProfileLoaded) { return }
$Global:MiosProfileLoaded = $true

# Ensure WinGet machine links directory is in the Path for the current session.
# This prevents PATH drift warnings or command-not-found errors if a user installs
# a global portable package (like claude) and expects it to work in the active shell.
if ($env:Path -notlike "*C:\Program Files\WinGet\Links*") {
    $env:Path += ";C:\Program Files\WinGet\Links"
}

# -- UTF-8 codepage + Console encoding ------------------------------
# Operator-reported regression: powerline glyphs (U+E0B4 etc.) rendered
# as 'î' mojibake -- WT was decoding the UTF-8 bytes as cp1252 because
# this profile body wasn't setting chcp 65001 / Console.OutputEncoding.
# Setting both ensures every glyph oh-my-posh emits to stdout renders
# as the correct PUA cap, not the cp1252-mangled multi-char sequence.
try { & chcp.com 65001 *> $null } catch {}
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch {}
try { [Console]::InputEncoding  = [System.Text.UTF8Encoding]::new($false) } catch {}
try { $OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch {}

# -- Window resize + center (every MiOS pwsh) --------------------
# Dimensions sourced from mios.toml [terminal] (cols/rows/
# scrollback_rows). Per feedback_mios_terminal_dimensions every
# MiOS-spawned window opens at the configured size centered on
# the active monitor. Apply BEFORE any output paints so the
# operator never sees a default-sized window briefly before the
# resize. Idempotent -- a second pass via the inner script
# (Pass-2 elevation) is a no-op.
#
# IMPORTANT GATE: only resize when we're actually in the MiOS APP
# context (i.e. the WT MiOS profile launched us). Otherwise -- if a
# child pwsh during BOOTSTRAP/INSTALL accidentally loads this profile
# via $PROFILE.CurrentUserAllHosts redirector -- the resize shrinks
# the operator's 80x40 install conhost down to the 80x20 MiOS-app
# size mid-install. Operator-reported regression: "window changes to
# the MiOS Global sizes of 80x20 somewhere in the middle of the
# installations". $env:MIOS_APP_CONTEXT is set ONLY by the WT MiOS
# profile commandline (see Install-MiOSTerminalProfile in Get-MiOS.ps1).
if ($env:MIOS_APP_CONTEXT) {
    try {
        $_curW = [Console]::WindowWidth
        if ($_curW -gt 80) {
            [Console]::SetWindowSize(80, 20)
            [Console]::SetBufferSize(80, 9000)
        } else {
            [Console]::SetBufferSize(80, 9000)
            [Console]::SetWindowSize(80, 20)
        }
    } catch {}
}
if ($env:MIOS_APP_CONTEXT) {
    try {
        Add-Type -Namespace MiosWin -Name N -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll")] public static extern System.IntPtr GetConsoleWindow();
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool MoveWindow(System.IntPtr hWnd, int x, int y, int w, int h, bool repaint);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool GetWindowRect(System.IntPtr hWnd, out System.Drawing.Rectangle rect);
'@ -ReferencedAssemblies System.Drawing -ErrorAction SilentlyContinue
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
        $_hwnd = [MiosWin.N]::GetConsoleWindow()
        $_r = New-Object System.Drawing.Rectangle
        [MiosWin.N]::GetWindowRect($_hwnd, [ref]$_r) | Out-Null
        $_w = $_r.Width  - $_r.X
        $_h = $_r.Height - $_r.Y
        # Center on the ACTIVE display (where the cursor currently is),
        # NOT PrimaryScreen. On multi-monitor hosts the operator launches
        # mios.bat from whichever monitor they're working on; the window
        # should land THERE.
        $_cur = [System.Windows.Forms.Cursor]::Position
        $_s   = [System.Windows.Forms.Screen]::FromPoint($_cur).WorkingArea
        $_x = $_s.X + [int](([math]::Max(0, $_s.Width  - $_w)) / 2)
        $_y = $_s.Y + [int](([math]::Max(0, $_s.Height - $_h)) / 2)
        [MiosWin.N]::MoveWindow($_hwnd, $_x, $_y, $_w, $_h, $true) | Out-Null
    } catch {}
}

# NO TERMINAL-TYPE GATE. Always run the PSReadLine reload + oh-my-
# posh init. The WT_SESSION gate on the previous version was
# silently skipping the init when WT didn't set the env var early
# enough -- producing the "theme works in normal terminal but not
# MiOS Terminal" symptom. fastfetch is gated separately below
# since its ASCII rendering only makes sense in a real terminal.
if ($true) {

    # -- Import terminal completion modules ------------------------
    # Silent best-effort: each module is imported if installed,
    # skipped if not. Operator gets icon-aware ls (Terminal-Icons),
    # git tab-completion (posh-git), AI-style prediction
    # (CompletionPredictor), and command-not-found suggestions
    # (Microsoft.WinGet.CommandNotFound).
    foreach ($mod in @('Terminal-Icons','posh-git','CompletionPredictor','Microsoft.WinGet.CommandNotFound')) {
        if (Get-Module -ListAvailable -Name $mod -ErrorAction SilentlyContinue) {
            try { Import-Module $mod -ErrorAction SilentlyContinue } catch {}
        }
    }

    # -- PSReadLine reload -----------------------------------------
    # PowerShell 7.x ships with an in-box PSReadLine that's too old
    # for oh-my-posh init's Get-PSReadLineKeyHandler -Chord syntax.
    # Updating PSReadLine on disk (Install-Module) doesn't help the
    # CURRENT session because PSReadLine is autoloaded BEFORE the
    # profile runs. Force-import the newest installed version here
    # so oh-my-posh init's PSReadLine integration doesn't throw
    # "A positional parameter cannot be found that accepts argument
    # 'Spacebar'/'Enter'/'Ctrl+c'".
    try {
        $latestPSRL = Get-Module -ListAvailable -Name PSReadLine |
                       Sort-Object Version -Descending | Select-Object -First 1
        if ($latestPSRL -and $latestPSRL.Version -ge [version]'2.3.5') {
            Import-Module PSReadLine -RequiredVersion $latestPSRL.Version -Force -ErrorAction SilentlyContinue
        }
    } catch {}

    # -- Resolve / self-heal MiOS artifact paths -------------------
    # M:\-everywhere invariant (operator: "irm|iex sets up M:\
    # disk/partition installs EVERYTHING to M:\ EVERYTHING").
    # M:\ is created at install time and never removed at runtime;
    # if it's missing, the install never completed and the operator
    # needs to re-run irm|iex.  The profile body falls back to a
    # warn rather than silently splitting state across drives.
    $miosArtifactRoot = 'M:\MiOS'
    if (-not (Test-Path -LiteralPath $miosArtifactRoot)) {
        Write-Host "  [!] M:\MiOS not found -- re-run the irm|iex bootstrap to provision M:\." -ForegroundColor Yellow
    }
    function _MiosSelfHeal {
        param([string]$RelDir, [string]$FileName, [string]$Blob)
        $dir = Join-Path $miosArtifactRoot $RelDir
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        $path = Join-Path $dir $FileName
        if (-not (Test-Path -LiteralPath $path)) {
            try { [System.IO.File]::WriteAllBytes($path, [Convert]::FromBase64String($Blob)) } catch { return $null }
        }
        return $path
    }

    # oh-my-posh config -- probe canonical paths, self-heal if missing.
    $miosOmp = $null
    $ompCands = @()
    if ($env:MIOS_OMP_JSON) { $ompCands += $env:MIOS_OMP_JSON }
    $ompCands += @(
        'M:\MiOS\themes\mios.omp.json',
        'M:\usr\share\mios\oh-my-posh\mios.omp.json'
    )
    # C:\* deliberately excluded -- M:\-everywhere invariant
    # (operator: EVERYTHING to M:\, no LOCALAPPDATA / C:\MiOS leaks).
    foreach ($c in $ompCands) {
        if ($c -and (Test-Path -LiteralPath $c)) { $miosOmp = $c; break }
    }
    if (-not $miosOmp) {
        $miosOmp = _MiosSelfHeal 'themes' 'mios.omp.json' 'ewogICIkc2NoZW1hIjogImh0dHBzOi8vcmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbS9KYW5EZURvYmJlbGVlci9vaC1teS1wb3NoL21haW4vdGhlbWVzL3NjaGVtYS5qc29uIiwKICAidmVyc2lvbiI6IDQsCiAgImZpbmFsX3NwYWNlIjogZmFsc2UsCiAgIi8vIjogWwogICAgIk1pT1MgT2gtTXktUG9zaCB0aGVtZS4iLAogICAgIkRFVEVSTUlOSVNUSUMgVFdPLUxJTkUgTEFZT1VUICgyMDI2LTA1LTEwIHJlZGVzaWduKTogdGhlIHByaW9yIiwKICAgICJsZWZ0K3JpZ2h0IGFsaWdubWVudCBzY2hlbWUgb3ZlcmZsb3dlZCB0byBhIDNyZCBsaW5lIG9uIDgweDIwIiwKICAgICJ0ZXJtaW5hbHMgYmVjYXVzZSBvaC1teS1wb3NoJ3MgcmlnaHQtYmxvY2sgYWxpZ25tZW50IG1hdGggc2F3IiwKICAgICJ0aGUgdHJhaWxpbmcgNi1OQlNQIGJ1ZmZlciArIHJpZ2h0X21hcmdpbiBhcyBwYXJ0IG9mIHRoZSByaWdodCIsCiAgICAiYmxvY2sncyByZW5kZXIgd2lkdGggYW5kIHRyaWdnZXJlZCBhbiBlYXJseSB3cmFwLiBPcGVyYXRvci0iLAogICAgInJlcG9ydGVkIGFzICdwb3dlcmxpbmVzIHdyYXAgaW5jb3JyZWN0bHknIHdpdGggc2NyZWVuc2hvdC4iLAogICAgIiIsCiAgICAiTmV3IGxheW91dDoiLAogICAgIiAgTGluZSAxIChibG9jayAxKTogbGVhZGVyIGNhcCArIHNoZWxsICsgcGF0aCArIGdpdCArIGV4ZWN0aW1lIiwKICAgICIgICAgICAgICAgICAgICAgICAgICsgV1NML09TIGluZGljYXRvciArIEhIOk1NIHRpbWUsIGFsbCBwYWNrZWQiLAogICAgIiAgICAgICAgICAgICAgICAgICAgTEVGVC1hbGlnbmVkIC0tIG5vIHJpZ2h0IGFsaWdubWVudCwgbm8iLAogICAgIiAgICAgICAgICAgICAgICAgICAgY3Jvc3MtYmxvY2sgbWF0aCwgbm8gd3JhcCByaXNrLiIsCiAgICAiICBMaW5lIDIgKGJsb2NrIDIpOiBjbG9zZXIgY2FwICsgY2hldnJvbiBwcm9tcHQgYXJyb3cuIiwKICAgICIiLAogICAgIkFsbCBzZWdtZW50cyBzdGlsbCBwdWxsIGdseXBocyBmcm9tIG1pb3MudG9tbCBbdGhlbWUucHJvbXB0XSIsCiAgICAidmlhIHRoZSBwb3N0LWluc3RhbGwgdGVtcGxhdGUgc3Vic3RpdHV0aW9uIGluIiwKICAgICJJbnN0YWxsLU1pT1NPaE15UG9zaFRoZW1lLiBQYWxldHRlOiBtaW9zLnRvbWwgW2NvbG9yc10gKEhva3VzYWkgKyIsCiAgICAib3BlcmF0b3IgbmV1dHJhbHMpLiBMYW5ndWFnZSBzZWdtZW50cyAobm9kZS9weXRob24vZ28vcnVzdC9kb3RuZXQpIiwKICAgICJhbmQgY29uZGl0aW9uYWwgaW5mcmFzdHJ1Y3R1cmUgc2VnbWVudHMgKGt1YmVjdGwvYXdzL2JhdHRlcnkpIiwKICAgICJyZW1vdmVkIC0tIHRoZXkgcG9sbHV0ZSB0aGUgbGluZSBhbmQgcmFyZWx5IHJlbmRlciBtZWFuaW5nZnVsbHkiLAogICAgIm9uIHRoZSBkZXYgVk0uIE9wZXJhdG9ycyB3aG8gbmVlZCB0aGVtIGNhbiBhZGQgdmlhIG1pb3MuaHRtbC4iLAogICAgIiIsCiAgICAiUG93ZXJsaW5lIGNhcCBnbHlwaDogVStFMEI0IChyb3VuZGVkIHJpZ2h0IGhhbGYtY2lyY2xlKS4gR2Vpc3QiLAogICAgIk1vbm8gTmVyZCBGb250IGhhcyBmdWxsIFBvd2VybGluZSBjb3ZlcmFnZTsgdGhlIHByZXZpb3VzIGRlc2lnbiIsCiAgICAidXNlZCBcIlwiIChlbXB0eSkgd2hpY2ggcHJvZHVjZWQgYWJ1dHRpbmcgc3F1YXJlIGNvbG9yIGJsb2NrcyAtLSIsCiAgICAib3BlcmF0b3ItZmxhZ2dlZCAyMDI2LTA1LTEwICdwaXBlbGluIGlzbid0IHJvdW5kZWQgYW55bW9yZScuIgogIF0sCiAgImJsb2NrcyI6IFsKICAgIHsKICAgICAgInR5cGUiOiAicHJvbXB0IiwKICAgICAgImFsaWdubWVudCI6ICJsZWZ0IiwKICAgICAgInNlZ21lbnRzIjogWwogICAgICAgIHsKICAgICAgICAgICIvLyI6ICJMZWFkaW5nIHByb21wdCBjYXAuIEJveC1kcmF3aW5nIGNoYXJzIChVKzI1NkQgLyBVKzI1MDApIGFyZSBndWFyYW50ZWVkIGluIGFueSBtb25vc3BhY2UgZm9udDsgdGhlIFUrRTBCNiByb3VuZGVkLWNhcCBQVUEgYXBwcm9hY2ggd2UgdHJpZWQgaW4gdjEgd2FzIHVucmVsaWFibGUgb24gb3BlcmF0b3IncyBHZWlzdE1vbm8gTmVyZCBGb250IE1vbm8gYnVpbGQgKGNhcCBnbHlwaCBuZXZlciBzdXJmYWNlZCwgbGVhdmluZyBjb2xzIDAtMiBibGFuaykuIiwKICAgICAgICAgICJ0eXBlIjogInRleHQiLAogICAgICAgICAgInN0eWxlIjogInBsYWluIiwKICAgICAgICAgICJmb3JlZ3JvdW5kIjogIiNCN0M5RDciLAogICAgICAgICAgInRlbXBsYXRlIjogIuKVreKUgCIKICAgICAgICB9LAogICAgICAgIHsKICAgICAgICAgICJ0eXBlIjogInNoZWxsIiwKICAgICAgICAgICJzdHlsZSI6ICJwb3dlcmxpbmUiLAogICAgICAgICAgInBvd2VybGluZV9zeW1ib2wiOiAi7oK0IiwKICAgICAgICAgICJiYWNrZ3JvdW5kIjogIiMxQTQwN0YiLAogICAgICAgICAgImZvcmVncm91bmQiOiAiI0U3REZEMyIsCiAgICAgICAgICAidGVtcGxhdGUiOiAiICB7eyAuTmFtZSB9fSAiCiAgICAgICAgfSwKICAgICAgICB7CiAgICAgICAgICAidHlwZSI6ICJyb290IiwKICAgICAgICAgICJzdHlsZSI6ICJwb3dlcmxpbmUiLAogICAgICAgICAgInBvd2VybGluZV9zeW1ib2wiOiAi7oK0IiwKICAgICAgICAgICJiYWNrZ3JvdW5kIjogIiNEQzI3MUIiLAogICAgICAgICAgImZvcmVncm91bmQiOiAiI0YzNUMxNSIsCiAgICAgICAgICAidGVtcGxhdGUiOiAiICAiCiAgICAgICAgfSwKICAgICAgICB7CiAgICAgICAgICAidHlwZSI6ICJwYXRoIiwKICAgICAgICAgICJzdHlsZSI6ICJwb3dlcmxpbmUiLAogICAgICAgICAgInBvd2VybGluZV9zeW1ib2wiOiAi7oK0IiwKICAgICAgICAgICJiYWNrZ3JvdW5kIjogIiNGMzVDMTUiLAogICAgICAgICAgImZvcmVncm91bmQiOiAiIzI4MjI2MiIsCiAgICAgICAgICAicHJvcGVydGllcyI6IHsKICAgICAgICAgICAgImZvbGRlcl9pY29uIjogIiAgIiwKICAgICAgICAgICAgImhvbWVfaWNvbiI6ICIiLAogICAgICAgICAgICAic3R5bGUiOiAiYWdub3N0ZXJfc2hvcnQiLAogICAgICAgICAgICAibWF4X2RlcHRoIjogMwogICAgICAgICAgfSwKICAgICAgICAgICJ0ZW1wbGF0ZSI6ICIgIHt7IC5QYXRoIH19ICIKICAgICAgICB9LAogICAgICAgIHsKICAgICAgICAgICJ0eXBlIjogImdpdCIsCiAgICAgICAgICAic3R5bGUiOiAicG93ZXJsaW5lIiwKICAgICAgICAgICJwb3dlcmxpbmVfc3ltYm9sIjogIu6CtCIsCiAgICAgICAgICAiYmFja2dyb3VuZCI6ICIjM0U3NzY1IiwKICAgICAgICAgICJiYWNrZ3JvdW5kX3RlbXBsYXRlcyI6IFsKICAgICAgICAgICAgInt7IGlmIG9yICguV29ya2luZy5DaGFuZ2VkKSAoLlN0YWdpbmcuQ2hhbmdlZCkgfX0jRjM1QzE1e3sgZW5kIH19IiwKICAgICAgICAgICAgInt7IGlmIGFuZCAoZ3QgLkFoZWFkIDApIChndCAuQmVoaW5kIDApIH19I0RDMjcxQnt7IGVuZCB9fSIsCiAgICAgICAgICAgICJ7eyBpZiBndCAuQWhlYWQgMCB9fSMxQTQwN0Z7eyBlbmQgfX0iLAogICAgICAgICAgICAie3sgaWYgZ3QgLkJlaGluZCAwIH19IzczNEYzOXt7IGVuZCB9fSIKICAgICAgICAgIF0sCiAgICAgICAgICAiZm9yZWdyb3VuZCI6ICIjMjgyMjYyIiwKICAgICAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICAgICAiYnJhbmNoX2ljb24iOiAiICIsCiAgICAgICAgICAgICJmZXRjaF9zdGF0dXMiOiB0cnVlLAogICAgICAgICAgICAiZmV0Y2hfdXBzdHJlYW1faWNvbiI6IHRydWUKICAgICAgICAgIH0sCiAgICAgICAgICAidGVtcGxhdGUiOiAiICB7eyAuVXBzdHJlYW1JY29uIH19e3sgLkhFQUQgfX17eyBpZiAuQnJhbmNoU3RhdHVzIH19IHt7IC5CcmFuY2hTdGF0dXMgfX17eyBlbmQgfX17eyBpZiAuV29ya2luZy5DaGFuZ2VkIH19IOKcjnt7IC5Xb3JraW5nLlN0cmluZyB9fXt7IGVuZCB9fXt7IGlmIGFuZCAoLldvcmtpbmcuQ2hhbmdlZCkgKC5TdGFnaW5nLkNoYW5nZWQpIH19IHx7eyBlbmQgfX17eyBpZiAuU3RhZ2luZy5DaGFuZ2VkIH19PCNEQzI3MUI+ICt7eyAuU3RhZ2luZy5TdHJpbmcgfX08Lz57eyBlbmQgfX0gIgogICAgICAgIH0sCiAgICAgICAgewogICAgICAgICAgInR5cGUiOiAiZXhlY3V0aW9udGltZSIsCiAgICAgICAgICAic3R5bGUiOiAicG93ZXJsaW5lIiwKICAgICAgICAgICJwb3dlcmxpbmVfc3ltYm9sIjogIu6CtCIsCiAgICAgICAgICAiYmFja2dyb3VuZCI6ICIjOTQ4RThFIiwKICAgICAgICAgICJmb3JlZ3JvdW5kIjogIiMyODIyNjIiLAogICAgICAgICAgInByb3BlcnRpZXMiOiB7CiAgICAgICAgICAgICJzdHlsZSI6ICJyb3VuZHJvY2siLAogICAgICAgICAgICAidGhyZXNob2xkIjogMAogICAgICAgICAgfSwKICAgICAgICAgICJ0ZW1wbGF0ZSI6ICIgIHt7IC5Gb3JtYXR0ZWRNcyB9fSAiCiAgICAgICAgfSwKICAgICAgICB7CiAgICAgICAgICAiLy8iOiAiQ29tcGFjdCBPUyBpbmRpY2F0b3IgLS0ganVzdCB0aGUgcGxhdGZvcm0gZ2x5cGgsIG5vICdXU0wgYXQnIHByb3NlLiBTYXZlcyBjZWxsczsgdGhlIGZyYW1lZCBkYXNoYm9hcmQgYWxyZWFkeSBuYW1lcyB0aGUgaG9zdCBraW5kIGV4cGxpY2l0bHkuIiwKICAgICAgICAgICJ0eXBlIjogIm9zIiwKICAgICAgICAgICJzdHlsZSI6ICJwb3dlcmxpbmUiLAogICAgICAgICAgInBvd2VybGluZV9zeW1ib2wiOiAi7oK0IiwKICAgICAgICAgICJiYWNrZ3JvdW5kIjogIiNCN0M5RDciLAogICAgICAgICAgImZvcmVncm91bmQiOiAiIzI4MjI2MiIsCiAgICAgICAgICAicHJvcGVydGllcyI6IHsKICAgICAgICAgICAgImxpbnV4IjogIiIsCiAgICAgICAgICAgICJtYWNvcyI6ICIiLAogICAgICAgICAgICAid2luZG93cyI6ICIiCiAgICAgICAgICB9LAogICAgICAgICAgInRlbXBsYXRlIjogIiB7eyAuSWNvbiB9fSAiCiAgICAgICAgfSwKICAgICAgICB7CiAgICAgICAgICAidHlwZSI6ICJ0aW1lIiwKICAgICAgICAgICJzdHlsZSI6ICJwb3dlcmxpbmUiLAogICAgICAgICAgInBvd2VybGluZV9zeW1ib2wiOiAi7oK0IiwKICAgICAgICAgICJiYWNrZ3JvdW5kIjogIiMxQTQwN0YiLAogICAgICAgICAgImZvcmVncm91bmQiOiAiI0U3REZEMyIsCiAgICAgICAgICAicHJvcGVydGllcyI6IHsKICAgICAgICAgICAgInRpbWVfZm9ybWF0IjogIjE1OjA0IgogICAgICAgICAgfSwKICAgICAgICAgICJ0ZW1wbGF0ZSI6ICIge3sgLkN1cnJlbnREYXRlIHwgZGF0ZSAuRm9ybWF0IH19ICIKICAgICAgICB9CiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJ0eXBlIjogInByb21wdCIsCiAgICAgICJhbGlnbm1lbnQiOiAibGVmdCIsCiAgICAgICJuZXdsaW5lIjogdHJ1ZSwKICAgICAgInNlZ21lbnRzIjogWwogICAgICAgIHsKICAgICAgICAgICIvLyI6ICJDbG9zZXIgY2FwICsgcHJvbXB0IGFycm93LiBTdGF0dXMtdGludGVkOiB0aW50cyB0aGUgd2hvbGUgYOKVsOKUgCDina9gIHJlZCBvbiBub24temVybyBleGl0IGNvZGUgKC5Db2RlID4gMCksIHBhbGUtYmx1ZSBvdGhlcndpc2UgKG1hdGNoZXMgdGhlIGxlYWRpbmcgYOKVreKUgGAgY2FwIGZvciB2aXN1YWwgc3ltbWV0cnkpLiIsCiAgICAgICAgICAidHlwZSI6ICJzdGF0dXMiLAogICAgICAgICAgInN0eWxlIjogInBsYWluIiwKICAgICAgICAgICJmb3JlZ3JvdW5kIjogIiNCN0M5RDciLAogICAgICAgICAgImZvcmVncm91bmRfdGVtcGxhdGVzIjogWwogICAgICAgICAgICAie3sgaWYgZ3QgLkNvZGUgMCB9fSNEQzI3MUJ7eyBlbmQgfX0iCiAgICAgICAgICBdLAogICAgICAgICAgInByb3BlcnRpZXMiOiB7CiAgICAgICAgICAgICJhbHdheXNfZW5hYmxlZCI6IHRydWUKICAgICAgICAgIH0sCiAgICAgICAgICAidGVtcGxhdGUiOiAi4pWw4pSAIOKdryAiCiAgICAgICAgfQogICAgICBdCiAgICB9CiAgXQp9Cg=='
    }

    # -- Framed MiOS dashboard (mirrors mios-dashboard.sh from mios.git) -
    # 80-col fixed frame, centered ASCII logo, framed fastfetch info.
    # Gated on WT_SESSION since the +-+ box-drawing only renders
    # properly in WT (conhost / VS Code embedded shell mangles it).
    function Show-MiosDashboard {
        param([string]$ConfigPath, [string]$LogoPath, [switch]$Full)
        # Width adapts to LIVE terminal width every render so the dashboard
        # always renders edge-to-edge. "dashboards
        # should be edge to edge globally!! 80x20 window is the Global
        # benchmark!" + "opening MiOS app and using things like fastfetch
        # and btop--things that clear the screen; ends up fitting the
        # dashboards in the same original window and tab--eventually".
        #
        # First-render timing: at session start, WT hasn't settled the
        # cell count yet. Solution: poll WindowWidth up to 5x with a
        # 50ms gap until it stabilizes (two consecutive reads agree),
        # then use the stable value. After fastfetch/btop run, WT has
        # fully settled and subsequent renders read correctly.
        $_widthA = 0; $_widthB = 0
        for ($_i = 0; $_i -lt 5; $_i++) {
            $_widthB = $_widthA
            $_winC = try { [Console]::WindowWidth } catch { 0 }
            $_winR = try { $Host.UI.RawUI.WindowSize.Width } catch { 0 }
            $_widthA = if ($_winC -gt 0 -and $_winR -gt 0) { [math]::Min($_winC, $_winR) }
                        elseif ($_winC -gt 0) { $_winC }
                        elseif ($_winR -gt 0) { $_winR }
                        else { 0 }
            if ($_widthA -gt 0 -and $_widthA -eq $_widthB) { break }
            if ($_i -lt 4) { Start-Sleep -Milliseconds 50 }
        }
        $_winWNow = if ($_widthA -gt 0) { $_widthA } else { 80 }
        $WIDTH = $_winWNow - 0
        # Cap to mios.toml [terminal].frame_width (SSOT). WT's
        # WindowWidth poll is unreliable during the first ~200ms after
        # spawn -- it can return a value 4-8 cells wider than the
        # final viewport (focus-mode + acrylic backdrop allocation
        # haven't settled). Without this cap, host_os/CPU/font lines
        # render at the inflated WIDTH, then WT re-sizes the buffer
        # narrower, and every overflowing line wraps -- pushing the
        # top frame off-viewport. Capping to the toml value (the
        # operator-declared "this is what 80x20 means") guarantees
        # the dashboard never renders wider than the declared frame.
        # Operator-flagged "ie..." / "on..." wraps in
        # MiOS-WIN dashboard with top frame clipped off-screen.
        if (80 -gt 0 -and $WIDTH -gt 80) {
            $WIDTH = 80
        }
        if ($WIDTH -lt 20) { $WIDTH = [math]::Max(20, $_winWNow) }
        $INNER = $WIDTH - 4
        # $H is a STRING (not [char]): the frame borders build with `$H * n`,
        # and PowerShell's `*` is undefined for [char] (it threw "[Char] *
        # [Int32] is not defined" -> Show-MiosDashboard never rendered, so the
        # framed Windows dashboard silently fell back to nothing and only the
        # fastfetch `mios dash` view showed). String repeat gives the border.
        $TL=[char]0x256d; $TR=[char]0x256e; $BL=[char]0x2570; $BR=[char]0x256f; $LT=[char]0x251c; $RT=[char]0x2524; $V=[char]0x2502; $H=[string][char]0x2500

        # Uniform frame color -- per "make the
        # entire frame 1 uniform colour--make it a complimenting colour
        # to the windows colour that's sourced from the toml fields that
        # are relevant to MiOS's color palette colours". MiOS canonical
        # accent (mios.toml [colors].accent + [branding.dashboard].frame_color)
        # is operator-blue (#1A407F = ANSI 34 = [ConsoleColor]::Blue).
        # Embed ANSI 34 around every $V border so the per-content rows
        # render their borders in the SAME color as the standalone
        # top/divider/bottom Write-Host calls (which use
        # -ForegroundColor Blue). Without this, _Frame/_Center returned
        # a plain string that Write-Host emitted in the inherited
        # foreground (often cream from the MiOS scheme), making per-row
        # borders visually different from top/divider/bottom borders.
        $_esc      = [char]27
        $_FrameC   = "$_esc[34m"
        $_FrameR   = "$_esc[0m"

        function _Strip { param($s) $s -replace '\x1b\[[0-9;]*m','' }
        function _Frame {
            param([string]$Line)
            $visible = _Strip $Line
            if ($visible.Length -gt $INNER) {
                # Truncate with ellipsis preserving ANSI prefix.
                $Line = $Line.Substring(0, [math]::Min($Line.Length, $INNER + ($Line.Length - $visible.Length) - 1)) + '…'
                $visible = _Strip $Line
            }
            $pad = ' ' * [math]::Max(0, $INNER - $visible.Length)
            "$_FrameC$V$_FrameR $Line$pad$_FrameC $V$_FrameR"
        }
        function _Center {
            param([string]$Line)
            $visible = _Strip $Line
            $totalPad = [math]::Max(0, $INNER - $visible.Length)
            $lpad = ' ' * [math]::Floor($totalPad / 2)
            $rpad = ' ' * ($totalPad - [math]::Floor($totalPad / 2))
            "$_FrameC$V$_FrameR $lpad$Line$rpad$_FrameC $V$_FrameR"
        }

        # Total budget: frame_height rows total. Layout:
        #   1 top frame
        #   logo block       (compact: 0-1 row -- title only;
        #                     full:    N-row ASCII when budget allows)
        #   1 divider
        #   fastfetch block  (paired -- two modules per row)
        #   1 divider
        #   hints block      (compact: 1 line; full: 1-line-per-verb)
        #   1 bottom frame
        # Per operator: dashboard MUST fit in 80x20 (= frame_height 19).
        # Compact mode kicks in when frame_height < 25.
        # -Full (the `mios dash` view) forces the banner/logo full layout to
        # match the Linux `mios dash`. Otherwise compact when the window is too
        # short to fit the logo + every section (the 80x20 `mios mini`). The
        # previous `19 -lt 25` was a hardcoded literal that was ALWAYS true, so
        # the full framed view was unreachable -- read the live window height.
        $_winH = try { [Console]::WindowHeight } catch { 0 }
        if ($_winH -le 0) { $_winH = try { $Host.UI.RawUI.WindowSize.Height } catch { 0 } }
        $_compact = if ($Full) { $false } elseif ($_winH -gt 0) { $_winH -lt 25 } else { $true }
        # Reserve rows for top + divider + divider + hints + bottom.
        # Compact hints = 1 row; full hints = 7 rows.
        $_hintsRows  = if ($_compact) { 1 } else { 7 }
        $_overhead   = 1 + 1 + 1 + $_hintsRows + 1   # top + 2 dividers + hints + bottom
        # Logo + fastfetch share whatever's left.
        $_contentBudget = [math]::Max(2, 19 - $_overhead)
        # In compact mode skip the multi-line ASCII logo entirely; in
        # full mode allocate up to half the content budget to the logo.
        $_logoBudget = if ($_compact) { 1 } else { [math]::Min(11, [math]::Floor($_contentBudget / 2)) }
        $_ffBudget   = $_contentBudget - $_logoBudget

        # Read mios.toml ONCE up-front so [dashboard].title (here),
        # [dashboard].rows + [theme.font] (further down) all read from
        # the same in-memory copy.  No fallback to other paths -- the
        # canonical layout is M:\etc\mios (host overlay) > M:\usr\share
        # (vendor on M:\).
        $_dashTomlText = $null
        foreach ($_tc in @('M:\etc\mios\mios.toml','M:\usr\share\mios\mios.toml')) {
            if (Test-Path -LiteralPath $_tc) {
                try { $_dashTomlText = [IO.File]::ReadAllText($_tc, (New-Object System.Text.UTF8Encoding($false))); break } catch {}
            }
        }

        # Top frame.
        Write-Host ($TL + ($H * ($WIDTH - 2)) + $TR) -ForegroundColor Blue
        if ($_compact) {
            # 1-line title band -- resolves through mios.toml [dashboard].title
            # at runtime so the configurator HTML edits flow through to the
            # next render.  Vendor default is the technical descriptor
            # ("MiOS  --  Immutable Fedora AI Workstation"); operators who
            # want the friendly "My Personal Operating System" face on the
            # dashboard subtitle override [dashboard].title via mios.html.
            $title = 'MiOS  --  My Personal Operating System'
            if ($_dashTomlText) {
                $_titleM = [regex]::Match($_dashTomlText, '(?ms)^\[dashboard\]\s*\r?\n.*?^\s*title\s*=\s*"([^"]+)"')
                if ($_titleM.Success) { $title = $_titleM.Groups[1].Value }
            }
            Write-Host (_Center $title) -ForegroundColor Blue
        }
        elseif ($LogoPath -and (Test-Path -LiteralPath $LogoPath)) {
            # Centered ASCII logo (operator-blue). Center the BLOCK (not
            # each line individually) -- the logo's internal alignment
            # depends on each line's leading whitespace.
            # Skip the AI-tagging `#` header lines the logo file carries (the
            # Linux dashboard skips ^# too) so the banner -- not a comment --
            # renders.
            $logoLines = @(Get-Content -LiteralPath $LogoPath) | Where-Object { $_ -ne $null -and $_ -notmatch '^\s*#' }
            # The full view (mios dash) shows the whole banner to match the
            # Linux dash; only the compact window path caps to the frame_height.
            if (-not $Full -and $logoLines.Count -gt $_logoBudget) {
                $logoLines = $logoLines[0..([math]::Max(0, $_logoBudget - 1))]
            }
            $maxLen = 0
            foreach ($ll in $logoLines) {
                $len = (_Strip $ll).Length
                if ($len -gt $maxLen) { $maxLen = $len }
            }
            $blockLPad = ' ' * [math]::Max(0, [math]::Floor(($INNER - $maxLen) / 2))
            foreach ($ll in $logoLines) {
                $stripped = _Strip $ll
                $rPad = ' ' * [math]::Max(0, $maxLen - $stripped.Length)
                Write-Host (_Frame ($blockLPad + $ll + $rPad)) -ForegroundColor Blue
            }
        }
        # Divider.
        Write-Host ($LT + ($H * ($WIDTH - 2)) + $RT) -ForegroundColor Blue

        # -- Compact metric rows ---------------------------------
        # Driven by mios.toml [dashboard].rows -- side-by-side fields
        # per row keep the dashboard at ~5 metric rows so 80x20 leaves
        # ample room for the prompt and command output.  Per operator
        # "the dash is set GLOBALLY to Windows and Linux
        # dashboards!! same settings!!! ... smaller metric can be
        # side-by-side in the dash; freeing up more room for the
        # prompt field."  The Linux-side mios-dashboard.sh reads the
        # same [dashboard] section.
        #
        # Field renderers fetch values via Get-CimInstance (single-
        # cached) / Get-Volume / $PSVersionTable.  They each return a
        # short labeled string ("CPU AMD Ryzen 9 9950X3D 5.75GHz (32c)").
        # Unknown field-keys are silently skipped so the dashboard
        # is forward-compatible with future mios.toml additions.
        $_dashCache = @{}
        $_DashGetField = {
            param([string]$_k, [string]$_fontFam, [int]$_fontSz)
            switch ($_k) {
                'host_os' {
                    if (-not $_dashCache.ContainsKey('_os')) {
                        $_dashCache['_os'] = try { Get-CimInstance Win32_OperatingSystem -ErrorAction Stop } catch { $null }
                    }
                    $_o = $_dashCache['_os']
                    # Compact OS caption: strip Microsoft prefix, the
                    # "for Workstations" SKU suffix, "Insider Preview"
                    # marketing, "(64-bit)" arch (it's redundant -- the
                    # arch line covers it), and trailing whitespace.
                    # Operator-flagged "Windows 11 Pro for
                    # Workstations Insider Preview" overflowed the 80x20
                    # frame and wrapped, pushing the top frame off-screen.
                    $_cap = if ($_o -and $_o.Caption) { (((((($_o.Caption -replace 'Microsoft\s*','') -replace '\s+for\s+Workstations','') -replace '\s+Insider\s+Preview','') -replace '\s*\(64-?bit\)','') -replace '\s*N\s+Edition','')).Trim() } else { 'Windows' }
                    return "$env:USERNAME@$env:COMPUTERNAME -- $_cap".Trim()
                }
                'cpu' {
                    if (-not $_dashCache.ContainsKey('_cpu')) {
                        $_dashCache['_cpu'] = try { Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1 } catch { $null }
                    }
                    $_c = $_dashCache['_cpu']
                    if (-not $_c) { return 'CPU --' }
                    $_n = ($_c.Name -replace '\s+@.*','' -replace '\s+Processor','' -replace '\(R\)','' -replace '\(TM\)','').Trim()
                    $_clk = if ($_c.MaxClockSpeed) { [math]::Round($_c.MaxClockSpeed / 1000.0, 2) } else { 0 }
                    $_co  = $_c.NumberOfLogicalProcessors
                    return "CPU $_n ${_clk}GHz (${_co}c)"
                }
                {$_ -in 'gpu_discrete','gpu_integrated'} {
                    if (-not $_dashCache.ContainsKey('_gpus')) {
                        $_dashCache['_gpus'] = try { @(Get-CimInstance Win32_VideoController -ErrorAction Stop) } catch { @() }
                    }
                    $_gs = $_dashCache['_gpus']
                    if (-not $_gs -or $_gs.Count -eq 0) { return 'GPU --' }
                    if ($_k -eq 'gpu_discrete') {
                        $_g = $_gs | Where-Object { $_.Name -match 'NVIDIA|GeForce|RTX|GTX|Quadro|Radeon RX|Radeon Pro' } | Select-Object -First 1
                        if (-not $_g) { $_g = $_gs | Sort-Object @{e={$_.AdapterRAM};Descending=$true} | Select-Object -First 1 }
                    } else {
                        $_g = $_gs | Where-Object { $_.Name -match 'Radeon\(TM\) Graphics|Intel.*Graphics|UHD Graphics' } | Select-Object -First 1
                        if (-not $_g) { return '' }
                    }
                    if (-not $_g) { return 'GPU --' }
                    $_n = ($_g.Name -replace 'NVIDIA GeForce ','' -replace 'NVIDIA ','' -replace '\(R\)','' -replace '\(TM\)','').Trim()
                    $_vr = if ($_g.AdapterRAM) { [math]::Round(([uint32]$_g.AdapterRAM) / 1GB, 1) } else { 0 }
                    if ($_vr -le 0) { return "GPU $_n" }
                    return "GPU $_n ${_vr}GiB"
                }
                'ram' {
                    if (-not $_dashCache.ContainsKey('_os')) {
                        $_dashCache['_os'] = try { Get-CimInstance Win32_OperatingSystem -ErrorAction Stop } catch { $null }
                    }
                    $_o = $_dashCache['_os']
                    if (-not $_o) { return 'RAM --' }
                    $_tot = [math]::Round(([int64]$_o.TotalVisibleMemorySize) / 1MB, 1)
                    $_use = [math]::Round((([int64]$_o.TotalVisibleMemorySize - [int64]$_o.FreePhysicalMemory)) / 1MB, 1)
                    $_pct = if ($_o.TotalVisibleMemorySize -gt 0) { [math]::Round((($_use / $_tot) * 100), 0) } else { 0 }
                    return "RAM ${_use} / ${_tot}GiB (${_pct}%)"
                }
                'swap' {
                    if (-not $_dashCache.ContainsKey('_pf')) {
                        $_dashCache['_pf'] = try { Get-CimInstance Win32_PageFileUsage -ErrorAction Stop } catch { $null }
                    }
                    $_p = @($_dashCache['_pf'])
                    if (-not $_p -or $_p.Count -eq 0 -or -not $_p[0]) { return 'Swap --' }
                    $_tot = [math]::Round(($_p | Measure-Object AllocatedBaseSize -Sum).Sum / 1024.0, 1)
                    $_use = [math]::Round(($_p | Measure-Object CurrentUsage -Sum).Sum / 1024.0, 1)
                    $_pct = if ($_tot -gt 0) { [math]::Round((($_use / $_tot) * 100), 0) } else { 0 }
                    return "Swap ${_use} / ${_tot}GiB (${_pct}%)"
                }
                {$_ -match '^disk_([a-zA-Z])$'} {
                    # PowerShell switch with regex condition matches but
                    # does NOT reliably populate $Matches in the action
                    # block scope -- saw disk_c : err
                    # in the dashboard because $Matches[1] was \ and
                    # $_dl came back empty.  Parse the letter from $_
                    # directly via Substring instead.
                    $_dl = $_.Substring(5,1).ToUpper()
                    $_v  = try { Get-Volume -DriveLetter $_dl -ErrorAction Stop } catch { $null }
                    if (-not $_v) { return "${_dl}: --" }
                    $_tot = [math]::Round($_v.Size / 1GB, 1)
                    $_use = [math]::Round(($_v.Size - $_v.SizeRemaining) / 1GB, 1)
                    $_pct = if ($_v.Size -gt 0) { [math]::Round(((($_v.Size - $_v.SizeRemaining) / $_v.Size) * 100), 0) } else { 0 }
                    return "${_dl}: ${_use} / ${_tot}GiB (${_pct}%)"
                }
                'kernel' {
                    return 'Kernel ' + [System.Environment]::OSVersion.Version.ToString()
                }
                'shell' {
                    return 'Shell pwsh ' + $PSVersionTable.PSVersion.ToString()
                }
                'font' {
                    return "Font $_fontFam ${_fontSz}pt"
                }
                'uptime' {
                    if (-not $_dashCache.ContainsKey('_os')) {
                        $_dashCache['_os'] = try { Get-CimInstance Win32_OperatingSystem -ErrorAction Stop } catch { $null }
                    }
                    $_o = $_dashCache['_os']
                    if (-not $_o -or -not $_o.LastBootUpTime) { return 'Up --' }
                    $_up = (Get-Date) - $_o.LastBootUpTime
                    $_upd = [math]::Floor($_up.TotalDays)
                    return "Up ${_upd}d $($_up.Hours)h $($_up.Minutes)m"
                }
                default { return '' }
            }
        }

        # Parse [dashboard].rows + [theme.font] from the mios.toml text
        # we already loaded above for [dashboard].title.  Vendor defaults
        # baked in below if parsing fails (cold first-run before M:\
        # overlay is staged).
        $_dashRows  = $null
        $_dashFontF = 'GeistMono Nerd Font Mono'
        $_dashFontS = 12
        if ($_dashTomlText) {
            $_dashSec = [regex]::Match($_dashTomlText, '(?ms)^\[dashboard\]\s*\r?\n(?<body>.*?)(?=^\[[^\]]+\]|\z)')
            if ($_dashSec.Success) {
                $_rowsM = [regex]::Match($_dashSec.Groups['body'].Value, '(?ms)^\s*rows\s*=\s*\[(?<arr>.*?)^\]')
                if ($_rowsM.Success) {
                    $_rowsBody = $_rowsM.Groups['arr'].Value
                    $_rowMatches = [regex]::Matches($_rowsBody, '\[(?<r>[^\]]*)\]')
                    $_dashRows = @()
                    foreach ($_rm in $_rowMatches) {
                        $_fields = @($_rm.Groups['r'].Value -split ',' | ForEach-Object { $_.Trim().Trim('"',"'",' ',"`t","`r","`n") } | Where-Object { $_ })
                        if ($_fields.Count -gt 0) { $_dashRows += ,$_fields }
                    }
                    if ($_dashRows.Count -eq 0) { $_dashRows = $null }
                }
            }
            # [theme.font] -- pick up runtime font overrides for the font field.
            $_fontSec = [regex]::Match($_dashTomlText, '(?ms)^\[theme\.font\]\s*\r?\n(?<body>.*?)(?=^\[[^\]]+\]|\z)')
            if ($_fontSec.Success) {
                $_fb = $_fontSec.Groups['body'].Value
                $_fm = [regex]::Match($_fb, '(?m)^\s*family\s*=\s*"([^"]+)"')
                if ($_fm.Success) { $_dashFontF = $_fm.Groups[1].Value }
                $_sm = [regex]::Match($_fb, '(?m)^\s*size\s*=\s*(\d+)')
                if ($_sm.Success) { $_dashFontS = [int]$_sm.Groups[1].Value }
            }
        }
        if (-not $_dashRows) {
            $_dashRows = @(@('host_os'),@('cpu','gpu_discrete'),@('ram','swap'),@('disk_c','disk_m'),@('kernel','shell','font'))
        }

        foreach ($_row in $_dashRows) {
            $_n = @($_row).Count
            if ($_n -le 0) { continue }
            # Equal-width columns within the framed inner area.
            $_colW = [math]::Floor(($INNER - ($_n - 1) * 2) / $_n)
            if ($_colW -lt 8) { $_colW = 8 }
            $_cells = @()
            foreach ($_fk in $_row) {
                # Try/catch per-field so a single broken renderer
                # (e.g. Get-Volume not available, lspci missing) doesn't
                # kill the whole loop -- saw the
                # dashboard render only the first 3 rows and bail because
                # the disk_c renderer's Get-Volume call raised in a
                # context where the Storage module wasn't loaded.
                $_val = ''
                try {
                    $_val = & $_DashGetField $_fk $_dashFontF $_dashFontS
                } catch {
                    $_val = "$_fk : err"
                }
                if (-not $_val) { $_val = '' }
                if ($_val.Length -gt $_colW) {
                    $_val = $_val.Substring(0, [math]::Max(1, $_colW - 1)) + '…'
                }
                $_cells += $_val.PadRight($_colW)
            }
            try {
                Write-Host (_Frame (($_cells -join '  ').TrimEnd()))
            } catch {
                # Frame helper failed (rare -- ANSI strip or PadRight
                # overflow); print a placeholder so the render flow
                # continues and the divider/hints/bottom frame land.
                Write-Host (_Frame "  [dashboard row render failed]")
            }
        }
        # -- MiOS services block ----------------------------------
        # Resolve the dev distro ONCE, and only if it is ALREADY RUNNING, via a
        # fast `wsl --list --running` check (WSL_UTF8 so the names aren't UTF-16
        # with embedded NULs). This never cold-boots a stopped distro -- the
        # service + dev-shell bridges below reuse $_devDistro, so on every
        # terminal spawn a stopped/absent MiOS-DEV degrades open INSTANTLY
        # instead of blocking the prompt on a login-shell that triggers a boot.
        $_devDistro = $null
        if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
            try {
                $env:WSL_UTF8 = '1'
                $_running = @(& wsl.exe --list --running --quiet 2>$null) |
                            ForEach-Object { ($_ -replace "`0", '').Trim() } |
                            Where-Object { $_ }
                foreach ($_c in @('podman-MiOS-DEV','MiOS-DEV')) {
                    if ($_running -contains $_c) { $_devDistro = $_c; break }
                }
            } catch {}
        }

        # Live UNIFIED service table -- bridged from the ONE Linux renderer
        # (mios-dashboard.sh --table-only/--endpoints-only) via wsl, so BOTH
        # dashboards show the SAME live services (pods/containers/host units +
        # SSOT ports) from a single source: no hardcoded service/port list, no
        # drift. Full `mios dash` -> fuller UNIFIED table; compact `mios mini`
        # (80x20) -> compact endpoint table, exactly as the Linux dash vs mini.
        Write-Host ($LT + ($H * ($WIDTH - 2)) + $RT) -ForegroundColor Blue
        $_svcMode = if ($Full) { '--table-only' } else { '--endpoints-only' }
        $_svcLines = $null
        if ($_devDistro) {
            try {
                $_o = & wsl.exe -d $_devDistro --user mios -- bash -lc "COLUMNS=$WIDTH INNER=$INNER bash /usr/libexec/mios/mios-dashboard.sh $_svcMode --no-color" 2>$null
                if ($LASTEXITCODE -eq 0 -and $_o) { $_svcLines = @($_o) }
            } catch {}
        }
        if ($_svcLines) {
            foreach ($_sl in $_svcLines) { Write-Host (_Frame $_sl) -ForegroundColor Blue }
        } else {
            Write-Host (_Frame "  $_esc[90m[services: MiOS-DEV distro not running -- start with: mios dev]$_esc[0m") -ForegroundColor Blue
        }

        # -- Command hints rows -----------------------------------
        # Verb list resolves through mios.toml [verbs] at RUNTIME (SSOT).
        # The dashboard re-reads on every render so an operator edit via
        # mios.html flows mios.toml -> dashboard immediately. No hard-
        # coding here. Vendor fallback only if every TOML candidate is
        # missing (cold first-run before M:\ overlay is staged).
        $_verbDefs = @(
            @{ name='build';  desc='open mios.html, save, then build the OCI image' },
            @{ name='config'; desc='edit mios.toml in the HTML configurator (no build)' },
            @{ name='dash';   desc='show this dashboard (framed banner + fastfetch info)' },
            @{ name='dev';    desc='enter the MiOS-DEV podman machine' },
            @{ name='pull';   desc='sync M:\ overlay to origin/main' },
            @{ name='update'; desc='re-run the bootstrap (cache-busted)' },
            @{ name='help';   desc='list every verb' }
        )
        try {
            $_tomlCands = @(
                (Join-Path $env:USERPROFILE '.config\mios\mios.toml'),
                'M:\etc\mios\mios.toml',
                'M:\usr\share\mios\mios.toml'
            )
            foreach ($_tc in $_tomlCands) {
                if ($_tc -and (Test-Path -LiteralPath $_tc)) {
                    $_tt = Get-Content -LiteralPath $_tc -Raw -ErrorAction SilentlyContinue
                    if (-not $_tt) { continue }
                    $_vb = [regex]::Match($_tt, '(?ms)^\[verbs\]\s*\r?\n(.*?)(?=^\[|\z)')
                    if ($_vb.Success) {
                        $_parsed = @()
                        foreach ($_ln in ($_vb.Groups[1].Value -split "`n")) {
                            $_pm = [regex]::Match($_ln, '^\s*([a-z][a-z0-9_-]*)\s*=\s*\{[^}]*description\s*=\s*"([^"]+)"')
                            if ($_pm.Success) { $_parsed += @{ name=$_pm.Groups[1].Value; desc=$_pm.Groups[2].Value } }
                        }
                        if ($_parsed.Count -gt 0) { $_verbDefs = $_parsed; break }
                    }
                }
            }
        } catch {}
        Write-Host ($LT + ($H * ($WIDTH - 2)) + $RT) -ForegroundColor Blue
        if ($_compact) {
            $_hint1 = (($_verbDefs | ForEach-Object { $_.name }) -join '  ')
            Write-Host (_Center $_hint1) -ForegroundColor DarkCyan
        } else {
            $_maxName = (($_verbDefs | ForEach-Object { $_.name.Length }) | Measure-Object -Maximum).Maximum
            foreach ($_v in $_verbDefs) {
                $_pad = ' ' * ($_maxName - $_v.name.Length + 2)
                Write-Host (_Frame ('  mios ' + $_v.name + $_pad + '-- ' + $_v.desc)) -ForegroundColor DarkCyan
            }
        }

        # Bottom frame.
        Write-Host ($BL + ($H * ($WIDTH - 2)) + $BR) -ForegroundColor Blue

        # LIVE, copy-pasteable "SSH from this Windows host into the code-server
        # dev container at the MiOS root tree". Sourced from the SAME SSOT
        # helper the Linux dashboard uses (mios-ssh-dev-cmd), run inside the dev
        # distro via a LOGIN shell so it sees the rootful podman -- so the two
        # dashboards never drift. Printed UNFRAMED below the box so the long
        # command is never truncated and stays copyable in full. The distro is
        # probed from the same candidate list the rest of this profile uses.
        try {
            $_devCmd = $null
            if ($_devDistro) {
                $_out = & wsl.exe -d $_devDistro --user mios -- bash -lc 'bash /usr/libexec/mios/mios-ssh-dev-cmd' 2>$null
                if ($LASTEXITCODE -eq 0 -and $_out) { $_devCmd = ("$($_out | Select-Object -First 1)").Trim() }
            }
            if ($_devCmd) {
                Write-Host ("$_esc[1m$_esc[36mdev shell:$_esc[0m $_devCmd")
            }
        } catch {}
    }

    # NO inline-render here. The profile body is a thin function-
    # definition layer; the "what shows up on terminal spawn" is
    # whatever verb mios.toml [terminal.startup].windows points at.
    # The dispatch fires AT THE END of this profile (after the mios
    # verb function is defined). See the [terminal.startup] block
    # below the function definitions.
    # "have the bash and pwsh/WT environment/
    # dotfile(s) automatically run mios dash on open/launch--NOT
    # PRINT ON LAUNCH!!! THE ACTUAL ENV/DOTFILE(S) SHOULD DICTATE THE
    # COMMANDS/VERBS AND WHATS RUN ON CONSOLE SPAWN(ALL PLATFORMS
    # GLOBALLY)--ALL SOURCED FROM THE MIOS.TOML"

    # -- oh-my-posh init -------------------------------------------
    # Capture the init script output, then regex-patch the broken
    # positional Get-PSReadLineKeyHandler calls. Older oh-my-posh
    # versions emit Get-PSReadLineKeyHandler Spacebar etc. -- which
    # NO PSReadLine version accepts (the cmdlet's parameter binder
    # has no positional [string]). Latest oh-my-posh emits -Chord
    # <key>. We inject -Chord even when running latest, since it's
    # idempotent (latest already has it). This makes oh-my-posh's
    # PSReadLine integration work regardless of installed version.
    if (Get-Command oh-my-posh -ErrorAction SilentlyContinue) {
        # Shell-aware: oh-my-posh init pwsh emits PS 7+ syntax that
        # FAILS silently in Windows PowerShell 5.1, leaving the
        # operator's pre-existing broken init showing "CONFIG NOT
        # FOUND". Detect PS edition and use the matching arg
        # (powershell for 5.1 / Desktop, pwsh for 7+ / Core).
        $_ompShell = if ($PSVersionTable.PSEdition -eq 'Desktop') { 'powershell' } else { 'pwsh' }
        $ompInit = if ($miosOmp -and (Test-Path -LiteralPath $miosOmp)) {
            (oh-my-posh init $_ompShell --config $miosOmp) -join "`n"
        } else {
            (oh-my-posh init $_ompShell) -join "`n"
        }
        if ($ompInit) {
            $ompInit = [regex]::Replace($ompInit, 'Get-PSReadLineKeyHandler\s+(?!-)([A-Za-z][\w+]*)', 'Get-PSReadLineKeyHandler -Chord ''$1''')
            try { Invoke-Expression $ompInit } catch {}
        }
    }
}

# -- MiOS commands ---------------------------------------------------
# Defined in EVERY pwsh session (not gated on WT_SESSION) so the
# operator can run mios-build / mios-update / mios-help from any shell.
# Each command fetches its target script fresh from
# raw.githubusercontent.com so the operator doesn't have to manually
# pull the mios-bootstrap repo. Cache-busting via ?cb=<unix-time>
# defeats Fastly's 5-minute max-age.

$Script:MiosBootstrapRaw = 'https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main'

function mios-build {
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments)]$Args)
    # New flow (per operator: "mios build should queue the build, launch
    # the html file in the local windows browser window, fetch the newly
    # minted html/toml files to the overlay >> start the build with new
    # key steps implemented"):
    #
    #   1. Open mios-config.html in the default Windows browser so the
    #      operator can edit theming / functionality / package lists.
    #   2. Wait for the operator to save + close the configurator (or
    #      hit Enter to skip the edit pass).
    #   3. mios-pull to sync M:\ overlay to origin/main + apply user edits.
    #   4. Run build-mios.ps1 -BuildOnly so it skips the bootstrap phase
    #      and goes straight into the OCI build inside MiOS-DEV.
    #
    # Bypass the configurator pass with: mios build -SkipConfig
    # Bypass the pull pass        with: mios build -SkipPull
    $skipConfig = $Args -contains '-SkipConfig'
    $skipPull   = $Args -contains '-SkipPull'
    $forwardArgs = @($Args | Where-Object { $_ -notin @('-SkipConfig','-SkipPull') })

    # -- Step 1 + 2: configurator pass ------------------------------
    if (-not $skipConfig) {
        $cfgHtml = $null
        foreach ($c in @(
            'M:\usr\share\mios\configurator\mios.html',
            'M:\MiOS\usr\share\mios\configurator\mios.html'
        )) { if (Test-Path -LiteralPath $c) { $cfgHtml = $c; break } }
        if ($cfgHtml) {
            # Capture mtime BEFORE opening so we can tell if the operator
            # actually saved a new copy (the browser saves to Downloads
            # because file:// URLs can't write back to source). Used by
            # the promote step below.
            $cfgMtimeBefore = (Get-Item -LiteralPath $cfgHtml).LastWriteTimeUtc
            Write-Host ''
            Write-Host '  [1/4] Opening MiOS configurator in your browser...' -ForegroundColor Cyan
            Write-Host ('         '+$cfgHtml) -ForegroundColor DarkGray
            Write-Host '         Edit values, click Save -> the browser writes mios.toml' -ForegroundColor DarkGray
            Write-Host '         to your Downloads folder (file:// URLs cannot write back).' -ForegroundColor DarkGray
            try { Start-Process $cfgHtml | Out-Null } catch {}
            Write-Host ''
            Write-Host '  Press Enter when you''ve saved the configurator (or to skip the edit pass)...' -ForegroundColor Yellow -NoNewline
            $null = Read-Host
        } else {
            Write-Host '  [!] Configurator HTML not found on M:\ -- skipping edit pass.' -ForegroundColor Yellow
            Write-Host '      Run mios pull first to seed the overlay.' -ForegroundColor DarkGray
        }

        # -- Step 2: promote downloaded mios.toml from Downloads ----
        # The browser saves to %USERPROFILE%\Downloads (file:// URLs
        # can't write back to source). Scan for any mios*.toml /
        # *mios*.html newer than the in-place overlay copies and
        # PROMOTE them to M:\etc\mios\ + M:\usr\share\mios\configurator\.
        # Also archive the imported source so we don't double-promote
        # on the next mios-build run.
        Write-Host ''
        Write-Host '  [2/4] Scanning Downloads for edited config files...' -ForegroundColor Cyan
        $dlDir = Join-Path $env:USERPROFILE 'Downloads'
        if (Test-Path -LiteralPath $dlDir) {
            $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
            # mios.toml -> M:\etc\mios\mios.toml (+ /usr/share copy for
            # the dev VM via /mnt/m/etc/mios)
            $tomlSrc = Get-ChildItem -LiteralPath $dlDir -Filter 'mios*.toml' -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
            if ($tomlSrc) {
                $tomlDst = 'M:\etc\mios\mios.toml'
                $tomlPar = Split-Path -Parent $tomlDst
                if (-not (Test-Path -LiteralPath $tomlPar)) {
                    New-Item -ItemType Directory -Path $tomlPar -Force | Out-Null
                }
                Copy-Item -LiteralPath $tomlSrc.FullName -Destination $tomlDst -Force
                Write-Host ('         [+] '+$tomlSrc.Name+' -> '+$tomlDst) -ForegroundColor Green
                # Also copy to M:\usr\share\mios so the layered overlay
                # picks it up even before mios-pull runs.
                $tomlDst2 = 'M:\usr\share\mios\mios.toml'
                if (Test-Path -LiteralPath (Split-Path -Parent $tomlDst2)) {
                    Copy-Item -LiteralPath $tomlSrc.FullName -Destination $tomlDst2 -Force
                    Write-Host ('         [+] '+$tomlSrc.Name+' -> '+$tomlDst2) -ForegroundColor Green
                }
                # Archive the source so a re-run of mios build doesn't
                # re-promote the same file. Keep it (don't delete) so
                # the operator can recover if something went wrong.
                $archive = Join-Path $dlDir ($tomlSrc.BaseName+'.imported-'+$stamp+'.toml')
                Move-Item -LiteralPath $tomlSrc.FullName -Destination $archive -Force
            } else {
                Write-Host '         [-] no mios*.toml in Downloads -- using existing overlay' -ForegroundColor DarkGray
            }
            # Also pick up an edited HTML configurator (rare; the
            # configurator emits TOML by default but operators may save
            # a hand-edited HTML).
            $htmlSrc = Get-ChildItem -LiteralPath $dlDir -Filter '*mios*.html' -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -notmatch '\.imported-' } |
                Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
            if ($htmlSrc) {
                $htmlDst = 'M:\usr\share\mios\configurator\mios.html'
                $htmlPar = Split-Path -Parent $htmlDst
                if (-not (Test-Path -LiteralPath $htmlPar)) {
                    New-Item -ItemType Directory -Path $htmlPar -Force | Out-Null
                }
                Copy-Item -LiteralPath $htmlSrc.FullName -Destination $htmlDst -Force
                Write-Host ('         [+] '+$htmlSrc.Name+' -> '+$htmlDst) -ForegroundColor Green
                $archive = Join-Path $dlDir ($htmlSrc.BaseName+'.imported-'+$stamp+'.html')
                Move-Item -LiteralPath $htmlSrc.FullName -Destination $archive -Force
            }
        } else {
            Write-Host '         [-] '$dlDir' does not exist -- skipping promote' -ForegroundColor DarkGray
        }
    }

    # -- Step 3: sync overlay so the build sees the latest mios.toml -
    # Note: this runs AFTER the Downloads-promote step so mios-pull
    # sees the just-promoted files in M:\etc\mios. mios-pull's git
    # reset --hard would otherwise blow away the operator's changes
    # if they lived in the tracked tree.
    if (-not $skipPull) {
        Write-Host ''
        Write-Host '  [3/4] Syncing M:\ overlay (mios.git + mios-bootstrap)...' -ForegroundColor Cyan
        try { mios-pull } catch { Write-Host "  [!] mios-pull failed: $($_.Exception.Message)" -ForegroundColor Yellow }
    }

    # -- Step 4: ignite the build -----------------------------------
    Write-Host ''
    Write-Host '  [4/4] Running build pipeline (build-mios.ps1)...' -ForegroundColor Cyan
    $env:MIOS_DASHBOARD_MODE = 'log'
    $cb = [int][double]::Parse((Get-Date -UFormat %s))
    $src = Invoke-RestMethod -Uri "$Script:MiosBootstrapRaw/build-mios.ps1?cb=$cb" -Headers @{ 'Cache-Control' = 'no-cache' }
    & ([scriptblock]::Create($src)) @forwardArgs
}

function mios-update {
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments)]$Args)
    $cb = [int][double]::Parse((Get-Date -UFormat %s))
    $src = Invoke-RestMethod -Uri "$Script:MiosBootstrapRaw/Get-MiOS.ps1?cb=$cb" -Headers @{ 'Cache-Control' = 'no-cache' }
    & ([scriptblock]::Create($src)) @Args
}

function mios-pull {
    if (-not (Test-Path 'M:\.git')) {
        Write-Host '  [!] M:\ is not a git working tree -- run mios-build first.' -ForegroundColor Yellow
        return
    }
    Push-Location 'M:\'
    try {
        git fetch --depth=1 origin main
        if ($LASTEXITCODE -eq 0) {
            git reset --hard FETCH_HEAD
            Write-Host '  [+] M:\ overlay synced to origin/main.' -ForegroundColor Green
        } else {
            Write-Host '  [!] git fetch failed -- check network.' -ForegroundColor Yellow
        }
    } finally { Pop-Location }
}

function mios-config {
    $cfg = if (Test-Path 'M:\usr\share\mios\configurator\mios.html') { 'M:\usr\share\mios\configurator\mios.html' }
           else { $null }
    if ($cfg) {
        Start-Process $cfg
        Write-Host "  [+] Opened $cfg" -ForegroundColor DarkGray
    } else {
        Write-Host '  [!] configurator not found -- run mios-build to deploy it.' -ForegroundColor Yellow
    }
}

function mios-dev {
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments)]$Args)
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        Write-Host '  [!] wsl.exe not on PATH -- WSL2 may not be installed.' -ForegroundColor Yellow
        return
    }
    # Probe for the actual on-disk WSL distro name. With the default
    # rename-skipped behavior (MIOS_RENAME_DISTRO unset), the distro is
    # 'podman-MiOS-DEV' (preserved from podman machine init so Podman
    # Desktop can see it). With opt-in rename, it's 'MiOS-DEV'. Either
    # works -- we resolve at call time so the helper survives both modes.
    $_devDistro = $null
    try {
        $_wsl = (& wsl.exe -l -q 2>$null) -split "?
" |
            ForEach-Object { ($_ -replace [char]0,'').Trim() } |
            Where-Object { $_ }
        foreach ($_cand in @('podman-MiOS-DEV','MiOS-DEV','podman-MiOS-BUILDER','MiOS-BUILDER')) {
            if ($_wsl -contains $_cand) { $_devDistro = $_cand; break }
        }
    } catch {}
    if (-not $_devDistro) {
        Write-Host '  [!] No MiOS-DEV / podman-MiOS-DEV WSL distro registered. Run irm|iex one-liner to provision.' -ForegroundColor Yellow
        return
    }
    & wsl.exe -d $_devDistro --cd / --user mios @Args
}

function mios-mini {
    # MINI dashboard -- the compact 80x20 framed banner + fastfetch
    # info. This is what fires on every shell spawn (vendor default
    # of [terminal.startup].verb). "have launch
    # be the mini-dashboard ... NOT PRINT ON LAUNCH" -- the dotfile
    # dispatches THIS verb so the render comes from a verb command,
    # not inline-print in the profile body.
    if (Get-Command Show-MiosDashboard -ErrorAction SilentlyContinue) {
        $cfg  = if (Test-Path 'M:\MiOS\fastfetch\config.jsonc') { 'M:\MiOS\fastfetch\config.jsonc' } else { '' }
        $logo = if (Test-Path 'M:\MiOS\fastfetch\mios.txt')      { 'M:\MiOS\fastfetch\mios.txt' }      else { '' }
        Show-MiosDashboard -ConfigPath $cfg -LogoPath $logo
    } else {
        Write-Host '  [!] mios mini: Show-MiosDashboard not loaded.' -ForegroundColor Yellow
    }
}

function mios-dash {
    # FULL MiOS dashboard = the SAME framed renderer as `mios mini`, but with
    # the ASCII banner (`-Full`), so the Windows `mios dash` matches the Linux
    # `mios dash` exactly: one design, Windows host values + the live MiOS
    # service table + the dev-shell command. (Previously this was a separate
    # fastfetch/podman-machine view that looked nothing like the Linux
    # dashboard -- the operator's "doesn't match at all".)
    if (Get-Command Show-MiosDashboard -ErrorAction SilentlyContinue) {
        $cfg  = if (Test-Path 'M:\MiOS\fastfetch\config.jsonc') { 'M:\MiOS\fastfetch\config.jsonc' } else { '' }
        $logo = if (Test-Path 'M:\MiOS\fastfetch\mios.txt') { 'M:\MiOS\fastfetch\mios.txt' }
                elseif (Test-Path 'M:\usr\share\mios\branding\mios.txt') { 'M:\usr\share\mios\branding\mios.txt' }
                else { '' }
        Show-MiosDashboard -ConfigPath $cfg -LogoPath $logo -Full
    } else {
        Write-Host '  [!] mios dash: Show-MiosDashboard not loaded.' -ForegroundColor Yellow
    }
}

function mios-help {
    Write-Host ''
    Write-Host '  MiOS commands' -ForegroundColor Cyan
    Write-Host '  -------------' -ForegroundColor DarkCyan
    Write-Host '  mios <verb>   unified dispatcher (tab-complete supported)' -ForegroundColor White
    Write-Host '                  or use mios-<verb> directly:' -ForegroundColor DarkGray
    Write-Host '  mios build    run the full MiOS OS bootstrap (WSL2 + podman + dev VM)' -ForegroundColor White
    Write-Host '  mios update   re-run Get-MiOS.ps1 (refresh terminal install)' -ForegroundColor White
    Write-Host '  mios pull     git fetch + hard reset M:\ to origin/main' -ForegroundColor White
    Write-Host '  mios config   open the HTML configurator (mios.toml editor)' -ForegroundColor White
    Write-Host '  mios ai       open Open WebUI (rich LLM interface) in your browser' -ForegroundColor White
    Write-Host '  mios dev      wsl into the MiOS-DEV distro (root /, user mios)' -ForegroundColor White
    Write-Host '  mios dash     FULL dashboard: ASCII banner + services + extended sys specs' -ForegroundColor White
    Write-Host '  mios xbox     Xbox VM Secure Boot / XML repair' -ForegroundColor White
    Write-Host '  mios virt     apply optimized VM config + CPU pinning' -ForegroundColor White
    Write-Host '  mios vfio     configure GPU/USB passthrough (Isolation)' -ForegroundColor White
    Write-Host '  mios help     this list' -ForegroundColor White
    Write-Host ''
}

# Unified mios <verb> dispatcher. Operator types mios build or
# mios b<TAB> (PSReadLine + the ArgumentCompleter below complete to
# mios build). Falls through to mios-<verb> so the same wrappers
# back both call shapes.
# Known verbs dispatch to mios-<verb>.ps1 wrappers in $Global:MiosBin.
# Anything that isn't a known verb is routed to Hermes-Agent at
# MIOS_AI_ENDPOINT as a chat completion, so mios how do I bootc switch
# works from any PowerShell terminal without a separate sk verb.
$Script:MiosKnownVerbs = @('build','update','pull','config','ai','dev','dash','mini','help','code','xbox','virt','vfio','tune','summary','profile','assess','iommu','theme','user')

function mios {
    [CmdletBinding()]
    param(
        [Parameter(Position=0)]
        [string]$Verb,
        [Parameter(ValueFromRemainingArguments)]
        $Args
    )
    if (-not $Verb) { $Verb = 'help' }
    if ($Script:MiosKnownVerbs -contains $Verb.ToLowerInvariant()) {
        $cmd = "mios-$($Verb.ToLowerInvariant())"
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            & $cmd @Args
        } else {
            Write-Host "  [!] mios: verb '$Verb' wrapper not found. Try: mios help" -ForegroundColor Yellow
        }
        return
    }
    # Free-form query -> Hermes-Agent /v1/chat/completions.
    $_query = (@($Verb) + @($Args)) -join ' '
    # $Global:MiosBin may be unset (this profile is dot-sourced standalone from
    # the $PROFILE redirector). Guard it -- Join-Path throws on a null Path,
    # which would surface a raw binder error instead of the friendly hint below.
    if (-not $Global:MiosBin) {
        Write-Host "  [!] mios-ask.ps1 not staged. Try: mios help" -ForegroundColor Yellow
        return
    }
    $_ask = Join-Path $Global:MiosBin 'mios-ask.ps1'
    if (Test-Path -LiteralPath $_ask) {
        & $_ask $_query
    } else {
        Write-Host "  [!] mios-ask.ps1 not staged. Try: mios help" -ForegroundColor Yellow
    }
}

Register-ArgumentCompleter -CommandName mios -ParameterName Verb -ScriptBlock {
    param($cmdName, $paramName, $wordToComplete, $cmdAst, $fakeBoundParam)
    $Script:MiosKnownVerbs |
        Where-Object { $_ -like "$wordToComplete*" } |
        ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
}

# -- Interactive-shell startup verb (SSOT: mios.toml [terminal.startup]) --
# The profile body above is JUST function definitions. What runs on
# terminal spawn is the verb declared in mios.toml -- read fresh
# every shell launch so HTML configurator edits flow through with
# zero re-bake. Vendor default is "dash" but the operator can flip
# to any other verb (or "" for a silent shell).
#
# Per-platform key precedence: [terminal.startup].windows wins over
# [terminal.startup].verb (the cross-platform default). The Linux
# bash side reads the same TOML keys (.linux > .verb).
#
# Guards:
#   - $env:MIOS_SKIP_MOTD = "1"      -> no startup verb fires.
#   - non-interactive host           -> no fire (background scripts,
#                                       VS Code's PowerShell extension
#                                       integrated terminal, etc.).
#   - $Global:MiosStartupVerbFired   -> idempotent across re-sources
#                                       (mios.ps1 dot-sources this
#                                       profile to load functions, we
#                                       don't want a recursive verb
#                                       call inside an already-running
#                                       verb).
function _MiosResolveStartupVerb {
    $_cands = @(
        (Join-Path $env:USERPROFILE '.config\mios\mios.toml'),
        'M:\etc\mios\mios.toml',
        'M:\usr\share\mios\mios.toml'
    )
    foreach ($_c in $_cands) {
        if (-not (Test-Path -LiteralPath $_c)) { continue }
        try {
            $_t = [IO.File]::ReadAllText($_c, (New-Object System.Text.UTF8Encoding($false)))
        } catch { continue }
        $_sec = [regex]::Match($_t, '(?ms)^\[terminal\.startup\]\s*\r?\n(?<body>.*?)(?=^\[[^\]]+\]|\z)')
        if (-not $_sec.Success) { continue }
        $_body = $_sec.Groups['body'].Value
        # Per-platform key wins over cross-platform 'verb' key.
        $_keys = @('windows','verb')
        foreach ($_k in $_keys) {
            $_m = [regex]::Match($_body, ('(?m)^\s*' + [regex]::Escape($_k) + '\s*=\s*"([^"]*)"'))
            if ($_m.Success) { return $_m.Groups[1].Value.Trim() }
        }
    }
    # Vendor fallback: mini (the compact 80x20 framed banner).
    # dash is the FULL render -- ASCII banner + service status +
    # extended sys specs -- explicitly invoked by the operator,
    # not auto-fired on every shell spawn.
    return 'mini'
}

if (-not $Global:MiosStartupVerbFired -and $Host.UI.RawUI -and (-not $env:MIOS_SKIP_MOTD)) {
    $Global:MiosStartupVerbFired = $true
    $_startupVerb = _MiosResolveStartupVerb
    if ($_startupVerb) {
        try { mios $_startupVerb } catch {}
    }
}
# -- MiOS WindowWidth diagnostic (auto-appended by Install-MiOSPowerShellProfile) --
# Every MiOS pwsh launch appends one line to M:\MiOS\diagnostics\window-width.txt
# capturing [Console]::WindowWidth + BufferWidth + WT_SESSION + timestamp.
# This is the SOURCE OF TRUTH for the actual visible cell count on the
# operator's hardware -- if WindowWidth != mios.toml [terminal].cols, the
# delta is the WT chrome budget that right_margin must absorb.
try {
    $_diagDir = 'M:\MiOS\diagnostics'
    if (-not (Test-Path -LiteralPath $_diagDir)) { New-Item -ItemType Directory -Path $_diagDir -Force | Out-Null }
    $_diagFile = Join-Path $_diagDir 'window-width.txt'
    $_ww = try { [Console]::WindowWidth } catch { '?' }
    $_bw = try { $Host.UI.RawUI.BufferSize.Width } catch { '?' }
    $_wh = try { [Console]::WindowHeight } catch { '?' }
    $_wt = if ($env:WT_SESSION) { 'WT' } else { 'conhost-or-other' }
    $_ts = (Get-Date).ToString('s')
    Add-Content -LiteralPath $_diagFile -Value ("{0} WindowWidth={1} BufferWidth={2} WindowHeight={3} host={4} pwsh={5}" -f $_ts, $_ww, $_bw, $_wh, $_wt, $PSVersionTable.PSVersion)
} catch {}
# -- end MiOS WindowWidth diagnostic --
