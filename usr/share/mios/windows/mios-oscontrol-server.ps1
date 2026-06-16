# AI-hint: Windows-specific HTTP listener for the MiOS OS-control system that executes Win32 commands, manages window states (move/resize/focus), and provides window/screen metadata for remote agent interaction.
# AI-related: mios-oscontrol-server, mios-daemon-agent, mios-igpu-server, mios-autocenter, mios-pc-control, mios-launch
# AI-functions: Info, Ok, Warn, Get-VisibleWindows, Test-WindowPresent, Resolve-TargetWindows, Invoke-WindowOp, Invoke-MouseMove, Invoke-Click, Invoke-DoubleClick, Invoke-TypeText, Invoke-Key
<#
  mios-oscontrol-server.ps1  --  MiOS OS-control executor (Windows node)

  WHY THIS EXISTS  (operator 2026-05-25, 4B)
  ------------------------------------------
  4A made the always-on mios-daemon-agent FIRE + VERIFY launches on the dev
  VM's desktop (through the launcher broker, which inherits the VM-host's WSLg
  display env). 4B extends OS-control TO A SEPARATE PHYSICAL NODE -- e.g. the
  iGPU host -- so an agent can launch + confirm an app on THAT machine's own
  desktop, reached over Tailscale.

  This is a tiny self-contained HTTP executor: a System.Net.HttpListener that
  accepts launch + verify requests and runs them with native Win32 on THIS
  node's interactive desktop. It is the OS-control sibling of
  mios-igpu-server.ps1 (which serves inference): same install/firewall
  machinery, different payload.

  The MiOS VM reaches it via [os_control.nodes.<name>].endpoint in mios.toml
  (put the real tailnet endpoint in your /etc/mios overlay, NOT the public repo).

  ROUTES
  ------
    GET  /health                 -> {ok, host, ts}
    POST /launch  {app:"<name>"}  -> resolve + Start-Process on this desktop,
                                     poll for the window, then
                                     {app, fired, launched, verdict, host, node}
    GET  /verify?app=<name>       -> window-presence check on this node ->
                                     {app, launched, verdict, host}
    GET  /windows                 -> {ok, count, windows:[{hwnd,title,pid,proc,
                                     x,y,w,h}], host} -- the grounding SNAPSHOT
                                     the agent records BEFORE+AFTER open/close to
                                     diff exactly what changed (operator 2026-05-26).
    POST /window/close  {title|hwnd}            -> graceful WM_CLOSE (NOT a kill)
    POST /window/focus  {title|hwnd}            -> raise + foreground
    POST /window/move   {title|hwnd, x, y}      -> reposition
    POST /window/resize {title|hwnd, width, height}
    POST /window/center {title|hwnd}            -> center on primary work area
    POST /window/state  {title|hwnd, state:minimize|maximize|restore}
                                  -> each returns {ok, op, count, matched:[...]}
    GET  /screen-layout           -> {ok, count, screens:[{device,primary,bounds,work}]}
    GET  /screenshot              -> {ok, format:png, width, height, image_b64}
    POST /input/mouse-move   {x, y}
    POST /input/click        {x, y, button:left|right|middle}
    POST /input/double-click {x, y}
    POST /input/type         {text}
    POST /input/key          {name}            -> Enter|Tab|Esc|F5|<char>...
    POST /input/key-combo    {combo:"Ctrl+C"}
                                  -- input/capture run on WinSta0\Default (the
                                  real desktop), unlike blind WSL-interop.

  It NEVER fabricates launched=true: launched reflects an actual top-level
  window match (title or owning-process name). Window ops report the ACTUAL
  matched windows; an empty match returns ok=false (no fabricated success).

  USAGE
  -----
    pwsh -File mios-oscontrol-server.ps1                 # run in foreground
    pwsh -File mios-oscontrol-server.ps1 -Install        # logon scheduled task (hidden, elevated)
    pwsh -File mios-oscontrol-server.ps1 -Uninstall      # remove the task
    pwsh -File mios-oscontrol-server.ps1 -Port 11437

  5.1-compatible (the scheduled task runs Windows PowerShell 5.1 for a stable
  interpreter path -- the MSIX pwsh alias is unresolvable by Task Scheduler;
  see mios-igpu-server.ps1 -Install for that lesson). No ternary / ?? / -Parallel.
#>
[CmdletBinding()]
param(
    [int]    $Port    = 11437,
    [double] $VerifySettleSeconds   = 1.5,
    [int]    $VerifyAttempts        = 6,
    [double] $VerifyIntervalSeconds = 2.5,
    [switch] $Install,
    [switch] $Uninstall
)

$ErrorActionPreference = 'Stop'
$taskName = 'MiOS-OSControl-Server'
$fwName   = "MiOS - oscontrol ($Port/tcp)"
# Firewall remote scope: tailnet peers (Tailscale CGNAT) PLUS the local WSL NAT
# subnet, so the in-WSL MiOS VM reaches this executor over its host gateway even
# when Tailscale is down (operator 2026-06-07). 172.16.0.0/12 covers every WSL
# Hyper-V-assigned 172.x gateway; both ranges are local-only (same machine).
$fwRemote = @('100.64.0.0/10', '172.16.0.0/12')
$logDir   = Join-Path $env:LOCALAPPDATA 'mios\oscontrol\logs'

function Info($m){ Write-Host "  [*] $m" -ForegroundColor Cyan }
function Ok($m)  { Write-Host "  [+] $m" -ForegroundColor Green }
function Warn($m){ Write-Host "  [!] $m" -ForegroundColor Yellow }

# ---- scheduled-task install / uninstall (mirrors mios-igpu-server.ps1) -------
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
            '-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath,'-Install','-Port',$Port)
        return
    }
    $argline = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" -Port $Port"
    # Resolve a CONCRETE interpreter path: NOT the bare 'pwsh.exe' MSIX alias
    # (Task Scheduler can't resolve it -> 0x80070002). Prefer a real pwsh under
    # Program Files, else Windows PowerShell 5.1 at its fixed System32 path
    # (this script is 5.1-compatible).
    $psExe = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
    if (-not $psExe -or $psExe -like '*\WindowsApps\*' -or -not (Test-Path $psExe)) {
        $psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    }
    $action  = New-ScheduledTaskAction  -Execute $psExe -Argument $argline
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $set     = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    # Interactive + Highest: the executor MUST run in the interactive desktop
    # session (to surface windows) AND elevated (so HttpListener can bind the
    # '+' prefix without a separate netsh urlacl reservation).
    $prin    = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $set -Principal $prin -Force | Out-Null
    Ok "registered logon scheduled task '$taskName' (port $Port)"
    # Tailnet-scoped firewall: only Tailscale peers (100.64.0.0/10) reach it.
    if (-not (Get-NetFirewallRule -DisplayName $fwName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $fwName -Direction Inbound -Action Allow -Protocol TCP `
            -LocalPort $Port -RemoteAddress $fwRemote -Profile Any -ErrorAction SilentlyContinue | Out-Null
        Ok "firewall: allow tailnet + local WSL -> :$Port"
    } else {
        # Reconcile an existing rule's scope so a widened $fwRemote (adding the
        # local WSL subnet) applies to installs created before this change --
        # create-if-missing alone left old rules tailnet-only (operator 2026-06-07).
        Set-NetFirewallRule -DisplayName $fwName -RemoteAddress $fwRemote -ErrorAction SilentlyContinue | Out-Null
        Ok "firewall: reconciled scope -> tailnet + local WSL on :$Port"
    }
    Info 'starting it now...'
    Start-ScheduledTask -TaskName $taskName
    return
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Foreground run also ensures the firewall rule exists + has the current scope.
if (-not (Get-NetFirewallRule -DisplayName $fwName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $fwName -Direction Inbound -Action Allow -Protocol TCP `
        -LocalPort $Port -RemoteAddress $fwRemote -Profile Any -ErrorAction SilentlyContinue | Out-Null
} else {
    # Reconcile existing rule scope (a widened $fwRemote applies to old installs).
    Set-NetFirewallRule -DisplayName $fwName -RemoteAddress $fwRemote -ErrorAction SilentlyContinue | Out-Null
}

# ---- Win32 surface for window enumeration ------------------------------------
$Win32Sig = @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class OSCW32 {
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int max);
    // InternalGetWindowText reads the title from the window's INTERNAL storage
    // WITHOUT sending WM_GETTEXT -- so enumeration never blocks on a hung /
    // non-responding window (operator 2026-05-29: /windows intermittently
    // wedged after launches -> GetWindowText was hanging on an unresponsive
    // app's message pump, freezing the whole listener + breaking autocenter +
    // launch-verify). Non-blocking; the robust enumeration primitive.
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int InternalGetWindowText(IntPtr h, StringBuilder s, int max);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int ht, bool repaint);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr wp, IntPtr lp);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr i);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    public const uint MOUSEEVENTF_LEFTDOWN  = 0x0002;
    public const uint MOUSEEVENTF_LEFTUP    = 0x0004;
    public const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
    public const uint MOUSEEVENTF_RIGHTUP   = 0x0010;
    public const uint MOUSEEVENTF_MIDDLEDOWN= 0x0020;
    public const uint MOUSEEVENTF_MIDDLEUP  = 0x0040;
}
"@
if (-not ([System.Management.Automation.PSTypeName]'OSCW32').Type) {
    Add-Type -TypeDefinition $Win32Sig -ErrorAction SilentlyContinue
}

# Enumerate visible top-level windows -> list of @{ title; pid; proc }.
#
# HANG-HARDENING (operator 2026-05-29: /windows timed out while / answered):
# the per-window `Get-Process -Id` call below was made INSIDE the EnumWindows
# callback, so a single hung/protected process (or a slow WMI-backed lookup)
# stalled the ENTIRE enumeration and the route never returned. Build a
# PID -> ProcessName snapshot ONCE up front (single Get-Process) and look up
# from the hashtable in the callback -- no blocking syscall per window, and
# far faster across a desktop full of windows.
function Get-VisibleWindows {
    $result = New-Object System.Collections.ArrayList
    # CACHE the PID->name snapshot with a short TTL (operator 2026-05-29: the
    # executor WEDGED under launch load). During a launch the agent verify-poll
    # + mios-autocenter hammer /windows ~30x in 30s; re-running the heavy +
    # occasionally-stalling Get-Process on EVERY request was the load-induced
    # hang. Rebuild only when the snapshot is stale (>2s); a burst reuses it, so
    # /windows stays cheap (just the non-blocking EnumWindows walk). script:
    # scope so the EnumWindows delegate callback always sees the map.
    $now = [DateTime]::UtcNow
    if ((-not $script:OSCProcMap) -or (-not $script:OSCProcMapTs) -or
        (($now - $script:OSCProcMapTs).TotalSeconds -gt 2)) {
        $m = @{}
        try {
            foreach ($p in (Get-Process -ErrorAction SilentlyContinue)) {
                if ($p -and -not $m.ContainsKey([int]$p.Id)) { $m[[int]$p.Id] = $p.ProcessName }
            }
        } catch {}
        $script:OSCProcMap = $m
        $script:OSCProcMapTs = $now
    }
    $cb = [OSCW32+EnumWindowsProc]{
        param($h, $l)
        if ([OSCW32]::IsWindowVisible($h)) {
            # InternalGetWindowText (non-blocking) -- NOT GetWindowTextLength +
            # GetWindowText, BOTH of which send synchronous messages that hang on
            # an unresponsive window + freeze the whole /windows enumeration.
            $sb = New-Object System.Text.StringBuilder 512
            if ([OSCW32]::InternalGetWindowText($h, $sb, $sb.Capacity) -gt 0) {
                $procId = 0
                [void][OSCW32]::GetWindowThreadProcessId($h, [ref]$procId)
                $pname = ''
                if ($script:OSCProcMap.ContainsKey([int]$procId)) { $pname = $script:OSCProcMap[[int]$procId] }
                $rect = New-Object OSCW32+RECT
                [void][OSCW32]::GetWindowRect($h, [ref]$rect)
                [void]$result.Add(@{ hwnd = $h.ToInt64(); title = $sb.ToString();
                                     pid = [int]$procId; proc = $pname;
                                     x = [int]$rect.Left; y = [int]$rect.Top;
                                     w = [int]($rect.Right - $rect.Left);
                                     h = [int]($rect.Bottom - $rect.Top) })
            }
        }
        return $true
    }
    [void][OSCW32]::EnumWindows($cb, [IntPtr]::Zero)
    return $result
}

# Does a visible top-level window match this app name (title OR process)?
function Test-WindowPresent($name) {
    $needle = ($name -replace '\.exe$','').Trim()
    if (-not $needle) { return @{ launched = $false; summary = 'empty-name' } }
    foreach ($w in Get-VisibleWindows) {
        if (($w.title -and $w.title -like "*$needle*") -or
            ($w.proc  -and $w.proc  -like "*$needle*")) {
            return @{ launched = $true; summary = 'presented';
                      title = $w.title; pid = $w.pid; proc = $w.proc }
        }
    }
    return @{ launched = $false; summary = 'no-window' }
}

# Resolve a target to the matching visible window(s): by hwnd when given,
# else case-insensitive title/proc substring. Returns the live window hashes.
function Resolve-TargetWindows($hwnd, $title) {
    $all = Get-VisibleWindows
    if ($hwnd) {
        $hv = [int64]$hwnd
        return @($all | Where-Object { $_.hwnd -eq $hv })
    }
    $needle = ("$title" -replace '\.exe$','').Trim()
    if (-not $needle) { return @() }
    return @($all | Where-Object {
        ($_.title -and $_.title -like "*$needle*") -or
        ($_.proc  -and $_.proc  -like "*$needle*") })
}

# Perform a window op on the matching window(s). op = close|focus|move|resize|
# state. close is a GRACEFUL WM_CLOSE (operator binding: never force-kill /
# Stop-Process a window). Returns {ok, op, count, matched:[...]}.
function Invoke-WindowOp($op, $hwnd, $title, $x, $y, $w, $h, $state) {
    $WM_CLOSE = 0x0010
    $targets = Resolve-TargetWindows $hwnd $title
    if (-not $targets -or $targets.Count -eq 0) {
        return @{ ok = $false; op = $op; count = 0; matched = @();
                  error = "no visible window matches" }
    }
    $done = New-Object System.Collections.ArrayList
    foreach ($wnd in $targets) {
        $p = [IntPtr]([int64]$wnd.hwnd)
        switch ($op) {
            'close'  { [void][OSCW32]::PostMessage($p, $WM_CLOSE, [IntPtr]::Zero, [IntPtr]::Zero) }
            'focus'  {
                # FORCEFUL foreground (operator 2026-05-26 "Xbox-mode focus didn't
                # work"): Windows blocks SetForegroundWindow from a background
                # process (only flashes the taskbar). Bypass the foreground lock:
                # tap Alt, AttachThreadInput to the current foreground window's
                # thread, then SetForegroundWindow, and toggle TOPMOST to force the
                # z-order. Works for normal + borderless-fullscreen windows (true
                # EXCLUSIVE-fullscreen games can still resist -- a Windows limit).
                $fg = [OSCW32]::GetForegroundWindow()
                $fgT = 0; [void][OSCW32]::GetWindowThreadProcessId($fg, [ref]$fgT)
                $myT = [OSCW32]::GetCurrentThreadId()
                [OSCW32]::keybd_event(0x12, 0, 0, [IntPtr]::Zero)   # Alt down
                [OSCW32]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)   # Alt up (KEYEVENTF_KEYUP)
                $att = $false
                if ($fgT -ne 0 -and $fgT -ne $myT) { $att = [OSCW32]::AttachThreadInput($myT, $fgT, $true) }
                [void][OSCW32]::ShowWindow($p, 9)        # SW_RESTORE
                [void][OSCW32]::BringWindowToTop($p)
                [void][OSCW32]::SetForegroundWindow($p)
                [void][OSCW32]::SetWindowPos($p, [IntPtr](-1), 0, 0, 0, 0, 0x0003)  # HWND_TOPMOST, NOMOVE|NOSIZE
                [void][OSCW32]::SetWindowPos($p, [IntPtr](-2), 0, 0, 0, 0, 0x0003)  # HWND_NOTOPMOST
                if ($att) { [void][OSCW32]::AttachThreadInput($myT, $fgT, $false) }
            }
            # move/resize/center use SetWindowPos with SWP_ASYNCWINDOWPOS instead
            # of MoveWindow (operator 2026-05-29: the executor stalled DURING a
            # launch -> centering hung the single-threaded listener). MoveWindow
            # (and a repaint:$true SetWindowPos) SENDS WM_WINDOWPOSCHANGING/paint
            # SYNCHRONOUSLY to the target window's message loop and BLOCKS until
            # it acks -- a freshly-launched app isn't pumping its queue yet, so
            # the call hangs for seconds and every queued /windows poll behind it
            # times out. SWP_ASYNCWINDOWPOS (0x4000) POSTS the request to the
            # target thread and returns immediately -> the listener never blocks.
            #   SWP_NOSIZE=0x1 NOMOVE=0x2 NOZORDER=0x4 NOACTIVATE=0x10 SHOWWINDOW=0x40 ASYNC=0x4000
            'move'   { [void][OSCW32]::SetWindowPos($p, [IntPtr]::Zero, [int]$x, [int]$y, 0, 0, 0x4015) }  # async|nozorder|noactivate|nosize
            'resize' { [void][OSCW32]::SetWindowPos($p, [IntPtr]::Zero, 0, 0, [int]$w, [int]$h, 0x4016) }  # async|nozorder|noactivate|nomove
            'center' {
                Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
                $sc = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
                $cw = [int]$wnd.w; $ch = [int]$wnd.h
                $cx = $sc.X + [int](($sc.Width - $cw) / 2)
                $cy = $sc.Y + [int](($sc.Height - $ch) / 2)
                # async|nozorder|showwindow -- positions+sizes+shows without blocking;
                # no NOACTIVATE so a centered window stays usable, no synchronous
                # ShowWindow/SetForegroundWindow (both can also block a busy app).
                [void][OSCW32]::SetWindowPos($p, [IntPtr]::Zero, $cx, $cy, $cw, $ch, 0x4044)
            }
            'state'  {
                $n = 1
                if ($state -eq 'minimize') { $n = 6 }
                elseif ($state -eq 'maximize') { $n = 3 }
                elseif ($state -eq 'restore')  { $n = 9 }
                [void][OSCW32]::ShowWindow($p, $n)
            }
        }
        [void]$done.Add(@{ hwnd = $wnd.hwnd; title = $wnd.title; proc = $wnd.proc })
    }
    return @{ ok = $true; op = $op; count = $done.Count; matched = $done }
}

# ---- input (SendInput-equivalent) + capture on the interactive desktop -------
# These mirror mios-pc-control.ps1 but run IN the executor's interactive session
# so SetCursorPos / mouse_event / SendKeys hit WinSta0\Default (the operator's
# real desktop), not a blind service window station.
function Invoke-MouseMove($x, $y) {
    [void][OSCW32]::SetCursorPos([int]$x, [int]$y)
    return @{ ok = $true; op = 'mouse-move'; x = [int]$x; y = [int]$y }
}

function Invoke-Click($x, $y, $button) {
    [void][OSCW32]::SetCursorPos([int]$x, [int]$y)
    Start-Sleep -Milliseconds 50
    $btn = "$button"; if (-not $btn) { $btn = 'left' }
    switch ($btn) {
        'left'   { [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_LEFTDOWN,0,0,0,[IntPtr]::Zero);  [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_LEFTUP,0,0,0,[IntPtr]::Zero) }
        'right'  { [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_RIGHTDOWN,0,0,0,[IntPtr]::Zero); [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_RIGHTUP,0,0,0,[IntPtr]::Zero) }
        'middle' { [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_MIDDLEDOWN,0,0,0,[IntPtr]::Zero);[OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_MIDDLEUP,0,0,0,[IntPtr]::Zero) }
        default  { return @{ ok = $false; error = "unknown button '$btn'" } }
    }
    return @{ ok = $true; op = 'click'; button = $btn; x = [int]$x; y = [int]$y }
}

function Invoke-DoubleClick($x, $y) {
    [void][OSCW32]::SetCursorPos([int]$x, [int]$y)
    Start-Sleep -Milliseconds 50
    [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_LEFTDOWN,0,0,0,[IntPtr]::Zero); [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_LEFTUP,0,0,0,[IntPtr]::Zero)
    Start-Sleep -Milliseconds 50
    [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_LEFTDOWN,0,0,0,[IntPtr]::Zero); [OSCW32]::mouse_event([OSCW32]::MOUSEEVENTF_LEFTUP,0,0,0,[IntPtr]::Zero)
    return @{ ok = $true; op = 'double-click'; x = [int]$x; y = [int]$y }
}

# ── UIA semantic element targeting (operator 2026-06-15; the #1 Windows gap --
# Linux has AT-SPI, Windows control was pixel-only). Find a control BY NAME via UI
# Automation, scoped to the FOREGROUND window's subtree (fast; avoids a whole-
# desktop tree walk that can hang), returning its clickable CENTER so the agent
# acts on a SEMANTIC target instead of guessed pixels. NOT arbitrary code exec --
# only enumerates + acts on the active window's accessibility tree.
$script:UIA_OK = $false
try {
    Add-Type -AssemblyName UIAutomationClient -ErrorAction Stop
    Add-Type -AssemblyName UIAutomationTypes  -ErrorAction Stop
    $script:UIA_OK = $true
} catch { $script:UIA_OK = $false }

function Find-UIElements($name, $maxN) {
    if (-not $script:UIA_OK) { return @() }
    if (-not $maxN -or $maxN -le 0) { $maxN = 15 }
    $fg = [OSCW32]::GetForegroundWindow()
    $root = $null
    try { if ($fg -ne [IntPtr]::Zero) { $root = [System.Windows.Automation.AutomationElement]::FromHandle($fg) } } catch {}
    if (-not $root) { $root = [System.Windows.Automation.AutomationElement]::RootElement }
    $out = @()
    try {
        $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                             [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($el in $all) {
            $nm = ''
            try { $nm = [string]$el.Current.Name } catch {}
            if (-not $nm) { continue }
            if ($name -and ($nm -notlike "*$name*")) { continue }
            $rect = $null
            try { $rect = $el.Current.BoundingRectangle } catch {}
            if (-not $rect -or $rect.Width -le 0 -or $rect.Height -le 0) { continue }
            $ct = ''; $aid = ''
            try { $ct = [string]$el.Current.ControlType.ProgrammaticName } catch {}
            try { $aid = [string]$el.Current.AutomationId } catch {}
            $out += @{ name = $nm; control_type = $ct; automation_id = $aid;
                       x = [int]$rect.X; y = [int]$rect.Y; w = [int]$rect.Width; h = [int]$rect.Height;
                       cx = [int]($rect.X + $rect.Width / 2); cy = [int]($rect.Y + $rect.Height / 2) }
            if ($out.Count -ge $maxN) { break }
        }
    } catch {}
    return $out
}

# Read-back helpers for type verification: the FOREGROUND-window title and the
# focused control's text (UIA Value/Text pattern). Used to confirm typed text
# ACTUALLY landed, so the executor never reports a false success.
function Get-FgTitleRaw {
    $sb = New-Object System.Text.StringBuilder 512
    [void][OSCW32]::GetWindowText([OSCW32]::GetForegroundWindow(), $sb, 512)
    return $sb.ToString()
}
function Get-FocusedTextRaw {
    if (-not $script:UIA_OK) { return $null }
    try {
        $fe = [System.Windows.Automation.AutomationElement]::FocusedElement
        if ($null -eq $fe) { return $null }
        $vp = $null
        if ($fe.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) {
            return $vp.Current.Value
        }
        $tp = $null
        if ($fe.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$tp)) {
            return $tp.DocumentRange.GetText(4096)
        }
    } catch { }
    return $null
}

function Invoke-TypeText($text) {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    $t = "$text"
    # READ-BACK VERIFICATION (operator 2026-06-16 "LIAR": never claim a type
    # succeeded unless the text actually landed). This is the PRIMARY type path
    # (the agent's pc_type POSTs here), so it previously returned ok=$true
    # UNCONDITIONALLY -- a keystroke that hit the wrong window / got dropped still
    # read as success. Mirror the proven mios-pc-control.ps1 read-back: capture the
    # focused-control value + foreground title BEFORE and AFTER SendKeys; verified
    # ONLY if the EXACT sent text appears in the focused value OR the (changed)
    # foreground title. ok=$false -> the handler returns HTTP 400 -> the wrapper
    # surfaces it honestly -> the orchestrator can retry / report uncertainty.
    $titleBefore = Get-FgTitleRaw
    $valBefore = Get-FocusedTextRaw
    # SendKeys interprets {} +^%~ specially; escape them.
    $escaped = ($t -replace '([+\^%~(){}\[\]])', '{$1}')
    # Pre-type settle: a freshly focused window often is not ready the instant after
    # focus, dropping LEADING characters ("DEHARD-5566" -> "RD-5566").
    Start-Sleep -Milliseconds 250
    # SendWait throws "Access is denied" when input injection is BLOCKED -- almost
    # always because the interactive desktop session is DISCONNECTED/locked (no
    # active input desktop) or an ELEVATED window holds the foreground (UIPI). Catch
    # it and return a CLASSIFIED, actionable reason instead of a raw exception string
    # surfaced as a generic 500 -- the agent (and operator) then see the real cause,
    # not a misleading network/permissions guess (operator 2026-06-16 anti-fabrication).
    try {
        [System.Windows.Forms.SendKeys]::SendWait($escaped)
    } catch {
        $msg = "$($_.Exception.Message)"
        $detail = if ($msg -match 'Access is denied') {
            'input injection blocked -- the interactive desktop session is likely DISCONNECTED/locked, or an ELEVATED window holds the foreground (UIPI). Reconnect the session (or run the executor elevated) to enable typing.'
        } else { $msg }
        return @{ ok = $false; verified = $false; op = 'type';
                  reason = 'input_injection_blocked'; detail = $detail;
                  error = $msg; chars = $t.Length }
    }
    Start-Sleep -Milliseconds 400
    $titleAfter = Get-FgTitleRaw
    $valAfter = Get-FocusedTextRaw
    # STRICT: success ONLY if the EXACT sent text appears (a partial / dropped result
    # must NOT pass -- "value grew" alone was the residual lie).
    $verified = $false
    $reason = 'text_not_delivered'
    if (($null -ne $valAfter) -and $valAfter.Contains($t)) {
        $verified = $true; $reason = 'uia_value_contains_text'
    } elseif (($titleAfter -ne $titleBefore) -and $titleAfter.Contains($t)) {
        $verified = $true; $reason = 'title_contains_text'
    } elseif (($null -eq $valAfter) -and ($titleAfter -eq $titleBefore)) {
        $reason = 'no_verifiable_target'
    } else {
        $reason = 'text_mismatch_partial_or_dropped'
    }
    $vc = ''
    if ($null -ne $valAfter) { $vc = $valAfter.Substring(0, [Math]::Min(160, $valAfter.Length)) }
    return @{ ok = $verified; verified = $verified; op = 'type'; reason = $reason;
             chars = $t.Length; title_before = $titleBefore; title_after = $titleAfter;
             focused_text_after = $vc }
}

function Invoke-Key($name) {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    $sk = switch -Regex ("$name") {
        '^(Enter|Return)$' { '{ENTER}' }
        '^(Tab)$'          { '{TAB}' }
        '^(Esc(ape)?)$'    { '{ESC}' }
        '^(Backspace|BS)$' { '{BACKSPACE}' }
        '^(Delete|Del)$'   { '{DELETE}' }
        '^Up$'             { '{UP}' }
        '^Down$'           { '{DOWN}' }
        '^Left$'           { '{LEFT}' }
        '^Right$'          { '{RIGHT}' }
        '^Home$'           { '{HOME}' }
        '^End$'            { '{END}' }
        '^F\d+$'           { "{$name}" }
        default            { "$name" }
    }
    [System.Windows.Forms.SendKeys]::SendWait($sk)
    return @{ ok = $true; op = 'key'; key = "$name"; sent = $sk }
}

function Invoke-KeyCombo($combo) {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    $parts = ("$combo" -split '\+')
    $key = $parts[-1]
    $mods = ''
    if ($parts.Count -ge 2) {
        foreach ($m in $parts[0..($parts.Count - 2)]) {
            switch ($m.ToLower()) {
                'ctrl'  { $mods += '^' }
                'alt'   { $mods += '%' }
                'shift' { $mods += '+' }
                'win'   { $mods += '#' }
            }
        }
    }
    [System.Windows.Forms.SendKeys]::SendWait($mods + $key)
    return @{ ok = $true; op = 'key-combo'; combo = "$combo" }
}

function Get-ScreenLayout {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    $screens = [System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
        @{ device = $_.DeviceName; primary = [bool]$_.Primary;
           bounds = @{ x = $_.Bounds.X; y = $_.Bounds.Y; width = $_.Bounds.Width; height = $_.Bounds.Height };
           work   = @{ x = $_.WorkingArea.X; y = $_.WorkingArea.Y; width = $_.WorkingArea.Width; height = $_.WorkingArea.Height } }
    }
    return @{ ok = $true; count = @($screens).Count; screens = @($screens) }
}

function Invoke-Screenshot {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing -ErrorAction SilentlyContinue
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.X, $b.Y, 0, 0, $b.Size)
    $ms = New-Object System.IO.MemoryStream
    $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    $b64 = [Convert]::ToBase64String($ms.ToArray())
    $ms.Dispose()
    return @{ ok = $true; format = 'png'; width = $b.Width; height = $b.Height; image_b64 = $b64 }
}

# Resolve an app name to a launch target. Returns the thing Start-Process can
# take: a Start-Menu .lnk path if one matches, else the bare name (Start-Process
# handles exe-on-PATH, registered apps, protocols/URIs like ms-settings:).
# Cached index of Start-Menu .lnks: @(@{Name;Path;Wslg}). The recursive scan +
# per-shortcut COM target-resolution (for the WSLg-skip) is the per-launch cost
# the executor-first routing added; cache it with a TTL so repeat launches are
# instant (operator 2026-05-29 "streamlined, fast and perfected"). Installs are
# rare -> a 60s TTL is safe; a cold cache (first launch / post-install) pays the
# full scan once. script: scope so it survives across requests.
function Get-StartMenuIndex {
    $now = [DateTime]::UtcNow
    if ($script:OSCLnkIdx -and $script:OSCLnkTs -and
        (($now - $script:OSCLnkTs).TotalSeconds -le 60)) {
        return $script:OSCLnkIdx
    }
    $menus = @(
        (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs'),
        (Join-Path $env:APPDATA      'Microsoft\Windows\Start Menu\Programs')
    )
    $wsh = New-Object -ComObject WScript.Shell
    $idx = New-Object System.Collections.ArrayList
    foreach ($m in $menus) {
        if (-not (Test-Path $m)) { continue }
        foreach ($f in (Get-ChildItem -Path $m -Recurse -Filter '*.lnk' -ErrorAction SilentlyContinue)) {
            $t = ''
            try { $t = $wsh.CreateShortcut($f.FullName).TargetPath } catch {}
            [void]$idx.Add(@{ Name = $f.BaseName; Path = $f.FullName;
                              Wslg = (($t -like '*wslg.exe') -or ($t -like '*wsl.exe')) })
        }
    }
    $script:OSCLnkIdx = $idx
    $script:OSCLnkTs  = $now
    return $idx
}

function Resolve-LaunchTarget($name) {
    $n = $name.Trim()
    if (-not $n) { return $null }
    # Direct path / protocol / URL -> hand straight to Start-Process.
    if ($n -match '^[a-zA-Z]:\\' -or $n -match '^[a-zA-Z][a-zA-Z0-9+.\-]*:' -or (Test-Path $n -ErrorAction SilentlyContinue)) {
        return $n
    }
    # Match the cached Start-Menu index, SKIPPING WSLg-exported shortcuts
    # (target = WSL\wslg.exe -- those launch a LINUX flatpak through WSLg, which
    # on the executor is slow + bypasses the operator's trained flatpak path;
    # letting the executor MISS makes mios-launch fall back to Linux). A NATIVE
    # Windows app .lnk targets a real .exe and is kept -- "codium" picks the
    # native VSCodium over the WSLg one; "discord"/"notepad" resolve normally.
    # Prefer the SHORTEST matching BaseName.
    $cand = Get-StartMenuIndex |
            Where-Object { (-not $_.Wslg) -and ($_.Name -like "*$n*") } |
            Sort-Object { $_.Name.Length } | Select-Object -First 1
    if ($cand) { return $cand.Path }
    return $n   # let Start-Process try it as a PATH exe / registered app
}

# FIRE a launch on this node's desktop, then poll for the window.
function Invoke-LaunchAndVerify($app, $center = $false, $verifyName = '') {
    # Window-match needle: prefer the human title hint -- a steam:// URI or a
    # shell:appsFolder string never appears in a window title, so verifying a
    # game by $app would always miss (operator 2026-05-30). Falls back to $app.
    $wname = if ([string]::IsNullOrWhiteSpace($verifyName)) { $app } else { $verifyName }
    $target = Resolve-LaunchTarget $app
    $fired  = $false
    $fireErr = ''
    if ($target) {
        try {
            if ($target -like 'shell:*') {
                # UWP / Store / Xbox apps: Start-Process can't grok shell: URIs
                # (treats them as filesystem paths); explorer.exe is the handler.
                Start-Process -FilePath 'explorer.exe' -ArgumentList $target -ErrorAction Stop
            } else {
                # exe paths, names, AND protocol URIs (steam:// epic:// uplay://
                # ...) -- Start-Process invokes the registered protocol handler.
                Start-Process -FilePath $target -ErrorAction Stop
            }
            $fired = $true
        } catch { $fireErr = $_.Exception.Message }
    } else {
        $fireErr = 'could not resolve launch target'
    }
    # FAST MISS: if the launch did NOT fire (target unresolvable on Windows /
    # Start-Process threw -- e.g. a Linux-only flatpak name), return immediately
    # instead of sleeping + polling for a window that was never started. The
    # executor is now tried FIRST for every app (operator 2026-05-29), so a
    # non-Windows app must fall through to the Linux chain cheaply.
    if (-not $fired) {
        return @{ app = $app; node = $env:COMPUTERNAME; host = $env:COMPUTERNAME;
                  target = "$target"; fired = $false; fire_error = $fireErr;
                  launched = $false; centered = $false;
                  verdict = @{ launched = $false; summary = 'not-fired' };
                  ts = [int][double]::Parse((Get-Date -UFormat %s)) }
    }
    Start-Sleep -Seconds $VerifySettleSeconds
    $verdict = @{ launched = $false; summary = 'no-window' }
    for ($i = 0; $i -lt [Math]::Max(1,$VerifyAttempts); $i++) {
        $verdict = Test-WindowPresent $wname
        if ($verdict.launched) { break }
        if ($i -lt ($VerifyAttempts - 1)) { Start-Sleep -Seconds $VerifyIntervalSeconds }
    }
    # CENTER the launched window (operator 2026-05-29: "launches are ALWAYS
    # centered -- the default MiOS opening pattern"). Center, briefly settle,
    # center AGAIN: Electron apps (Discord) restore their saved WINDOW_BOUNDS a
    # beat after the window maps, which undoes a single early center (proven
    # live: Discord snapped back to 229,125). The second center -- after the
    # restore -- wins. Async SetWindowPos, so neither call blocks the listener.
    $centered = $false
    if ($center -and $verdict.launched) {
        try {
            [void](Invoke-WindowOp 'center' $null $wname 0 0 0 0 '')
            Start-Sleep -Milliseconds 900
            [void](Invoke-WindowOp 'center' $null $wname 0 0 0 0 '')
            $centered = $true
        } catch {}
    }
    return @{
        app      = $app
        node     = $env:COMPUTERNAME
        host     = $env:COMPUTERNAME
        target   = "$target"
        fired    = $fired
        fire_error = $fireErr
        launched = [bool]$verdict.launched
        centered = $centered
        verdict  = $verdict
        ts       = [int][double]::Parse((Get-Date -UFormat %s))
    }
}

# ---- minimal query-string parser (System.Web not guaranteed on 5.1) ----------
function Get-QueryValue($rawUrl, $key) {
    $q = ''
    $idx = $rawUrl.IndexOf('?')
    if ($idx -ge 0) { $q = $rawUrl.Substring($idx + 1) }
    foreach ($pair in $q.Split('&')) {
        $kv = $pair.Split('=', 2)
        if ($kv.Length -eq 2 -and $kv[0] -eq $key) {
            return [Uri]::UnescapeDataString($kv[1])
        }
    }
    return ''
}

function Read-JsonBody($ctx) {
    $body = ''
    $reader = New-Object System.IO.StreamReader($ctx.Request.InputStream, $ctx.Request.ContentEncoding)
    try { $body = $reader.ReadToEnd() } finally { $reader.Close() }
    if (-not $body) { return $null }
    try { return ($body | ConvertFrom-Json) } catch { return $null }
}

function Write-JsonResponse($ctx, $code, $obj) {
    $json = $obj | ConvertTo-Json -Depth 6 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $ctx.Response.StatusCode = $code
    $ctx.Response.ContentType = 'application/json'
    $ctx.Response.ContentLength64 = $bytes.Length
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    $ctx.Response.OutputStream.Close()
}

# ---- HttpListener loop -------------------------------------------------------
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://+:$Port/")
try {
    $listener.Start()
} catch {
    Warn "HttpListener could not bind '+:$Port' (need elevation or a urlacl)."
    Warn "Fix: run elevated, or: netsh http add urlacl url=http://+:$Port/ user=$env:USERNAME"
    throw
}
$tsIp = (Get-NetIPAddress -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -like '100.*' } | Select-Object -First 1).IPAddress
Ok "MiOS OS-control executor listening on http://+:$Port/  (tailnet -> http://$tsIp`:$Port)"
$logFile = Join-Path $logDir ("oscontrol-{0:yyyyMMdd}.log" -f (Get-Date))

while ($listener.IsListening) {
    $ctx = $null
    try { $ctx = $listener.GetContext() } catch { break }
    try {
        $method = $ctx.Request.HttpMethod
        $path   = $ctx.Request.Url.AbsolutePath.TrimEnd('/')
        if ($path -eq '') { $path = '/' }

        if ($method -eq 'GET' -and $path -eq '/health') {
            Write-JsonResponse $ctx 200 @{ ok = $true; host = $env:COMPUTERNAME;
                                           ts = [int][double]::Parse((Get-Date -UFormat %s)) }
        }
        elseif ($method -eq 'GET' -and $path -eq '/verify') {
            $app = Get-QueryValue $ctx.Request.Url.OriginalString 'app'
            if (-not $app) { Write-JsonResponse $ctx 400 @{ error = 'missing ?app=' } }
            else {
                $v = Test-WindowPresent $app
                Write-JsonResponse $ctx 200 @{ app = $app; launched = [bool]$v.launched;
                                               verdict = $v; host = $env:COMPUTERNAME }
            }
        }
        elseif ($method -eq 'POST' -and $path -eq '/launch') {
            $body = ''
            $reader = New-Object System.IO.StreamReader($ctx.Request.InputStream, $ctx.Request.ContentEncoding)
            try { $body = $reader.ReadToEnd() } finally { $reader.Close() }
            $app = ''; $center = $false; $verify = ''
            if ($body) {
                try {
                    $j = $body | ConvertFrom-Json
                    $app = ([string]$j.app).Trim()
                    # Default-ON: launches center by default (operator binding
                    # "launches are ALWAYS centered"); only an explicit false opts out.
                    if ($j.PSObject.Properties.Name -contains 'center') {
                        $center = [bool]$j.center
                    } else { $center = $true }
                    # Optional human title hint for the window-match (games: a
                    # steam:// URI never matches a window title).
                    if ($j.PSObject.Properties.Name -contains 'verify') {
                        $verify = ([string]$j.verify).Trim()
                    }
                } catch { $app = ''; $center = $true }
            }
            if (-not $app) { Write-JsonResponse $ctx 400 @{ error = "missing 'app' in JSON body" } }
            else {
                $r = Invoke-LaunchAndVerify $app $center $verify
                ("{0}  launch app={1} fired={2} launched={3}" -f (Get-Date -Format s), $app, $r.fired, $r.launched) |
                    Out-File -FilePath $logFile -Append -Encoding utf8
                Write-JsonResponse $ctx 200 $r
            }
        }
        elseif ($method -eq 'GET' -and $path -eq '/windows') {
            # Enumerate ALL visible top-level windows (the grounding snapshot
            # the agent records before/after open+close to diff what changed).
            $wins = @(Get-VisibleWindows)
            Write-JsonResponse $ctx 200 @{ ok = $true; count = $wins.Count;
                                           windows = $wins; host = $env:COMPUTERNAME }
        }
        elseif ($method -eq 'POST' -and $path -like '/window/*') {
            $op = $path.Substring('/window/'.Length)
            $b  = Read-JsonBody $ctx
            $hwnd  = $null; $title = ''; $x = 0; $y = 0; $ww = 0; $hh = 0; $state = 'restore'
            if ($b) {
                if ($b.PSObject.Properties.Name -contains 'hwnd'  -and $b.hwnd)  { $hwnd = [int64]$b.hwnd }
                if ($b.PSObject.Properties.Name -contains 'title') { $title = "$($b.title)" }
                if ($b.PSObject.Properties.Name -contains 'x')      { $x  = [int]$b.x }
                if ($b.PSObject.Properties.Name -contains 'y')      { $y  = [int]$b.y }
                if ($b.PSObject.Properties.Name -contains 'width')  { $ww = [int]$b.width }
                if ($b.PSObject.Properties.Name -contains 'height') { $hh = [int]$b.height }
                if ($b.PSObject.Properties.Name -contains 'state')  { $state = "$($b.state)" }
            }
            if ($op -notin @('close','focus','move','resize','state','center')) {
                Write-JsonResponse $ctx 404 @{ error = "unknown window op '$op'" }
            }
            elseif (-not $hwnd -and -not $title.Trim()) {
                Write-JsonResponse $ctx 400 @{ error = "need 'hwnd' or 'title'" }
            }
            else {
                $r = Invoke-WindowOp $op $hwnd $title $x $y $ww $hh $state
                ("{0}  window {1} title='{2}' hwnd={3} count={4}" -f (Get-Date -Format s), $op, $title, $hwnd, $r.count) |
                    Out-File -FilePath $logFile -Append -Encoding utf8
                $code = 200
                if (-not $r.ok) { $code = 404 }
                Write-JsonResponse $ctx $code $r
            }
        }
        elseif ($method -eq 'GET' -and $path -eq '/screen-layout') {
            Write-JsonResponse $ctx 200 (Get-ScreenLayout)
        }
        elseif ($method -eq 'GET' -and $path -eq '/screenshot') {
            Write-JsonResponse $ctx 200 (Invoke-Screenshot)
        }
        elseif ($method -eq 'POST' -and $path -like '/input/*') {
            $op = $path.Substring('/input/'.Length)
            $b  = Read-JsonBody $ctx
            $x = 0; $y = 0; $text = ''; $name = ''; $combo = ''; $button = 'left'
            if ($b) {
                if ($b.PSObject.Properties.Name -contains 'x')      { $x = [int]$b.x }
                if ($b.PSObject.Properties.Name -contains 'y')      { $y = [int]$b.y }
                if ($b.PSObject.Properties.Name -contains 'text')   { $text = "$($b.text)" }
                if ($b.PSObject.Properties.Name -contains 'name')   { $name = "$($b.name)" }
                if ($b.PSObject.Properties.Name -contains 'combo')  { $combo = "$($b.combo)" }
                if ($b.PSObject.Properties.Name -contains 'button') { $button = "$($b.button)" }
            }
            $r = $null
            switch ($op) {
                'mouse-move'   { $r = Invoke-MouseMove $x $y }
                'click'        { $r = Invoke-Click $x $y $button }
                'double-click' { $r = Invoke-DoubleClick $x $y }
                'type'         { $r = Invoke-TypeText $text }
                'key'          { $r = Invoke-Key $name }
                'key-combo'    { $r = Invoke-KeyCombo $combo }
                default        { $r = @{ ok = $false; error = "unknown input op '$op'" } }
            }
            $code = 200
            if (-not $r.ok) { $code = 400 }
            ("{0}  input {1}" -f (Get-Date -Format s), $op) | Out-File -FilePath $logFile -Append -Encoding utf8
            Write-JsonResponse $ctx $code $r
        }
        elseif ($method -eq 'POST' -and ($path -eq '/ui/find' -or $path -eq '/ui/click')) {
            # UIA semantic targeting: /ui/find lists matching controls in the
            # foreground window; /ui/click finds the first match + clicks its
            # center. Element-targeting only -- no arbitrary code execution.
            $b = Read-JsonBody $ctx
            $name = ''
            if ($b -and ($b.PSObject.Properties.Name -contains 'name')) { $name = "$($b.name)" }
            if (-not $name.Trim()) {
                Write-JsonResponse $ctx 400 @{ ok = $false; error = "missing 'name'" }
            }
            elseif (-not $script:UIA_OK) {
                Write-JsonResponse $ctx 200 @{ ok = $false; error = 'UIA unavailable on this host'; host = $env:COMPUTERNAME }
            }
            elseif ($path -eq '/ui/find') {
                $els = @(Find-UIElements $name 15)
                Write-JsonResponse $ctx 200 @{ ok = ($els.Count -gt 0); count = $els.Count; elements = $els; host = $env:COMPUTERNAME }
            }
            else {
                $els = @(Find-UIElements $name 1)
                if ($els.Count -eq 0) {
                    Write-JsonResponse $ctx 404 @{ ok = $false; error = "no UIA element matching '$name' in the foreground window"; host = $env:COMPUTERNAME }
                }
                else {
                    $e = $els[0]
                    [void](Invoke-Click $e.cx $e.cy 'left')
                    ("{0}  ui-click name='{1}' -> ({2},{3})" -f (Get-Date -Format s), $name, $e.cx, $e.cy) | Out-File -FilePath $logFile -Append -Encoding utf8
                    Write-JsonResponse $ctx 200 @{ ok = $true; clicked = $true; element = $e; host = $env:COMPUTERNAME }
                }
            }
        }
        elseif ($method -eq 'GET' -and $path -eq '/ui/list') {
            # SoM-first grounding (operator 2026-06-15): list ALL named controls in the
            # FOREGROUND window (the UIA tree AS the set-of-marks) so the agent surveys
            # them + picks one to click by name/center -- coordinate-free, no VLM needed
            # for UIA surfaces. (Vision-overlay SoM for non-UIA canvas surfaces is the
            # remaining fallback.)
            if (-not $script:UIA_OK) {
                Write-JsonResponse $ctx 200 @{ ok = $false; error = 'UIA unavailable on this host'; host = $env:COMPUTERNAME }
            }
            else {
                $els = @(Find-UIElements '' 40)
                for ($i = 0; $i -lt $els.Count; $i++) { $els[$i].mark = $i + 1 }
                Write-JsonResponse $ctx 200 @{ ok = ($els.Count -gt 0); count = $els.Count; elements = $els; host = $env:COMPUTERNAME }
            }
        }
        else {
            Write-JsonResponse $ctx 404 @{ error = 'not found'; path = $path; method = $method }
        }
    } catch {
        try { Write-JsonResponse $ctx 500 @{ error = "$($_.Exception.Message)" } } catch {}
    }
}
