#Requires -Version 7.0
<#
.SYNOPSIS
    Windows-native MiOS OCI exporter / converter -- no podman machine required.

.DESCRIPTION
    Complement to mios-cloud-build.ps1 (which routes every conversion
    through podman-MiOS-DEV). This script does as much as it can WITHOUT
    a Linux container backend, using only Windows-native tooling:

      WSL2 tarball  -  Pull the OCI image's rootfs layers straight from
                       GHCR's registry API + reassemble into a single
                       .tar via tar.exe (Windows 10+ bundled) + compress
                       with zstd.exe (auto-installed via winget if
                       missing). NO podman / WSL distro required.

      VHDX          -  Convert an existing qcow2 / raw / vmdk to vhdx via
                       qemu-img.exe (Windows port, auto-installed via
                       winget from `qemu.qemu`).

      Hyper-V VM    -  Generate a sample New-VM script that attaches the
                       produced VHDX (does NOT auto-import; operator
                       reviews + runs as admin).

    Formats that genuinely require Linux tooling (raw / qcow2 / iso
    from a fresh OCI image, anaconda-installer iso, etc.) fall through
    to mios-cloud-build.ps1 with a clear pointer; this script does NOT
    silently spin up a podman machine on the operator's behalf.

.PARAMETER Image
    OCI reference to pull. Default: ghcr.io/mios-dev/mios:latest

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
    Pulls the rootfs of ghcr.io/mios-dev/mios:latest from GHCR and emits
    mios.wsl.tar.zst under M:\MiOS\build\latest\. Zero Linux tools used.

.EXAMPLE
    .\mios-windows-export.ps1 -Targets wsl,vhdx
    Builds the WSL tarball AND -- if a qcow2 or raw is already in the
    output dir (e.g. produced earlier by mios-cloud-build.ps1) -- converts
    it to mios.vhdx via Windows-native qemu-img.exe.

.NOTES
    Why pure-Windows matters: an operator on a fresh Windows install can
    clone mios.git + run this script + get a working `wsl --import`-ready
    tarball with zero prerequisites beyond winget. The dev VM is for
    BUILDING MiOS; this script is for CONSUMING the GHCR-published
    artifact when the operator only wants to USE MiOS, not contribute to
    it.

    OCI rootfs assembly logic mirrors `podman export`: concatenate every
    image layer's tar contents (gzip-decoded), preserve whiteout marks
    (.wh.*) for deletions, drop OCI metadata (manifest.json, *.json).
    Equivalent to: `podman create X && podman export ID -o tar` but
    entirely off Windows native HTTP + tar.

    No anonymous GitHub token is needed for public images on GHCR --
    `ghcr.io/mios-dev/mios` is publicly readable, the script fetches a
    short-lived bearer from ghcr.io/token automatically.
#>

[CmdletBinding()]
param(
    [string]   $Image      = 'ghcr.io/mios-dev/mios:latest',
    [string]   $OutputDir  = '',
    [string]   $Tag        = '',
    [string[]] $Targets    = @('wsl'),
    [string]   $HyperVName = 'MiOS-Auto'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'   # 10-20x speedup for IWR

# ── Console helpers ───────────────────────────────────────────────────────
function Write-Step([string]$m) { Write-Host ("▶ "    + $m) -ForegroundColor Cyan  }
function Write-Ok  ([string]$m) { Write-Host ("  [+] " + $m) -ForegroundColor Green }
function Write-Warn([string]$m) { Write-Host ("  [!] " + $m) -ForegroundColor Yellow }
function Write-Bad ([string]$m) { Write-Host ("  [X] " + $m) -ForegroundColor Red   }

# ── winget helper -- auto-install qemu + zstd if missing ─────────────────
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

# ── OCI registry helpers (GHCR public-image protocol) ────────────────────
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

function Get-ImageManifest([hashtable]$Ref, [string]$Token) {
    # Request the FAT manifest first so multi-arch images are unambiguous.
    $headers = @{
        'Authorization' = "Bearer $Token"
        'Accept'        = 'application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'
    }
    $url = "https://$($Ref.Registry)/v2/$($Ref.Repo)/manifests/$($Ref.Ref)"
    $resp = Invoke-RestMethod -Uri $url -Headers $headers -ErrorAction Stop
    # If it's a list/index, pick amd64+linux. MiOS only ships x86_64 for now.
    if ($resp.manifests) {
        $picked = $resp.manifests | Where-Object {
            $_.platform.architecture -eq 'amd64' -and $_.platform.os -eq 'linux'
        } | Select-Object -First 1
        if (-not $picked) {
            throw "No linux/amd64 manifest in the index for $($Ref.Repo):$($Ref.Ref)"
        }
        Write-Ok "Manifest index resolved -> $($picked.digest) (linux/amd64)"
        $headers['Accept'] = 'application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'
        $url = "https://$($Ref.Registry)/v2/$($Ref.Repo)/manifests/$($picked.digest)"
        $resp = Invoke-RestMethod -Uri $url -Headers $headers -ErrorAction Stop
    }
    return $resp
}

# Pull every layer blob into a flat dir on disk. GHCR layers are gzipped
# tarballs (mediaType application/vnd.oci.image.layer.v1.tar+gzip).
function Save-ImageLayers([hashtable]$Ref, [string]$Token, [object]$Manifest, [string]$Dest) {
    if (-not (Test-Path -LiteralPath $Dest)) {
        New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    }
    $headers = @{ 'Authorization' = "Bearer $Token" }
    $layerFiles = @()
    foreach ($layer in $Manifest.layers) {
        $digest = $layer.digest        # sha256:<hex>
        $url    = "https://$($Ref.Registry)/v2/$($Ref.Repo)/blobs/$digest"
        $sha    = $digest -replace '^sha256:',''
        $out    = Join-Path $Dest ("layer-{0}.tar.gz" -f $sha.Substring(0,12))
        if (Test-Path -LiteralPath $out) {
            Write-Ok "Layer cached: $($out | Split-Path -Leaf) ($($layer.size) bytes)"
        } else {
            Write-Step "Pull layer $($sha.Substring(0,12)) ($([Math]::Round($layer.size/1MB,1)) MiB)"
            Invoke-WebRequest -Uri $url -Headers $headers -OutFile $out -ErrorAction Stop
        }
        $layerFiles += $out
    }
    return $layerFiles
}

# Stitch every layer into one flat tarball, preserving OCI whiteout
# semantics (a `.wh.foo` file means "delete foo" in the running rootfs).
# `tar.exe` (Win10+ bundled) handles gzip directly via `-xzf`. We extract
# every layer in order into a staging dir, then re-tar that dir.
function Merge-LayersToTar([string[]]$LayerFiles, [string]$StagingDir, [string]$OutTar) {
    if (-not (Test-CommandExists 'tar.exe')) {
        throw "tar.exe not found. Win10 1803+ ships it bundled at %SystemRoot%\System32\tar.exe; check your PATH."
    }
    if (Test-Path -LiteralPath $StagingDir) {
        Remove-Item -LiteralPath $StagingDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

    foreach ($layer in $LayerFiles) {
        Write-Step "Extract $((Split-Path $layer -Leaf))"
        # --force-local: tar.exe interprets `C:` as a remote host otherwise.
        & tar.exe --force-local -xzf $layer -C $StagingDir 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "tar -xzf $layer failed (rc=$LASTEXITCODE)"
        }
        # Whiteout handling: .wh.<name> files mean "delete <name>"; .wh..wh..opq
        # means "delete every sibling". The OCI spec leaves processing to the
        # extractor. For WSL2 the simplest correct interpretation is to honor
        # whiteouts in-line so the final tar contains the right set.
        Get-ChildItem -LiteralPath $StagingDir -Recurse -Filter '.wh.*' -Force -ErrorAction SilentlyContinue |
            ForEach-Object {
                $parent = $_.Directory.FullName
                $name   = $_.Name
                if ($name -eq '.wh..wh..opq') {
                    # Opaque directory marker -- siblings get wiped.
                    Get-ChildItem -LiteralPath $parent -Force -ErrorAction SilentlyContinue |
                        Where-Object { $_.Name -ne '.wh..wh..opq' } |
                        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
                } else {
                    $target = Join-Path $parent ($name.Substring(4))   # strip '.wh.'
                    if (Test-Path -LiteralPath $target) {
                        Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
                    }
                }
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
            }
    }

    Write-Step "Pack rootfs -> $(Split-Path $OutTar -Leaf)"
    # Push-Location so tar.exe sees relative paths. Without this it stores
    # an absolute Windows path and `wsl --import` chokes parsing it.
    Push-Location -LiteralPath $StagingDir
    try {
        & tar.exe --force-local -cf $OutTar . 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "tar -cf $OutTar failed (rc=$LASTEXITCODE)"
        }
    } finally {
        Pop-Location
    }
}

# Compress to .zst. zstd Windows binary from `Facebook.zstd` (winget).
# Falls through to keeping the plain .tar if zstd isn't available --
# `wsl --import` accepts uncompressed too.
function Compress-WithZstd([string]$InTar, [string]$OutZst, [int]$Level = 19) {
    if (Test-CommandExists 'zstd.exe') {
        Write-Step "zstd -$Level $InTar"
        & zstd.exe "-$Level" -f --rm -o $OutZst $InTar 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "zstd compression failed (rc=$LASTEXITCODE)"
        }
        Write-Ok "Wrote $OutZst"
    } else {
        Write-Warn 'zstd.exe not found; leaving uncompressed .tar (wsl --import accepts either)'
    }
}

# ── Output directory resolver ─────────────────────────────────────────────
function Resolve-OutputBase {
    if ($script:OutputDir) { return $script:OutputDir }
    if (Test-Path -LiteralPath 'M:\') {
        return 'M:\MiOS\build'
    }
    return Join-Path $env:USERPROFILE 'MiOS-Build'
}

# ── Surface handlers ──────────────────────────────────────────────────────
function Export-WslTar([hashtable]$Ref, [string]$Token, [string]$OutDir) {
    Write-Step "Surface: wsl2 tarball  (pure Windows: HTTP + tar.exe + zstd.exe)"
    $manifest = Get-ImageManifest $Ref $Token
    $layerCache = Join-Path $OutDir '.layers'
    $layers = Save-ImageLayers $Ref $Token $manifest $layerCache
    $staging = Join-Path $OutDir '.rootfs-stage'
    $tar     = Join-Path $OutDir 'mios.wsl.tar'
    $zst     = Join-Path $OutDir 'mios.wsl.tar.zst'

    if (Test-Path -LiteralPath $zst) {
        Write-Warn "mios.wsl.tar.zst already exists -- skipping (delete to rebuild)"
        return
    }

    Merge-LayersToTar -LayerFiles $layers -StagingDir $staging -OutTar $tar
    Compress-WithZstd -InTar $tar -OutZst $zst -Level 19

    # Clean the staging tree -- the operator only cares about the final
    # tarball, not the 1-3 GB of intermediate extracted files.
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    Write-Ok "WSL2 import-ready: $zst"
    Write-Host ("    Try it:  wsl --import MiOS $env:USERPROFILE\MiOS-VM `"$zst`"") -ForegroundColor DarkGray
}

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

# ── Main ──────────────────────────────────────────────────────────────────
Write-Step "MiOS Windows-side export  --  image=$Image"
$ref = Resolve-ImageRef $Image
Write-Ok ("Registry={0}  Repo={1}  Ref={2}" -f $ref.Registry, $ref.Repo, $ref.Ref)

if (-not $Tag) { $Tag = $ref.Ref -replace '[:@/]','_' }
$outBase = Resolve-OutputBase
$outDir  = Join-Path $outBase $Tag
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Write-Ok "Output dir: $outDir"

# Anonymous bearer for the public-read pull. Even private repos that the
# operator has access to via gh auth would work if you swap this for a
# PAT-derived token -- left out of scope for the public-image use case.
$token = Get-GhcrToken -Repo $ref.Repo

foreach ($t in $Targets) {
    switch ($t.ToLower()) {
        'wsl'    { Export-WslTar          -Ref $ref -Token $token -OutDir $outDir }
        'vhdx'   { Convert-ToVhdx         -OutDir $outDir }
        'hyperv' { New-HyperVScaffold     -OutDir $outDir -VmName $HyperVName }
        { $_ -in 'qcow2','raw','iso' } {
            Write-Warn "Target '$t' needs a Linux container backend (BIB). Use:"
            Write-Host "    .\mios-cloud-build.ps1 -Targets $t" -ForegroundColor DarkGray
        }
        default  { Write-Warn "Unknown target: $t (skipping)" }
    }
}

# ── Summary ───────────────────────────────────────────────────────────────
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
