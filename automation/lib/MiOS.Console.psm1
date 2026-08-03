# AI-hint: Console palette and VT100 formatting module resolving from mios.toml [colors] SSOT.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$tomlModule = Join-Path $scriptDir 'MiOS.Toml.psm1'
if (Test-Path -LiteralPath $tomlModule) {
    Import-Module $tomlModule -Force -ErrorAction SilentlyContinue
}

function Convert-HexToRgb {
    param([string]$Hex, [int[]]$DefaultRgb)
    if ($Hex -and $Hex -match '^#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$') {
        try {
            return @(
                [convert]::ToInt32($Matches[1], 16),
                [convert]::ToInt32($Matches[2], 16),
                [convert]::ToInt32($Matches[3], 16)
            )
        } catch {}
    }
    return $DefaultRgb
}

function Get-MiosPalette {
    $defaults = @{
        bg      = @(40,34,98)
        fg      = @(231,223,211)
        accent  = @(26,64,127)
        cursor  = @(243,92,21)
        success = @(62,119,101)
        warning = @(243,92,21)
        error   = @(220,39,27)
        muted   = @(148,142,142)
        subtle  = @(183,201,215)
    }

    $pal = @{}
    foreach ($k in $defaults.Keys) {
        $defHex = '#{0:X2}{1:X2}{2:X2}' -f $defaults[$k][0], $defaults[$k][1], $defaults[$k][2]
        $hex = if (Get-Command Get-MiosTomlValue -ErrorAction SilentlyContinue) {
            Get-MiosTomlValue 'colors' $k $defHex
        } else {
            $defHex
        }
        $pal[$k] = Convert-HexToRgb $hex $defaults[$k]
    }
    return $pal
}

function Enable-MiosVt {
    if ($env:MIOS_NO_COLOR -or $env:NO_COLOR) { return $false }
    if ($env:TERM -and $env:TERM -ne 'dumb') { return $true }
    if ($env:WT_SESSION) { return $true }
    try {
        $code = '[DllImport("kernel32.dll")] public static extern bool GetConsoleMode(IntPtr h, out uint m); [DllImport("kernel32.dll")] public static extern bool SetConsoleMode(IntPtr h, uint m); [DllImport("kernel32.dll")] public static extern IntPtr GetStdHandle(int n);'
        $type = Add-Type -MemberDefinition $code -Name "Win32Console_$([guid]::NewGuid().ToString('N'))" -Namespace "MiosConsole" -PassThru -ErrorAction SilentlyContinue
        if ($type) {
            $h = $type::GetStdHandle(-11)
            $mode = 0
            if ($type::GetConsoleMode($h, [ref]$mode)) {
                $mode = $mode -bor 7
                [void]$type::SetConsoleMode($h, $mode)
                return $true
            }
        }
    } catch {}
    return $true
}

$script:MiosVtOk = Enable-MiosVt
$script:Pal      = Get-MiosPalette

function C {
    param([int[]]$rgb, [string]$t)
    if (-not $script:MiosVtOk -or $env:MIOS_NO_COLOR -or $env:NO_COLOR) { return $t }
    $e = [char]27
    return "$e[38;2;$($rgb[0]);$($rgb[1]);$($rgb[2])m$t$e[0m"
}

function B {
    param([string]$t)
    if (-not $script:MiosVtOk -or $env:MIOS_NO_COLOR -or $env:NO_COLOR) { return $t }
    $e = [char]27
    return "$e[1m$t$e[0m"
}

function Rule {
    param([int]$Width = 64)
    return (C $script:Pal.muted ("=" * $Width))
}

function Write-MiosLine {
    param([string]$Level, [string]$Message)
    $tag = switch ($Level.ToLower()) {
        'info'  { C $script:Pal.accent  (B '[INFO]') }
        'warn'  { C $script:Pal.warning (B '[WARN]') }
        'err'   { C $script:Pal.error   (B '[FAIL]') }
        'pass'  { C $script:Pal.success (B '[PASS]') }
        default { C $script:Pal.muted   (B "[$Level]") }
    }
    Write-Host "  $tag $Message"
}

function Write-MiosKV {
    param([string]$Key, [string]$Value)
    $k = (C $script:Pal.subtle ("{0,-14}" -f $Key))
    $v = (C $script:Pal.fg $Value)
    Write-Host "  $k : $v"
}

Export-ModuleMember -Function Get-MiosPalette, Enable-MiosVt, C, B, Rule, Write-MiosLine, Write-MiosKV
