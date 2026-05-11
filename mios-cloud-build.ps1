#Requires -Version 7.0
<#
.SYNOPSIS
    Pull the MiOS OCI image from GHCR and convert it to every deployable target.

.DESCRIPTION
    Reverse of `mios build`. Where `mios build` runs INSIDE the dev VM and
    produces artifacts from a local Containerfile, this script pulls the
    pre-built image that mios.git's CI/CD pipeline pushed to
    ghcr.io/mios-dev/mios:<tag> and runs bootc-image-builder (BIB) against
    it from the Windows host to produce:

        qcow2  - QEMU / KVM / libvirt (mios.qcow2)
        raw    - bare-metal flash (USB / dd / writable to disk)
        vhdx   - Hyper-V (derived from raw via qemu-img convert)
        wsl    - WSL2 tarball (podman export + zstd, NOT BIB; BIB has no
                 WSL target type)
        iso    - anaconda installer ISO (bootable, kickstart-driven)

    Every conversion runs inside `podman-MiOS-DEV` via `podman run`
    (the dev VM ships qemu-img, bootc-image-builder, and the WSL export
    pipeline). The script never assumes Windows-side tooling beyond podman
    + WSL.

.PARAMETER Image
    OCI reference to pull + convert. Default: ghcr.io/mios-dev/mios:latest

.PARAMETER OutputDir
    Where artifacts land on the Windows host. Defaults to M:\MiOS\build\<tag>
    when M: is the MiOS data disk, falls back to %USERPROFILE%\MiOS-Build
    otherwise. The dev VM mounts this via /mnt/m or /mnt/c automatically.

.PARAMETER Targets
    Subset of qcow2 / raw / vhdx / wsl / iso to produce. Default = all 5.

.PARAMETER Tag
    Subdirectory label under OutputDir. Defaults to the image's :tag.

.PARAMETER Machine
    podman machine name that hosts the BIB container. Defaults to
    podman-MiOS-DEV (the MiOS canonical dev VM).

.PARAMETER SkipPull
    Skip the `podman pull` step (use the image already on disk).

.PARAMETER BibImage
    Override the bootc-image-builder image. Default:
    quay.io/centos-bootc/bootc-image-builder:latest

.EXAMPLE
    .\mios-cloud-build.ps1
    Pulls ghcr.io/mios-dev/mios:latest and emits all 5 artifact formats to
    M:\MiOS\build\latest\.

.EXAMPLE
    .\mios-cloud-build.ps1 -Targets wsl,qcow2 -Tag '0.2.4'
    Only WSL tarball + qcow2 from ghcr.io/mios-dev/mios:0.2.4 into
    M:\MiOS\build\0.2.4\.

.NOTES
    Architectural Law context: ".git IS /" (per
    feedback_mios_no_c_drive_fallback). C:\MiOS is the operator dev clone
    of mios.git; this script lives at C:\MiOS\mios-cloud-build.ps1 -- the
    repo root -- so it ships alongside the OCI Containerfile + automation/
    that produced the GHCR image in the first place. Closes the deploy
    loop: any operator clones mios.git, runs this script, and has every
    target artifact without spinning up the full `mios build` pipeline.
#>

[CmdletBinding()]
param(
    [string]   $Image      = 'ghcr.io/mios-dev/mios:latest',
    [string]   $OutputDir  = '',
    [string[]] $Targets    = @('qcow2','raw','vhdx','wsl','iso'),
    [string]   $Tag        = '',
    [string]   $Machine    = 'podman-MiOS-DEV',
    [switch]   $SkipPull,
    [string]   $BibImage   = 'quay.io/centos-bootc/bootc-image-builder:latest'
)

$ErrorActionPreference = 'Stop'

# ── Helpers ───────────────────────────────────────────────────────────────
function Write-Step([string]$Msg) {
    Write-Host ('▶ ' + $Msg) -ForegroundColor Cyan
}
function Write-Ok([string]$Msg) {
    Write-Host ('  [+] ' + $Msg) -ForegroundColor Green
}
function Write-Warn([string]$Msg) {
    Write-Host ('  [!] ' + $Msg) -ForegroundColor Yellow
}
function Write-Bad([string]$Msg) {
    Write-Host ('  [X] ' + $Msg) -ForegroundColor Red
}

# Convert Windows path -> WSL mount path so podman run -v can use it
# regardless of which drive M: lives on. Windows C:\foo\bar becomes
# /mnt/c/foo/bar inside any WSL distro the operator has registered.
function ConvertTo-WslPath([string]$WinPath) {
    if (-not $WinPath) { return '' }
    $drive = $WinPath.Substring(0,1).ToLower()
    $rest  = $WinPath.Substring(2) -replace '\\','/'
    return "/mnt/$drive$rest"
}

# Resolve the output base. Prefer M:\ (the MiOS data disk) when present,
# fall back to %USERPROFILE%\MiOS-Build for operators that haven't run
# Initialize-DataDisk yet. The dev VM mounts both transparently.
function Resolve-OutputBase {
    if ($script:OutputDir) { return $script:OutputDir }
    if (Test-Path -LiteralPath 'M:\') {
        return 'M:\MiOS\build'
    }
    return Join-Path $env:USERPROFILE 'MiOS-Build'
}

# Run a podman command bound to the named machine. Routes through
# wsl.exe -d podman-MiOS-DEV so the build runs INSIDE the dev VM (where
# BIB has the kernel/loop-device privileges it needs); the Windows-side
# podman.exe with the right --connection would also work but adds another
# moving piece per-machine.
function Invoke-Podman([string[]]$ArgsList, [string]$Description = '') {
    if ($Description) { Write-Step $Description }
    Write-Host ('  $ podman ' + ($ArgsList -join ' ')) -ForegroundColor DarkGray
    & wsl.exe -d $Machine --user root -- podman @ArgsList
    if ($LASTEXITCODE -ne 0) {
        throw "podman $($ArgsList -join ' ') exited $LASTEXITCODE"
    }
}

# Same but capture stdout to a variable instead of streaming to console.
function Invoke-PodmanCapture([string[]]$ArgsList) {
    $out = & wsl.exe -d $Machine --user root -- podman @ArgsList 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "podman $($ArgsList -join ' ') exited $LASTEXITCODE`n$out"
    }
    return $out
}

# ── Pre-flight ────────────────────────────────────────────────────────────
Write-Step "MiOS cloud build  --  image=$Image"

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Bad 'wsl.exe not on PATH. Install WSL2 from the Microsoft Store.'
    exit 1
}

# Verify dev VM is registered + responsive.
$distros = (& wsl.exe -l -q 2>$null) -split "`r?`n" |
    ForEach-Object { ($_ -replace [char]0,'').Trim() } |
    Where-Object { $_ }
if ($distros -notcontains $Machine) {
    Write-Bad "WSL distro '$Machine' is not registered."
    Write-Bad "Run the MiOS irm|iex bootstrap first so $Machine gets provisioned."
    exit 1
}
Write-Ok "WSL distro $Machine is registered"

# Confirm podman responds inside the VM.
& wsl.exe -d $Machine --user root -- podman version --format '{{.Client.Version}}' 2>$null |
    Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Bad "podman inside $Machine isn't responding."
    exit 1
}
Write-Ok 'podman is responsive inside the dev VM'

# Resolve tag if the operator didn't pass -Tag.
if (-not $Tag) {
    if ($Image -match ':([^:/@]+)$') {
        $Tag = $Matches[1]
    } else {
        $Tag = 'latest'
    }
}
$outBase = Resolve-OutputBase
$outDir  = Join-Path $outBase $Tag
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Write-Ok "Output dir: $outDir"
$outWsl = ConvertTo-WslPath $outDir

# ── Pull ───────────────────────────────────────────────────────────────────
if (-not $SkipPull) {
    Invoke-Podman -ArgsList @('pull', $Image) -Description "pull $Image"
    Write-Ok "Image present: $Image"
} else {
    Write-Warn "Skipping pull (--SkipPull)"
}

# Inspect digest + size so the operator can verify what they got from GHCR.
try {
    $digest = (Invoke-PodmanCapture -ArgsList @('image','inspect','--format','{{.Digest}}', $Image)).Trim()
    $size   = (Invoke-PodmanCapture -ArgsList @('image','inspect','--format','{{.Size}}',   $Image)).Trim()
    Write-Ok ("Digest: {0}" -f $digest)
    Write-Ok ("Size:   {0:N0} bytes ({1:N1} GiB)" -f [int64]$size, ([int64]$size / 1GB))
} catch {
    Write-Warn "Image inspect failed: $($_.Exception.Message)"
}

# ── BIB runner ────────────────────────────────────────────────────────────
# BIB needs --privileged + a loop device, plus the OCI image to convert AND
# its own image. Mount the output dir read-write so the qcow2/raw/iso
# land on the host. --tls-verify=false on Image= push isn't relevant
# here since BIB just reads the local podman storage.
function Invoke-BibTarget([string]$BibType, [string]$OutFileName) {
    $outPath = Join-Path $outDir $OutFileName
    if (Test-Path -LiteralPath $outPath) {
        Write-Warn "$OutFileName already exists at $outPath -- skipping ($BibType)"
        return
    }
    Write-Step "BIB build: $BibType -> $OutFileName"
    $bibArgs = @(
        'run','--rm','--privileged',
        '--security-opt','label=type:unconfined_t',
        '--pull=newer',
        '-v', ("{0}:/output:Z" -f $outWsl),
        '-v','/var/lib/containers/storage:/var/lib/containers/storage',
        $BibImage,
        '--type', $BibType,
        '--rootfs', 'btrfs',
        '--output','/output',
        $Image
    )
    try {
        Invoke-Podman -ArgsList $bibArgs -Description "bootc-image-builder $BibType"
        Write-Ok "Built: $outPath"
    } catch {
        Write-Bad "BIB $BibType failed: $($_.Exception.Message)"
    }
}

# WSL2 tar: BIB has no WSL target type. Do it directly: `podman create`
# a stopped container, `podman export` its rootfs to a tar, compress with
# zstd. The dev VM has zstd in coreutils-extra; falls back to gzip if
# not available.
function Invoke-WslExport {
    $outPath = Join-Path $outDir 'mios.wsl.tar.zst'
    if (Test-Path -LiteralPath $outPath) {
        Write-Warn "mios.wsl.tar.zst already exists -- skipping (wsl)"
        return
    }
    Write-Step "WSL2 tar: podman export + zstd"
    $tmpName = "mios-cloud-export-$([guid]::NewGuid().ToString('N').Substring(0,8))"
    try {
        # The exported tar is the rootfs of the IMAGE -- no container needed
        # for runtime, just for `podman export`. --pull=never assumes the
        # image is already local (we pulled above).
        Invoke-Podman -ArgsList @('create','--name',$tmpName,$Image,'/bin/true') -Description "stage rootfs"
        $tarWsl = "$outWsl/mios.wsl.tar"
        Invoke-Podman -ArgsList @('export','-o',$tarWsl,$tmpName) -Description "export rootfs"
        # zstd -19 trades CPU for a smaller tarball; WSL imports don't care
        # which compressor was used. The bootstrap-installed machine-os
        # tarball uses zstd so we match the convention.
        $zstdScript = "if command -v zstd >/dev/null 2>&1; then zstd -19 --rm -f '$tarWsl' -o '$tarWsl.zst'; else gzip -9 '$tarWsl'; fi"
        & wsl.exe -d $Machine --user root -- bash -c $zstdScript
        if ($LASTEXITCODE -ne 0) {
            throw "zstd / gzip compression of $tarWsl failed (rc=$LASTEXITCODE)"
        }
        Write-Ok "Built: $outPath"
    } catch {
        Write-Bad "WSL export failed: $($_.Exception.Message)"
    } finally {
        # Clean up the staging container regardless of success.
        & wsl.exe -d $Machine --user root -- podman rm -f $tmpName *>$null
    }
}

# VHDX: derive from raw via qemu-img convert. BIB's vmdk type targets
# VMware; Hyper-V wants vhdx specifically. The dev VM has qemu-img from
# [packages.virt] (mios.toml).
function Invoke-VhdxConvert {
    $rawPath = Join-Path $outDir 'disk.raw'
    $vhdPath = Join-Path $outDir 'mios.vhdx'
    if (Test-Path -LiteralPath $vhdPath) {
        Write-Warn "mios.vhdx already exists -- skipping"
        return
    }
    if (-not (Test-Path -LiteralPath $rawPath)) {
        Write-Warn "vhdx requires the raw target. Re-run with -Targets raw,vhdx (or all)."
        return
    }
    Write-Step "VHDX: qemu-img convert raw -> vhdx (dynamic)"
    $cmd = "qemu-img convert -p -O vhdx -o subformat=dynamic '$outWsl/disk.raw' '$outWsl/mios.vhdx'"
    & wsl.exe -d $Machine --user root -- bash -c $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Bad "qemu-img convert exited $LASTEXITCODE"
        return
    }
    Write-Ok "Built: $vhdPath"
}

# ── Drive each requested target ───────────────────────────────────────────
# Order matters: vhdx depends on raw, so process raw first when both are
# requested. The order below is the natural BIB precedence: lighter
# artifacts first, ISO last (it's the slowest to produce).
$orderedTargets = @()
foreach ($t in @('qcow2','raw','vhdx','wsl','iso')) {
    if ($Targets -contains $t) { $orderedTargets += $t }
}

foreach ($target in $orderedTargets) {
    switch ($target) {
        'qcow2' { Invoke-BibTarget -BibType 'qcow2'         -OutFileName 'mios.qcow2' }
        'raw'   { Invoke-BibTarget -BibType 'raw'           -OutFileName 'disk.raw'   }
        'iso'   { Invoke-BibTarget -BibType 'anaconda-iso'  -OutFileName 'install.iso' }
        'wsl'   { Invoke-WslExport }
        'vhdx'  { Invoke-VhdxConvert }
        default { Write-Warn "Unknown target: $target (skipping)" }
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
Write-Ok "Artifacts: $outDir"
Write-Ok "Next steps:"
Write-Host "    qcow2  -> virt-install / virsh / Boxes / virt-manager" -ForegroundColor DarkGray
Write-Host "    raw    -> dd to USB:  dd if=disk.raw of=/dev/sdX bs=4M status=progress" -ForegroundColor DarkGray
Write-Host "    vhdx   -> Hyper-V Manager: New VM -> Attach existing disk -> mios.vhdx" -ForegroundColor DarkGray
Write-Host "    wsl    -> wsl --import MiOS C:\MiOS-VM `"$outDir\mios.wsl.tar.zst`"" -ForegroundColor DarkGray
Write-Host "    iso    -> Burn / mount in Hyper-V / qemu -cdrom for fresh install" -ForegroundColor DarkGray
