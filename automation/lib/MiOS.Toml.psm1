# AI-hint: Single-sourced PowerShell module for resolving mios.toml values across Windows PowerShell scripts.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path Variable:script:_MiosTomlCache)) {
    $script:_MiosTomlCache = @{}
}

function Resolve-MiosTomlText {
    if ($script:_MiosTomlCache.ContainsKey('_text') -and $script:_MiosTomlCache['_text']) {
        return $script:_MiosTomlCache['_text']
    }

    $candidates = @(
        (Join-Path $env:USERPROFILE '.config\mios\mios.toml'),
        'M:\etc\mios\mios.toml',
        'M:\usr\share\mios\mios.toml',
        'C:\mios-bootstrap\mios.toml',
        'C:\ProgramData\MiOS\mios.toml',
        (Join-Path $PSScriptRoot '..\..\usr\share\mios\mios.toml')
    )

    foreach ($p in $candidates) {
        if ($p -and (Test-Path -LiteralPath $p)) {
            try {
                $script:_MiosTomlCache['_text']   = [System.IO.File]::ReadAllText($p, (New-Object System.Text.UTF8Encoding($false)))
                $script:_MiosTomlCache['_source'] = $p
                return $script:_MiosTomlCache['_text']
            } catch {
                try {
                    $script:_MiosTomlCache['_text']   = Get-Content -LiteralPath $p -Raw -Encoding UTF8 -ErrorAction Stop
                    $script:_MiosTomlCache['_source'] = $p
                    return $script:_MiosTomlCache['_text']
                } catch {}
            }
        }
    }

    try {
        $cb  = [int][double]::Parse((Get-Date -UFormat %s))
        $ref = if ($null -ne $global:MiosRef -and $global:MiosRef) { $global:MiosRef } else { 'main' }
        $url = "https://raw.githubusercontent.com/mios-dev/MiOS/$ref/usr/share/mios/mios.toml?cb=$cb"
        $resp = Invoke-WebRequest -Uri $url `
            -Headers @{ 'Cache-Control'='no-cache, no-store, max-age=0'; 'Pragma'='no-cache' } `
            -UseBasicParsing -ErrorAction Stop
        if ($resp.Content -is [byte[]]) {
            $script:_MiosTomlCache['_text'] = [System.Text.Encoding]::UTF8.GetString($resp.Content)
        } else {
            $script:_MiosTomlCache['_text'] = [string]$resp.Content
        }
        $script:_MiosTomlCache['_source'] = "origin/$ref (web)"
        return $script:_MiosTomlCache['_text']
    } catch {
        $script:_MiosTomlCache['_text']   = ''
        $script:_MiosTomlCache['_source'] = '(unreachable)'
        return ''
    }
}

function Get-MiosTomlValue {
    param(
        [Parameter(Mandatory)][string]$Section,
        [Parameter(Mandatory)][string]$Key,
        [Parameter(Mandatory)]$Default
    )
    $txt = Resolve-MiosTomlText
    if (-not $txt) { return $Default }

    $rxSec = '(?ms)^\[' + [regex]::Escape($Section) + '\][ \t]*\r?\n(?<body>.*?)(?=^\[[^\]]+\]|\z)'
    $mSec  = [regex]::Match($txt, $rxSec)
    if (-not $mSec.Success) { return $Default }

    $rxKey = '(?m)^[ \t]*' + [regex]::Escape($Key) + '[ \t]*=[ \t]*(?<val>.+?)[ \t]*(?:#.*)?$'
    $mKey  = [regex]::Match($mSec.Groups['body'].Value, $rxKey)
    if (-not $mKey.Success) { return $Default }

    $raw = $mKey.Groups['val'].Value.Trim()
    if ($Default -is [int]) {
        $n = 0
        if ([int]::TryParse(($raw -replace '_',''), [ref]$n)) { return $n }
        return $Default
    }
    if ($Default -is [bool]) {
        if ($raw -eq 'true') { return $true }
        if ($raw -eq 'false') { return $false }
        return $Default
    }
    if ($raw.Length -ge 2 -and (($raw.StartsWith('"') -and $raw.EndsWith('"')) -or ($raw.StartsWith("'") -and $raw.EndsWith("'")))) {
        return $raw.Substring(1, $raw.Length - 2)
    }
    return $raw
}

Export-ModuleMember -Function Resolve-MiosTomlText, Get-MiosTomlValue
