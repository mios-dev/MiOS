# AI-hint: A Windows-native OCI image exporter that streams rootfs layers directly from container storage to uncompressed .tar or converts disk images to .vhdx via qemu-img.
# AI-doc: usr/share/doc/mios/manual/root.md
<#
.SYNOPSIS
    Windows-native MiOS OCI exporter / converter.

.DESCRIPTION
    Complement to mios-cloud-build.ps1. Exports deployable artifacts for Windows and WSL2:

      WSL2 rootfs   -  Stream the container filesystem directly from container
                       storage (via podman export) to a standard uncompressed
                       .tar preserving all Linux POSIX permissions, ownership,
                       and symlinks. Avoids intermediate NTFS extraction and
                       avoids .tar.zst compression (which causes WSL2 error 0x80070057).

      VHDX          -  Convert an existing qcow2 / raw / vmdk to native .vhdx via
                       qemu-img.exe (Windows port, auto-installed via
                       winget from `qemu.qemu`), importable into WSL2 via --vhd.

      Hyper-V VM    -  Generate a sample New-VM script that attaches the
                       produced VHDX (does NOT auto-import; operator
                       reviews + runs as admin).

.PARAMETER Image
    OCI reference to pull / export. Default: ghcr.io/mios-dev/mios:latest

.PARAMETER OutputDir
    Where artifacts land. Default: M:\MiOS\build\<tag> when M:\ exists,
    otherwise %USERPROFILE%\MiOS-Build\<tag>.

.PARAMETER Tag
    Subdirectory label. Defaults to the image's :tag.

.PARAMETER Targets
    Which surfaces to emit. Default = wsl. vhdx requires a pre-existing
    qcow2 or raw at OutputDir.

.PARAMETER HyperVName
    When 'hyperv' is in -Targets, the VM name to scaffold (default MiOS-Auto).

.EXAMPLE
    .\mios-windows-export.ps1
    Streams the rootfs of ghcr.io/mios-dev/mios:latest from container storage and emits
    mios.wsl.tar under M:\MiOS\build\latest\.

.EXAMPLE
    .\mios-windows-export.ps1 -Targets wsl,vhdx
    Builds the WSL tarball AND -- if a qcow2 or raw is already in the
    output dir -- converts it to mios.vhdx via Windows-native qemu-img.exe.

.NOTES
    WSL2 'wsl --import' requires either an uncompressed .tar rootfs archive
    or a native .vhdx virtual hard disk (imported with the --vhd flag).
    Intermediate extraction to NTFS strips POSIX permissions and symlinks.
    Compressing with .zst causes WSL error 0x80070057.
#>


[CmdletBinding()]
param(
    [string]   $Image      = 'ghcr.io/mios-dev/mios:latest',
    [string]   $OutputDir  = '',
    [string]   $Tag        = '',
    [string[]] $Targets    = @('wsl'),
    [string]   $HyperVName = 'MiOS-Auto'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

$exportModule = Join-Path $PSScriptRoot 'usr\libexec\mios\MiOS.Export.psm1'
if (Test-Path $exportModule) { Import-Module $exportModule -ErrorAction SilentlyContinue }

# -- winget helper -- auto-install qemu + zstd if missing -----------------
# We use winget rather than chocolatey/scoop because winget is bundled in
# every Win10 21H2+ install -- operators don't need a separate package
# manager. The `--scope user` keeps installs in %LOCALAPPDATA%\Microsoft\
# WinGet so we don't trip UAC.
function Test-CommandExists([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WingetTool([string]$WingetId, [string]$BinaryName) {
    if (Test-CommandExists $BinaryName) {
        Write-Ok "$BinaryName already on PATH"
        return $true
    }
    if (-not (Test-CommandExists 'winget')) {
        Write-Bad "winget unavailable; install $BinaryName manually (looking for: $WingetId)"
        return $false
    }
    Write-Step "winget install $WingetId  (for $BinaryName)"
    & winget install --id $WingetId --silent --accept-package-agreements --accept-source-agreements --scope user 2>&1 |
        ForEach-Object { Write-Host ("  winget: " + $_) -ForegroundColor DarkGray }
    if ($LASTEXITCODE -ne 0) {
        # winget exits with various error codes (PACKAGE_ALREADY_INSTALLED,
        # NO_APPLICABLE_INSTALLER) that aren't fatal -- re-check the binary.
        Write-Warn "winget install exit $LASTEXITCODE; re-checking PATH..."
    }
    # winget appends install dirs to USER PATH for next-session shells;
    # we refresh in-process so the current run picks the binary up.
    $env:PATH = [Environment]::GetEnvironmentVariable('PATH','Machine') +
                ';' + [Environment]::GetEnvironmentVariable('PATH','User')
    return (Test-CommandExists $BinaryName)
}

# -- OCI registry helpers (GHCR public-image protocol) --------------------
# GHCR follows the OCI Distribution v1 spec. Public images need an
# anonymous token from /token before /manifests/<ref> succeeds.
function Get-GhcrToken([string]$Repo) {
    $tokUrl = "https://ghcr.io/token?scope=repository:$Repo`:pull&service=ghcr.io"
    $tok = Invoke-RestMethod -Uri $tokUrl -ErrorAction Stop
    if (-not $tok.token) { throw "GHCR /token returned no .token (response: $tok)" }
    return $tok.token
}

# Resolve image ref into (registry, repo, ref). Only ghcr.io is supported
# directly; other registries fall through to a clear error so the operator
# knows to use mios-cloud-build.ps1 + a podman pull instead.
function Resolve-ImageRef([string]$ImageRef) {
    if ($ImageRef -notmatch '^([^/]+)/(.+?)(?::([^:/@]+)|@(sha256:[a-f0-9]+))?$') {
        throw "Cannot parse image reference: $ImageRef"
    }
    $registry = $Matches[1]
    $repo     = $Matches[2]
    $tagOrDig = if ($Matches[3]) { $Matches[3] } elseif ($Matches[4]) { $Matches[4] } else { 'latest' }
    if ($registry -notin @('ghcr.io','registry.ghcr.io')) {
        throw "This Windows-side path only supports ghcr.io. Got: $registry. Use mios-cloud-build.ps1 for other registries."
    }
    return @{ Registry = $registry; Repo = $repo; Ref = $tagOrDig }
}


# -- Output directory resolver ---------------------------------------------
function Resolve-OutputBase {
    if ($script:OutputDir) { return $script:OutputDir }
    if (Test-Path -LiteralPath 'M:\') {
        return 'M:\MiOS\build'
    }
    return Join-Path $env:USERPROFILE 'MiOS-Build'
}

# -- Surface handlers ------------------------------------------------------
function Export-WslTar([string]$ImageRef, [string]$OutDir) {
    Write-Step "Surface: WSL2 rootfs export (direct container storage stream -> uncompressed .tar)"
    $tar = Join-Path $OutDir 'mios.wsl.tar'

    if (Test-Path -LiteralPath $tar) {
        Write-Warn "mios.wsl.tar already exists at $tar -- skipping (delete to rebuild)"
        Write-Host ("    Try it:  wsl --import MiOS `"$env:USERPROFILE\MiOS-VM`" `"$tar`"") -ForegroundColor DarkGray
        return
    }

    # Ensure podman is available
    if (-not (Test-CommandExists 'podman')) {
        throw "podman is required for direct rootfs streaming export. Ensure Podman Desktop / podman CLI is installed."
    }

    # Pull image into container storage if not already present
    Write-Step "Checking container image $ImageRef in local container storage..."
    & podman image exists $ImageRef 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Step "Pulling $ImageRef into container storage..."
        & podman pull $ImageRef
        if ($LASTEXITCODE -ne 0) {
            throw "podman pull $ImageRef failed with exit code $LASTEXITCODE"
        }
    }

    # Create transient container snapshot without entrypoint arguments (entrypoint command override removed to avoid conflicts)
    Write-Step "Creating transient container snapshot of $ImageRef..."
    $contLines = (& podman create $ImageRef 2>&1)
    $contId = ($contLines | Where-Object { $_ -match '^[0-9a-f]{12,64}$' } | Select-Object -Last 1)
    if ([string]::IsNullOrWhiteSpace($contId)) {
        $contId = ($contLines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1)
    }
    if ([string]::IsNullOrWhiteSpace($contId) -or $contId -match 'error' -or $LASTEXITCODE -ne 0) {
        $createErr = ($contLines -join "`n").Trim()
        throw "podman create failed for ${ImageRef}: $createErr"
    }
    $contId = $contId.Trim()
    Write-Ok "Transient export container: $contId"

    $proc = $null
    $stderrTask = $null
    try {
        Write-Step "Streaming rootfs from container storage -> $(Split-Path $tar -Leaf)..."
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName               = "podman"
        $psi.Arguments              = "export $contId"
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError  = $true
        $psi.UseShellExecute        = $false
        $psi.CreateNoWindow         = $true

        $proc = [System.Diagnostics.Process]::Start($psi)
        if (-not $proc) {
            throw "Failed to start podman export process"
        }

        # Asynchronously capture standard error to prevent OS pipe buffer deadlock
        $stderrTask = $proc.StandardError.ReadToEndAsync()

        $fs = [System.IO.File]::Create($tar)
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $buf    = New-Object byte[] 65536
            $stream = $proc.StandardOutput.BaseStream
            while ($true) {
                $n = $stream.Read($buf, 0, $buf.Length)
                if ($n -le 0) { break }
                $fs.Write($buf, 0, $n)
                if ($sw.ElapsedMilliseconds -ge 2000) {
                    $mb = [math]::Round($fs.Length / 1MB)
                    Write-Step "Exporting WSL2 tar... ${mb} MB"
                    $sw.Restart()
                }
            }
        } finally {
            $fs.Close()
        }

        $proc.WaitForExit()
        $exportStderr = if ($stderrTask) {
            try { $stderrTask.Result.Trim() } catch { "" }
        } else { "" }

        if ($proc.ExitCode -ne 0) {
            $exportErr = "podman export failed with exit code $($proc.ExitCode)"
            if ($exportStderr) { $exportErr += ": $exportStderr" }
            throw $exportErr
        }

        if (-not (Test-Path -LiteralPath $tar) -or (Get-Item -LiteralPath $tar).Length -eq 0) {
            throw "podman export produced an empty or missing archive at $tar"
        }

        $sizeMB = [math]::Round((Get-Item $tar).Length / 1MB, 1)
        Write-Ok "WSL2 import-ready (uncompressed tar, ${sizeMB} MB): $tar"
        Write-Host ("    Try it:  wsl --import MiOS `"$env:USERPROFILE\MiOS-VM`" `"$tar`"") -ForegroundColor DarkGray
    } catch {
        # Clean up partial output on failure to avoid corrupted archives
        if (Test-Path -LiteralPath $tar) {
            try { Remove-Item -LiteralPath $tar -Force -ErrorAction SilentlyContinue } catch {}
        }
        throw
    } finally {
        if ($proc) {
            try {
                if (-not $proc.HasExited) {
                    $proc.Kill()
                }
            } catch {}
            try { $proc.Dispose() } catch {}
        }
        if ($contId) {
            try { & podman rm -f $contId 2>$null | Out-Null } catch {}
        }
    }
}

# DEPRECATED: wsl --import does NOT support .tar.zst archives and fails with error 0x80070057 (E_INVALIDARG).
# WSL2 requires either a standard uncompressed .tar rootfs or a native .vhdx disk (via --vhd).
# DEPRECATED: .tar.zst compression is incompatible with 'wsl --import' (causes error 0x80070057). Target uncompressed mios.wsl.tar directly.

function Convert-ToVhdx([string]$OutDir) {
    Write-Step "Surface: vhdx  (qemu-img convert -O vhdx,subformat=dynamic)"
    $okQemu = Install-WingetTool -WingetId 'qemu.qemu' -BinaryName 'qemu-img.exe'
    if (-not $okQemu) {
        Write-Bad 'qemu-img.exe unavailable; install qemu manually or use mios-cloud-build.ps1.'
        return
    }
    # Source preference: qcow2 first (smaller / faster), raw fallback.
    $candidates = @(
        @{ Path = Join-Path $OutDir 'mios.qcow2'; Format = 'qcow2' },
        @{ Path = Join-Path $OutDir 'disk.raw';   Format = 'raw'   }
    )
    $src = $candidates | Where-Object { Test-Path -LiteralPath $_.Path } | Select-Object -First 1
    if (-not $src) {
        Write-Bad "No source disk image found in $OutDir."
        Write-Warn "vhdx needs a qcow2 or raw. Run mios-cloud-build.ps1 -Targets qcow2 first, or download one."
        return
    }
    $out = Join-Path $OutDir 'mios.vhdx'
    if (Test-Path -LiteralPath $out) {
        Write-Warn "mios.vhdx already exists -- skipping"
        return
    }
    Write-Step "qemu-img convert -O vhdx -o subformat=dynamic $($src.Path) -> $out"
    & qemu-img.exe convert -p -f $src.Format -O vhdx -o 'subformat=dynamic' $src.Path $out
    if ($LASTEXITCODE -ne 0) {
        Write-Bad "qemu-img convert exited $LASTEXITCODE"
        return
    }
    Write-Ok "Built: $out"
    Write-Host ("    Try it in WSL:  wsl --import MiOS `"$env:USERPROFILE\MiOS-VM`" `"$out`" --vhd") -ForegroundColor DarkGray
}

function New-HyperVScaffold([string]$OutDir, [string]$VmName) {
    Write-Step "Surface: Hyper-V scaffold script"
    $vhdx = Join-Path $OutDir 'mios.vhdx'
    if (-not (Test-Path -LiteralPath $vhdx)) {
        Write-Warn "Hyper-V scaffold needs mios.vhdx. Run with -Targets vhdx first."
        return
    }
    $script = Join-Path $OutDir 'mios-hyperv-create.ps1'
    # The scaffold needs admin (Hyper-V cmdlets gate on RunAsAdmin), so we
    # generate it for the operator to review + launch elevated themselves
    # rather than auto-elevating from here. Operators get to see the New-VM
    # parameters before committing.
    $body = @"
#Requires -Version 7.0
#Requires -RunAsAdministrator
# Generated by mios-windows-export.ps1
# Creates a Generation-2 Hyper-V VM attached to the converted MiOS vhdx.
`$VmName  = '$VmName'
`$VhdPath = '$vhdx'
`$Switch  = 'Default Switch'   # rename if your install uses a custom switch
New-VM -Name `$VmName -Generation 2 -MemoryStartupBytes 8GB -VHDPath `$VhdPath -SwitchName `$Switch
Set-VMProcessor   -VMName `$VmName -Count 4
Set-VMMemory      -VMName `$VmName -DynamicMemoryEnabled `$true -MinimumBytes 2GB -MaximumBytes 16GB
Set-VMFirmware    -VMName `$VmName -EnableSecureBoot Off
Add-VMDvdDrive    -VMName `$VmName
Write-Host 'VM ready -- start with: Start-VM -Name $VmName' -ForegroundColor Green
"@
    Set-Content -Path $script -Value $body -Encoding UTF8
    Write-Ok "Hyper-V scaffold: $script"
    Write-Host "    Open an elevated PowerShell + run: pwsh -File `"$script`"" -ForegroundColor DarkGray
}

# -- Main ------------------------------------------------------------------
Write-Step "MiOS Windows-side export  --  image=$Image"
$ref = Resolve-ImageRef $Image
Write-Ok ("Registry={0}  Repo={1}  Ref={2}" -f $ref.Registry, $ref.Repo, $ref.Ref)

if (-not $Tag) { $Tag = $ref.Ref -replace '[:@/]','_' }
$outBase = Resolve-OutputBase
$outDir  = Join-Path $outBase $Tag
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Write-Ok "Output dir: $outDir"


foreach ($t in $Targets) {
    switch ($t.ToLower()) {
        'wsl'    { Export-WslTar          -ImageRef $Image -OutDir $outDir }
        'vhdx'   { Convert-ToVhdx         -OutDir $outDir }
        'hyperv' { New-HyperVScaffold     -OutDir $outDir -VmName $HyperVName }
        { $_ -in 'qcow2','raw','iso' } {
            Write-Warn "Target '$t' needs a Linux container backend (BIB). Use:"
            Write-Host "    .\mios-cloud-build.ps1 -Targets $t" -ForegroundColor DarkGray
        }
        default  { Write-Warn "Unknown target: $t (skipping)" }
    }
}

# -- Summary ---------------------------------------------------------------
Write-Step "Build summary"
$rows = foreach ($f in Get-ChildItem -Path $outDir -File -ErrorAction SilentlyContinue) {
    [pscustomobject]@{
        Artifact = $f.Name
        Size_MB  = '{0:N1}' -f ($f.Length / 1MB)
        Path     = $f.FullName
    }
}
if ($rows) {
    $rows | Format-Table -AutoSize
} else {
    Write-Warn "No artifacts produced under $outDir"
}

Write-Step "Done"
Write-Ok "Output: $outDir"
