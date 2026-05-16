# /usr/share/mios/windows/mios-pc-control.ps1
#
# Windows-side computer-use surface for MiOS-Agent. Called from the
# Linux helper /usr/libexec/mios/mios-pc-control via mios-windows ps.
#
# Subcommands (passed via -Action):
#   screenshot <out-path>
#   click <x> <y> [button]
#   double-click <x> <y>
#   mouse-move <x> <y>
#   type "<text>"
#   key <name>
#   key-combo "Ctrl+C"
#   window-list
#   window-focus <hwnd-or-pid>
#   window-move <hwnd> <x> <y>
#   window-resize <hwnd> <w> <h>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0)][string]$Action,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Args
)

# ─── Win32 P/Invoke surface (loaded once) ─────────────────────────
$Win32Sig = @"
using System;
using System.Runtime.InteropServices;
public class W32 {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr i);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int n, bool repaint);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int max);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    public const uint MOUSEEVENTF_LEFTDOWN  = 0x0002;
    public const uint MOUSEEVENTF_LEFTUP    = 0x0004;
    public const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
    public const uint MOUSEEVENTF_RIGHTUP   = 0x0010;
    public const uint MOUSEEVENTF_MIDDLEDOWN= 0x0020;
    public const uint MOUSEEVENTF_MIDDLEUP  = 0x0040;
}
"@
if (-not ([System.Management.Automation.PSTypeName]'W32').Type) {
    Add-Type -TypeDefinition $Win32Sig -ReferencedAssemblies System.Drawing -ErrorAction SilentlyContinue
}

# ─── Subcommand dispatch ─────────────────────────────────────────
switch ($Action) {

    'screenshot' {
        $out = $Args[0]
        if (-not $out) { throw "screenshot: missing <out-path>" }
        Add-Type -AssemblyName System.Windows.Forms, System.Drawing
        $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)
        $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose(); $bmp.Dispose()
        Write-Output ("[mios-pc-control] screenshot saved to {0} ({1}x{2})" -f $out, $bounds.Width, $bounds.Height)
    }

    'mouse-move' {
        $x = [int]$Args[0]; $y = [int]$Args[1]
        [W32]::SetCursorPos($x, $y) | Out-Null
        Write-Output "[mios-pc-control] mouse-move $x $y"
    }

    'click' {
        $x = [int]$Args[0]; $y = [int]$Args[1]
        $btn = if ($Args.Count -ge 3) { $Args[2] } else { 'left' }
        [W32]::SetCursorPos($x, $y) | Out-Null
        Start-Sleep -Milliseconds 50
        switch ($btn) {
            'left'   { [W32]::mouse_event([W32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [IntPtr]::Zero); [W32]::mouse_event([W32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [IntPtr]::Zero) }
            'right'  { [W32]::mouse_event([W32]::MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, [IntPtr]::Zero); [W32]::mouse_event([W32]::MOUSEEVENTF_RIGHTUP, 0, 0, 0, [IntPtr]::Zero) }
            'middle' { [W32]::mouse_event([W32]::MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, [IntPtr]::Zero); [W32]::mouse_event([W32]::MOUSEEVENTF_MIDDLEUP, 0, 0, 0, [IntPtr]::Zero) }
            default  { throw "click: unknown button '$btn'" }
        }
        Write-Output "[mios-pc-control] click $btn at ($x,$y)"
    }

    'double-click' {
        $x = [int]$Args[0]; $y = [int]$Args[1]
        [W32]::SetCursorPos($x, $y) | Out-Null
        Start-Sleep -Milliseconds 50
        [W32]::mouse_event([W32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [IntPtr]::Zero)
        [W32]::mouse_event([W32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [IntPtr]::Zero)
        Start-Sleep -Milliseconds 50
        [W32]::mouse_event([W32]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [IntPtr]::Zero)
        [W32]::mouse_event([W32]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [IntPtr]::Zero)
        Write-Output "[mios-pc-control] double-click at ($x,$y)"
    }

    'type' {
        Add-Type -AssemblyName System.Windows.Forms
        $text = $Args -join ' '
        # SendKeys interprets {} +^%~ specially; escape them.
        $escaped = ($text -replace '([+\^%~(){}\[\]])', '{$1}')
        [System.Windows.Forms.SendKeys]::SendWait($escaped)
        Write-Output "[mios-pc-control] type ($($text.Length) chars)"
    }

    'key' {
        Add-Type -AssemblyName System.Windows.Forms
        $name = $Args[0]
        # SendKeys uses {ENTER}, {TAB}, etc. -- pass the name through.
        $sk = switch -Regex ($name) {
            '^(Enter|Return)$'  { '{ENTER}' }
            '^(Tab)$'           { '{TAB}' }
            '^(Esc(ape)?)$'     { '{ESC}' }
            '^(Backspace|BS)$'  { '{BACKSPACE}' }
            '^(Delete|Del)$'    { '{DELETE}' }
            '^Up$'              { '{UP}' }
            '^Down$'            { '{DOWN}' }
            '^Left$'            { '{LEFT}' }
            '^Right$'           { '{RIGHT}' }
            '^Home$'            { '{HOME}' }
            '^End$'             { '{END}' }
            '^F\d+$'            { "{$name}" }
            default             { $name }
        }
        [System.Windows.Forms.SendKeys]::SendWait($sk)
        Write-Output "[mios-pc-control] key $name -> $sk"
    }

    'key-combo' {
        Add-Type -AssemblyName System.Windows.Forms
        # Translate "Ctrl+C" / "Alt+F4" / "Shift+Tab" / "Win+R" -> SendKeys
        $combo = ($Args -join ' ')
        $parts = $combo -split '\+'
        $key = $parts[-1]
        $mods = ''
        foreach ($m in $parts[0..($parts.Count-2)]) {
            switch ($m.ToLower()) {
                'ctrl'  { $mods += '^' }
                'alt'   { $mods += '%' }
                'shift' { $mods += '+' }
                'win'   { $mods += '#' }   # SendKeys doesn't support Win; will silently no-op on older .NET
            }
        }
        [System.Windows.Forms.SendKeys]::SendWait($mods + $key)
        Write-Output "[mios-pc-control] key-combo $combo"
    }

    'window-list' {
        $rows = @()
        $callback = [W32+EnumWindowsProc]{
            param($h, $l)
            if ([W32]::IsWindowVisible($h)) {
                $len = [W32]::GetWindowTextLength($h)
                if ($len -gt 0) {
                    $sb = New-Object System.Text.StringBuilder ($len + 1)
                    [W32]::GetWindowText($h, $sb, $sb.Capacity) | Out-Null
                    $rect = New-Object W32+RECT
                    [W32]::GetWindowRect($h, [ref]$rect) | Out-Null
                    $proc_pid = 0
                    [W32]::GetWindowThreadProcessId($h, [ref]$proc_pid) | Out-Null
                    $script:rows += [pscustomobject]@{
                        hwnd  = [int64]$h
                        pid   = [int]$proc_pid
                        title = $sb.ToString()
                        x     = $rect.Left
                        y     = $rect.Top
                        w     = $rect.Right - $rect.Left
                        h     = $rect.Bottom - $rect.Top
                    }
                }
            }
            return $true
        }
        $script:rows = @()
        [W32]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
        $script:rows | Format-Table hwnd, pid, x, y, w, h, title -AutoSize
    }

    'window-focus' {
        $arg = $Args[0]
        $hwnd = $null
        if ($arg -match '^\d+$') {
            # Try as PID first; fall back to interpreting as hwnd
            $proc = Get-Process -Id ([int]$arg) -ErrorAction SilentlyContinue
            if ($proc -and $proc.MainWindowHandle -ne 0) {
                $hwnd = $proc.MainWindowHandle
            } else {
                $hwnd = [IntPtr]([int64]$arg)
            }
        } else {
            throw "window-focus: <hwnd-or-pid> must be numeric"
        }
        [W32]::ShowWindow($hwnd, 9) | Out-Null  # SW_RESTORE
        [W32]::BringWindowToTop($hwnd) | Out-Null
        [W32]::SetForegroundWindow($hwnd) | Out-Null
        Write-Output "[mios-pc-control] window-focus hwnd=$hwnd"
    }

    'window-move' {
        $hwnd = [IntPtr]([int64]$Args[0])
        $x = [int]$Args[1]; $y = [int]$Args[2]
        $rect = New-Object W32+RECT
        [W32]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
        $w = $rect.Right - $rect.Left
        $h = $rect.Bottom - $rect.Top
        [W32]::MoveWindow($hwnd, $x, $y, $w, $h, $true) | Out-Null
        Write-Output "[mios-pc-control] window-move hwnd=$hwnd to ($x,$y)"
    }

    'window-resize' {
        $hwnd = [IntPtr]([int64]$Args[0])
        $w = [int]$Args[1]; $h = [int]$Args[2]
        $rect = New-Object W32+RECT
        [W32]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
        [W32]::MoveWindow($hwnd, $rect.Left, $rect.Top, $w, $h, $true) | Out-Null
        Write-Output "[mios-pc-control] window-resize hwnd=$hwnd to ${w}x${h}"
    }

    'window-center' {
        # Center the window on the primary monitor's work area.
        # Usage: window-center <hwnd-or-pid>
        # Operator directive 2026-05-16: "MiOS apps STILL don't center
        # launch and don't self center" -- Windows apps launched via
        # Start-Process appear at default Win32 placement (often top-
        # left or last-position). This puts them in the screen center.
        $arg = $Args[0]
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
        # Try treating $arg as hwnd first; if it's a small int (PID),
        # resolve to the process's main window handle.
        $hwnd = [IntPtr]::Zero
        if ($arg -match '^\d+$' -and [int64]$arg -lt 1000000) {
            try {
                $proc = Get-Process -Id ([int]$arg) -ErrorAction Stop
                $hwnd = $proc.MainWindowHandle
            } catch {}
        }
        if ($hwnd -eq [IntPtr]::Zero) {
            $hwnd = [IntPtr]([int64]$arg)
        }
        if ($hwnd -eq [IntPtr]::Zero) {
            throw "window-center: could not resolve '$arg' to a window handle"
        }
        $rect = New-Object W32+RECT
        [W32]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
        $w = $rect.Right - $rect.Left
        $h = $rect.Bottom - $rect.Top
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
        $x = $screen.X + [int](($screen.Width - $w) / 2)
        $y = $screen.Y + [int](($screen.Height - $h) / 2)
        [W32]::MoveWindow($hwnd, $x, $y, $w, $h, $true) | Out-Null
        [W32]::ShowWindow($hwnd, 9) | Out-Null  # SW_RESTORE
        [W32]::SetForegroundWindow($hwnd) | Out-Null
        Write-Output "[mios-pc-control] window-center hwnd=$hwnd to ($x,$y) ${w}x${h}"
    }

    default {
        throw "mios-pc-control.ps1: unknown action '$Action' (try: screenshot, click, double-click, mouse-move, type, key, key-combo, window-list, window-focus, window-move, window-resize, window-center)"
    }
}
