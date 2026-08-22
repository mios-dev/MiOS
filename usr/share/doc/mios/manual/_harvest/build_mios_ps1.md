<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: PowerShell entry point for MiOS installation that configures the MiOS-DEV podman-machine, handles initial licensing, and manages the SSH handoff to the Linux-side build driver for generating OCI images and disk formats.
AI-related: 37-ollama-prep.sh, mios-btop.sh, /usr/libexec/mios/mios-build-driver, /usr/share/mios/mios.toml, /usr/libexec/mios/mios-build-driver., /etc/mios/mios.toml, /usr/share/mios/configurator/mios.html, /usr/libexec/mios/flatpak-launch, /etc/mios/hermes/config.yaml, /etc/mios/hermes/config.local.yaml
AI-functions: parse_sections_from_toml, get_pkgs, install_section, parse_pkgs, Disable-ConsoleQuickEdit, Resolve-MiosTomlText, Get-MiosTomlValue, Resolve-MiosInstallRoot, Update-MiosInstallPaths, Invoke-MigrateLegacyInstallRoot, Invoke-DataDiskBootstrap, Test-DashboardCanRedraw
Requires -Version 5.1
'MiOS' Unified Installer & Builder -- Windows 11 / PowerShell

  irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.ps1 | iex

Flags:
  -BuildOnly    Pull latest + build only (skip first-time setup)
  -Unattended   Accept all defaults, no prompts

── ARCHITECTURE: Day-0 self-replication contract ────────────────────────────
Per the MiOS self-replication architecture (project memory:
project_mios_self_replication_vision.md), the Windows side of the bootstrap
is STRICTLY an entry point with a narrow scope:

  1. Acknowledgements (AGREEMENTS.md / LICENSES.md)
  2. MiOS-DEV podman-machine setup (Phases 0-5 + 8 of this script)
  3. SSH handoff into MiOS-DEV

After step 3, EVERYTHING else runs INSIDE MiOS-DEV: local fetch + overlay,
identity prompts, and the FULL build pipeline producing every output
format MiOS targets (OCI bootc image, WSL2/g .tar/.vhdx, Hyper-V .vhdx,
QEMU qcow2, Live-CD/USB ISO, USB installer, RAW dd image). The build
dashboard renders on the MiOS-DEV tty inside the SSH-hosted Windows
Terminal -- it is NOT streamed back across the WSL/Windows boundary.

Show-PostBootstrapMenu's "Continue to build" choice IS the SSH handoff:
it spawns a new Windows Terminal tab running `wsl.exe -d MiOS-DEV` which
in turn invokes /usr/libexec/mios/mios-build-driver inside the dev distro.

Migration status : Phase 6+ legacy code (identity, OCI build,
disk image generation, Hyper-V VM deploy) still lives in this script as
the -FullBuild / -BuildOnly path. The new SSH-handoff flow runs alongside
it via the menu. Subsequent migration chunks move identity prompts and
the full output-format matrix into the Linux-side driver, then trim this
Windows-side tail entirely.

<!-- mios-src:0acbcca01ab2 from build-mios.ps1:1-38 -->

### BootstrapOnly / -BuildOnly / -FullBuild

-BootstrapOnly / -BuildOnly / -FullBuild: LEGACY FLAGS, KEPT FOR
CALL-SITE COMPATIBILITY ONLY. Per the self-replication contract
(project memory: project_mios_self_replication_vision.md), the
Windows side runs ONLY: ack -> MiOS-DEV podman-machine setup ->
SSH handoff. Phase 6+ (Identity / OCI build / WSL2 export /
Hyper-V deploy) MUST run inside MiOS-DEV via /usr/libexec/mios/
mios-build-driver, NOT on Windows.

These flags are now no-ops -- the script always behaves as if
-BootstrapOnly was the only mode. -FullBuild and -BuildOnly emit
a deprecation note and are otherwise ignored. Operators who want
the old in-Windows pipeline can revert to a pre-352aee3 build of
this script; nothing else honors them any more.

<!-- mios-src:26faab5f1dc1 from build-mios.ps1:5-17 -->

### Disable console QuickEdit mode up-front. With QuickEdit on...

Disable console QuickEdit mode up-front. With QuickEdit on (the Windows
default), the instant anyone clicks or selects text in the window the console
enters "mark" mode and BLOCKS the process on its next write until Enter/Esc is
pressed -- on a long elevated install this looks identical to a dead hang
(process idle, only a conhost child, VM perfectly healthy). The
stall right after "MiOS Quadlet overlay applied" was exactly this. Clearing
ENABLE_QUICK_EDIT_MODE (0x40) + setting ENABLE_EXTENDED_FLAGS (0x80) makes the
installer immune to accidental click-to-freeze. Best-effort; never fatal.

<!-- mios-src:18854c8749fd from build-mios.ps1:29-36 -->

### ── mios.toml layered-overlay reader (mirrors Get-MiOS.ps1's...

── mios.toml layered-overlay reader (mirrors Get-MiOS.ps1's helper) ─────────
mios.toml is THE global dotfile (per feedback_mios_toml_html_global_dotfile).
Every tunable -- terminal dims, retry delays, dev VM image tag, distro
names -- sources from the layered overlay. We inline the helper instead
of dot-sourcing because build-mios.ps1 must work both in-tree (clone) and
under irm|iex relaunch where the path to Get-MiOS.ps1 isn't guaranteed.

<!-- mios-src:0a6f4880c60c from build-mios.ps1:60-65 -->

### Read as UTF-8. PS 5.1's Get-Content default is the system...

Read as UTF-8. PS 5.1's Get-Content default is the
system ANSI codepage (cp1252 on en-US) which decoded
the UTF-8 PUA glyphs in [theme.prompt] as 3-char
mojibake (the U+E0B4 cap's bytes EE 82 B4 became
'î‚´'). The omp.json glyph substitution then took
'î' as the cap and wrote U+00EE into the deployed
theme, producing operator-reported "powerline seconds
are shifted to the next row" + 'î' instead of ''.

<!-- mios-src:256749306a9a from build-mios.ps1:77-84 -->

### Return without unary-comma -- callers do `@(Get-Mios...)`...

Return without unary-comma -- callers do `@(Get-Mios...)`
which collects pipeline-unrolled ints into an array.
With `,$coerced` the result was @(@(0,5,15,30)) -- a
1-element array, so $delays[0] was the array itself,
crashing Start-Sleep -Seconds with "cannot convert
System.Object[] to System.Double".

<!-- mios-src:d90a9eb585e6 from build-mios.ps1:142-147 -->

### String -- strip SURROUNDING TOML quotes only (no Trim...

String -- strip SURROUNDING TOML quotes only (no Trim multi-set,
which previously ate leading ' from values like "'MiOS' v0.2.4"
because Trim('"',"'") matches both chars on both ends). Unescape
backslash sequences for double-quoted strings per TOML 1.0.0.

<!-- mios-src:a24bff2256b8 from build-mios.ps1:154-157 -->

### Resolve canonical terminal dims ONCE at script-load so...

Resolve canonical terminal dims ONCE at script-load so every later
resize / wt --size / stty call uses the same values from mios.toml.

IMPORTANT: build-mios.ps1 runs DURING the bootstrap install. Use
[terminal.install] dims (vendor default 80x40 -- enough rows for
the dashboard + install logs to fit visibly without auto-scroll
eating the banner). [terminal] dims (80x20) are reserved for the
POST-INSTALL MiOS app spawn -- using them here would shrink the
install conhost mid-flight, which the operator reports as "windows
still shrink to 80x20 and are also off-center". The post-install
wt --size spawn uses script:MiosAppCols / script:MiosAppRows.
[terminal.install] dims (80x40 install conhost, taller for log
room).  Renamed to $script:MiosInst{Cols,Rows} to avoid colliding
with Initialize-MiosGlobals which loads $script:Mios{Cols,Rows}
from [terminal] (the app dims).  Operator: "I said Unified!!! ...
extracted to ONE function used by every".

<!-- mios-src:ed47787e30fd from build-mios.ps1:179-194 -->

### Initialize-MiosGlobals (defined further down, called once...

Initialize-MiosGlobals (defined further down, called once at
script load) writes $script:MiosCols / $script:MiosRows from
the [terminal] section.  Shadow with the install dims here so
any sizing-dependent code BEFORE Initialize-MiosGlobals fires
uses the install conhost dims; after that point the app dims
from Initialize-MiosGlobals take over.  $script:MiosScroll +
$script:MiosAppCols / $script:MiosAppRows are kept inline (not
overwritten by Initialize-MiosGlobals) for any legacy site that
referenced the App-prefixed names.

<!-- mios-src:e5e4b3750aaf from build-mios.ps1:197-205 -->

### ── Console resize: mios.toml [terminal] dims BEFORE any...

── Console resize: mios.toml [terminal] dims BEFORE any sizing-dependent state ─
$script:DW (~line 543) is computed from [Console]::WindowWidth at script-
load time and never re-read. If the parent window opened wider, the
dashboard frame draws at the wrong width and log lines bleed past it.
Resize NOW, before $DW is computed. Dims source from mios.toml [terminal]
(vendor default 80x20 portal feel).
Per feedback_mios_terminal_dimensions.md.

The order matters: SetWindowSize requires buffer >= window. If the
current buffer is smaller than the target cols, SetWindowSize fails.
If the current window is larger than the target cols, SetBufferSize
fails (buffer can't be smaller than current window). So we branch.

<!-- mios-src:cb218c343935 from build-mios.ps1:212-223 -->

### NOTE

NOTE: The bootstrap-conhost window-centering helper that lived here
was REMOVED in commit 82dda7e+ because AMSI heuristics flagged the
combination of console-window-handle retrieval + window-positioning
Win32 calls as malware. Window centering was purely cosmetic; install
runs identically without it. Operator can drag the window if needed.

<!-- mios-src:27fa2991253d from build-mios.ps1:246-250 -->

### ── Self-replication enforcement: Windows ALWAYS halts at...

── Self-replication enforcement: Windows ALWAYS halts at Phase 5 ────────────
Per the self-replication architecture, the Windows side has STRICT scope:
ack + MiOS-DEV podman-machine setup + SSH handoff. The legacy -FullBuild /
-BuildOnly flags that bypassed this and ran identity / OCI / disk-image
phases ON WINDOWS are deprecated AND IGNORED here. We force $BootstrapOnly
to $true unconditionally so every code path that gates "stop after
Windows phases" via `if ($BootstrapOnly)` keeps the bootstrap halted.
Operators who need the old behavior must revert to a pre-352aee3 build.

<!-- mios-src:5764b475fcd7 from build-mios.ps1:253-260 -->

### ── Install scope detection...

── Install scope detection ───────────────────────────────────────────────────
'MiOS' installs as a native Windows app. Two scopes:

  AllUsers  -- machine-wide install at C:\Program Files\MiOS\
               Add/Remove Programs in HKLM. Distros + images in
               C:\ProgramData\MiOS. Per-user logs/config still use
               %LOCALAPPDATA%\MiOS / %APPDATA%\MiOS so each Windows
               account on the box gets its own state.

  CurrentUser -- per-user install at %LOCALAPPDATA%\Programs\MiOS\
                 Add/Remove Programs in HKCU. Used as a fallback when
                 the operator declines UAC elevation, or when the
                 installer is invoked under a standard (non-admin)
                 account.

Detection: a process is "admin" if it holds the Administrators
built-in role. The 'irm | iex' one-liner from Get-MiOS.ps1 will refuse
to elevate itself (UAC cannot prompt mid-pipeline); operators are
expected to run from an elevated PowerShell when AllUsers is desired.

<!-- mios-src:1c9488443726 from build-mios.ps1:285-303 -->

### ── Paths & constants -- ALL sourced from mios.toml SSOT...

── Paths & constants -- ALL sourced from mios.toml SSOT ─────────────────────
Per operator: "toml is the SSOT for code too!!! no hardcoding ANYWHERE!!!".
Every value below resolves through Get-MiosTomlValue with a vendor-default
fallback. The configurator HTML (mios.html) exposes each key as an editable
field; an operator edit there flows mios.toml -> these values -> the entire
install pipeline.

<!-- mios-src:333e1b58afe2 from build-mios.ps1:313-318 -->

### MiOS-DEV's base machine-OS image. Pinned to 6.0 per...

MiOS-DEV's base machine-OS image. Pinned to 6.0 per operator's
explicit instruction:

  "use 6.0 machine podman-os images!!!!!"

6.0 is the newest stable non-floating tag at quay.io/podman/machine-os
(probed tags = 5.0, 5.1,..., 5.8, 6.0, next).

IMPORTANT compatibility note: pinning a major-version-newer machine-os
than the installed podman client requires the client to know how to
consume it. On podman 5.8.2 (the operator's current client), `--image
docker://quay.io/podman/machine-os:6.0` may fail at the Win32 pull-
extraction step with:
    Error: failed to pull ... : The system cannot find the path specified.
That's a podman-5.8-on-WSL bug, NOT a wrong-URL bug -- 6.0 itself is
correctly published at quay.io. The fix on the operator's side is:
    winget upgrade Podman.Podman
which gets a 6.x client that handles the 6.0 machine-os pull cleanly.

The `docker://` prefix is required for OCI-registry refs on the
`--image` flag; bare refs hit GetFileAttributesEx-as-file-path on
Windows. The MIOS_MACHINE_IMAGE override hatch stays open if a
specific operator wants to fall back to 5.8 (their bundled default)
until they upgrade -- set MIOS_MACHINE_IMAGE='' (empty string) to
omit --image entirely.
Default: NO --image (use podman's bundled local file, which always
works because podman ships its own machine-os tarball alongside the
client). Empirical lesson from logs across this stretch:

  * podman 5.8.2 on Windows / WSL provider FAILS to pull ANY OCI
    ref via `podman machine init --image docker://...` -- both 6.0
    AND the bundled-tag fallback to :5.8 hit the same Win32 error:
        Error: failed to pull quay.io/podman/machine-os@sha256:<digest>:
               The system cannot find the path specified.
    This is a podman-on-Windows pull-extraction bug, NOT a wrong-URL
    bug -- the digests resolve correctly; the local extraction
    stage is broken on the WSL provider for this client version.

  * Without --image, podman uses its bundled local tarball and
    `wsl --import`s it directly -- no pull, no extraction-from-
    registry path, just works. Operator's earlier successful runs
    all took this path.

To pin a specific machine-os tag, the operator must:
  (a) upgrade their podman client to a version that fixes the
      WSL pull bug (`winget upgrade Podman.Podman`, retry)
  (b) THEN set $env:MIOS_MACHINE_IMAGE=docker://quay.io/podman/
      machine-os:6.0 (or whatever tag) before invoking the
      bootstrap.

Until the operator's client is upgraded, pinning is wedged shut by
podman, not by us. This default makes the bootstrap actually
progress instead of dying at Phase 3 with "path not found."

<!-- mios-src:f3eefd951ccf from build-mios.ps1:340-392 -->

### Mirror the path locals to $script: scope so functions...

Mirror the path locals to $script: scope so functions defined in
this file (which use $script:MiosInstallDir / $script:MiosRepoDir
etc. for the AFTER-data-disk-bootstrap variant) ALWAYS find a
valid value -- even when Update-MiosInstallPaths never runs (no
admin, no M:\ provisioning). Without this mirroring,
New-BuilderDistro's `Join-Path $script:MiosInstallDir 'machine-os'`
threw "Cannot bind argument to parameter 'Path' because argument
is null" the moment Phase 3 fired in CurrentUser scope.

<!-- mios-src:958c3ace40ac from build-mios.ps1:437-444 -->

### Early M:\ detection: if the MIOS-DEV partition is already...

Early M:\ detection: if the MIOS-DEV partition is already mounted
(from a previous admin run), redirect EVERY install path onto it
UNCONDITIONALLY -- regardless of whether THIS run is admin. The
operator's expectation per memory feedback_mios_repo_context_invariant
is "EVERY MiOS artifact lives on M:\ when M:\ is provisioned".
Without this early redirect, a non-admin re-run of build-mios.ps1
falls back to C:\Users\Administrator\AppData\Local\MiOS even when
M:\ is right there waiting -- which is exactly the operator's
"should ALL be installing to the created M:\ partition!!!" symptom.

<!-- mios-src:e07092dae433 from build-mios.ps1:458-466 -->

### Data/log/config roots derive from the ALREADY-RESOLVED...

Data/log/config roots derive from the ALREADY-RESOLVED install root
($script:MiosInstallDir) so logging + btop + toml work in BOTH modes:
  * admin / M:\ provisioned -> $script:MiosInstallDir is M:\MiOS (the
    early M:\ redirect / Update-MiosInstallPaths fired above), so logs
    land on M:\MiOS\logs exactly as before -- single mount point holds
    the full audit trail per feedback_mios_m_drive_everything.
  * non-admin (no M:\, no write to C:\) -> $script:MiosInstallDir is
    %LOCALAPPDATA%\MiOS, so logs/config land there instead of a
    non-existent M:\ (which previously hard-broke logging/btop/toml).
The 'M:\MiOS' literal stays only as the last-resort fallback for the
(theoretically unreachable) case where neither root resolved.

<!-- mios-src:bc4916eb6801 from build-mios.ps1:508-518 -->

### Returns the best Windows-side install root, preferring the...

Returns the best Windows-side install root, preferring the dedicated
MiOS data disk (created by Initialize-MiosDataDisk in Phase 3:
shrinks C: by 256 GB, formats NTFS, label "MIOS-DEV", default
mount letter M:). Falls back to the boot-time default
($MiosInstallDir) when the data disk hasn't been provisioned yet.

Honors $env:MIOS_DATA_DISK_LETTER for non-default mount letters
(must match Initialize-MiosDataDisk's -DriveLetter argument).

<!-- mios-src:017ed4c0b1e6 from build-mios.ps1:528-535 -->

### Full-partition overlay

Full-partition overlay: re-point EVERY install path at the new
root so the entire MiOS pipeline (Windows app, repos, dev VM
VHDX, build artifacts, machine-state, logs) lives on the same
volume. The `MIOS-DEV` partition is the operator's choice for
"everything MiOS lives here"; we honor that across the board.

Caller MUST run this BEFORE Phase 2 (repos clone) so the clones
land at the right place for the new "M:\ IS git" layout.

OPERATOR DIRECTIVE -- "MIOS REPOSITORIES BOTH OVERLAYED
AT THE M:\ ROOT". The previous "$MiosRepoDir = M:\MiOS\repo with
mios/ + mios-bootstrap/ as siblings" layout is gone. New layout:

  M:\                  mios.git working tree (M:\.git is mios.git's)
                         + mios-bootstrap.git files overlaid on top
                           (Get-MiOS.ps1, build-mios.ps1, bootstrap.ps1)
  M:\MiOS\               Windows install state (subdirs below)
  M:\MiOS\bin            entry-point .ps1 scripts
  M:\MiOS\share          materialized templates (legacy convenience)
  M:\MiOS\machine-state  podman-machine + WSL2 state
  M:\MiOS\distros        WSL2 distro tarballs
  M:\MiOS\images         BIB output artifacts
  M:\MiOS\logs           install logs
  M:\MiOS\bootstrap-shadow  mios-bootstrap.git's actual checkout (.git lives here
                             so fetch+reset on bootstrap doesn't fight mios.git's
                             .git at M:\); files are robocopied onto M:\ root.

<!-- mios-src:ffcdc3132293 from build-mios.ps1:546-571 -->

### NO-OP by default (final). Kept callable only for legacy...

NO-OP by default (final). Kept callable only for legacy
invocation sites; the function returns immediately unless the operator
explicitly opts in via MIOS_FORCE_LEGACY_MIGRATE=1.

── Why no-op ───────────────────────────────────────────────────

The "C:\\MiOS legacy install -> M:\\MiOS data disk" migration was a
design error. The two surfaces serve DIFFERENT purposes and should
never be merged:

  C:\\MiOS   = developer's git working tree on the Windows host.
              Where the operator edits source, runs git, drives
              Claude Code, etc. Active dev surface.

  M:\\MiOS\\ = bootstrap-created install root for MiOS-DEV runtime
              artifacts: vhdx, icons, themes, machine-state,
              distros, build-output images, logs, plus
              M:\\MiOS\\repo\\ as a Windows-side MIRROR of origin
              (cloned by the bootstrap from origin, NOT migrated
              from C:\\MiOS).

The "full-partition overlay is the LAW" architectural rule applies
INSIDE a running MiOS deployment (the deployed Linux host treats
`/` as a full git working tree against the local Forgejo / cloud
GitHub). It does NOT mean "migrate the developer's Windows-side
working tree onto M:\\".

The previous /MOVE behavior wiped C:\\MiOS files between bootstrap
turns (visible 14:43-14:52 session as a 13-file working-
tree wipe restored via `git checkout HEAD -- ...`) -- a destructive
failure mode for the operator's active dev surface that no
combination of "make it git-aware" or "fence it behind opt-in"
really redeems. The cleanest fix is: don't migrate.

── Bypass switches (env vars; all default off) ─────────────────

  MIOS_FORCE_LEGACY_MIGRATE=1    proceed with destructive
                                 robocopy /MOVE (rare cleanup
                                 scenarios where the operator
                                 KNOWS the legacy root is stale).
  MIOS_SKIP_LEGACY_MIGRATE=1     legacy bypass alias; now the
                                 default behavior, kept
                                 recognized so old recipes
                                 don't error.

<!-- mios-src:7d433d6dee6d from build-mios.ps1:614-658 -->

### Provisions the dedicated MIOS-DEV data disk and re-points...

Provisions the dedicated MIOS-DEV data disk and re-points all
install paths onto it. Idempotent: if M:\ is already a MIOS-DEV-
labeled volume we just redirect; otherwise we shrink C: by the
configured amount and create the partition. Honors:
  $env:MIOS_SKIP_DATA_DISK    - skip everything (legacy C:\MiOS layout)
  $env:MIOS_DATA_DISK_LETTER  - drive letter (default M)
  $env:MIOS_DATA_DISK_MB      - shrink size in MB (default 262144)

Called BEFORE Phase 2 so the repo clones go directly to the
data disk instead of having to migrate later.

<!-- mios-src:c2c620946e4b from build-mios.ps1:717-726 -->

### Verify [Console]::SetCursorPosition actually moves the...

Verify [Console]::SetCursorPosition actually moves the cursor.
In some hosts (Start-Transcript active, redirected stdout, certain
`irm | iex` parent shells, remote PSSession, captured runspace)
the call silently no-ops or throws -- in either case the dashboard
would just stack frames downward forever. Returns $true only when
we can confidently repaint in place.

<!-- mios-src:a08637db8169 from build-mios.ps1:774-779 -->

### ── Log files...

── Log files ─────────────────────────────────────────────────────────────────
UNIFIED COUNTING SYSTEM: there is exactly one logged counter timeline --
the Write-Log entries written to $LogFile by [IO.File]::AppendAllText.
Show-Dashboard writes directly to the console (in-place repaint via
SetCursorPosition) and is NEVER captured to the log file. This keeps
the log a single chronological event stream instead of being flooded
by hundreds of repainted dashboard frames per minute.

Why no Start-Transcript: Start-Transcript wraps stdout at the host
layer, so [Console]::Write calls from Show-Dashboard get captured.
Each 150ms repaint then duplicates the entire ~20-row dashboard into
the log. Direct file append-only logging avoids this entirely.

<!-- mios-src:310a1660de3e from build-mios.ps1:815-826 -->

### Capture build-mios.ps1's own commit SHA when running from a...

Capture build-mios.ps1's own commit SHA when running from a git
working tree. This is invaluable for diagnosing "is the user
actually running the latest build-mios.ps1?" -- GitHub raw +
Fastly caching can serve a stale outer Get-MiOS.ps1 / cached
mios-bootstrap clone for ~5 minutes after a push, and without
this stamp it's impossible to tell from the log whether a
specific fix was reachable.

<!-- mios-src:db632fbb75c8 from build-mios.ps1:837-843 -->

### Promote to script scope so the dashboard's title can show...

Promote to script scope so the dashboard's title can show it on
every screenshot -- the operator can see at a glance which
commit is actually running, no log-grep required.

<!-- mios-src:f36c31036e21 from build-mios.ps1:854-856 -->

### Console mirroring policy

Console mirroring policy:
  * INFO/DEBUG -> file ONLY. Never Write-Host. The previous code
    said "interactive: mirror every line, Show-Dashboard repaints
    over them" but Show-Dashboard only writes ~25 rows; the
    quadlet-overlay seed alone emits hundreds of INFO lines (file
    update percent x 618, oh-my-posh sub-lines, etc.), drowning
    the dashboard with scrolling text and producing the
    stacked-frame screenshot artifact. The operator sees the
    current step via $script:CurStep on the dashboard's now-line;
    the log file is authoritative for everything else.
  * WARN/ERROR -> file + Write-Host. Operators MUST see these,
    so we surface them above the dashboard. Show-Dashboard's next
    tick scrolls the visible region but the log file always has
    the canonical record.

<!-- mios-src:a8c3eaf6c94a from build-mios.ps1:891-904 -->

### ── MiOS globals (ONE central loader)...

── MiOS globals (ONE central loader) ────────────────────────────────────────
"EXACTLY BUT FOR ALL VARIABLES GLOBALLY!!!!".
Every shared mios.toml value the build pipeline reads is loaded
ONCE here into the $script:Mios* namespace and read by name from
downstream code instead of each site re-calling Get-MiosTomlValue.
Single source-of-truth catalog -- one call site for each toml key.

<!-- mios-src:0a22c8e006a2 from build-mios.ps1:913-918 -->

### ── [terminal] -- framing only ───────────────────────────...

── [terminal] -- framing only ───────────────────────────
cols / rows / scrollback are loaded at top-of-script into
$script:MiosInst{Cols,Rows} (install conhost) + $script:MiosApp{
Cols,Rows} (post-install MiOS app) -- DIFFERENT toml sections
([terminal.install] vs [terminal]) -- so Initialize-MiosGlobals
doesn't touch them to avoid clobbering the install dims with
the app dims.  Frame width / height / right_margin ARE
loaded here because they're identical for both contexts.

<!-- mios-src:d388a8dadd8a from build-mios.ps1:920-927 -->

### Per the self-replication architecture, the Windows side...

Per the self-replication architecture, the Windows side (BootstrapOnly,
the default for irm | iex entry) does ONLY:
  ack -> hardware/env probe -> minimal mios-bootstrap clone ->
  MiOS-DEV podman-machine setup -> .wslconfig sanity ->
  Start Menu / shortcuts -> SSH handoff into MiOS-DEV.
Everything else (identity prompts, OCI build, WSL2/Hyper-V/QEMU
image exports, disk-image generation) belongs INSIDE MiOS-DEV via
/usr/libexec/mios/mios-build-driver -- no Windows-side rendering of
those phases. We render a 6-entry dashboard in BootstrapOnly mode
and the historical 14-entry one in -FullBuild / -BuildOnly mode.

$AppRegPhaseId is the index for the "App registration" phase in
whichever array is active; the Start-Phase / End-Phase callers near
the bottom of the script reference it so we don't hardcode 8 or 5.
Phase names resolve through mios.toml [install_phases.<mode>] (SSOT).
Operator edits via mios.html flow mios.toml -> next install run uses
the new names. Vendor fallback below is the cold first-run set when
no TOML is reachable.

<!-- mios-src:9d9891aab14f from build-mios.ps1:977-994 -->

### Last-rendered row count -- used by Show-Dashboard to blank...

Last-rendered row count -- used by Show-Dashboard to blank rows that
were part of a previous larger render but are no longer present in
the current one. Without this, transitioning from a 14-phase layout
to a 6-phase layout (BootstrapOnly mode truncating the tail) leaves
the bottom 8 rows of the previous dashboard as ghost content.

<!-- mios-src:5b2951f1c8ce from build-mios.ps1:1044-1048 -->

### Last-rendered row WIDTH (in columns). Tracks the high-water...

Last-rendered row WIDTH (in columns). Tracks the high-water mark
across renders so a render that ends up narrower than a prior one
(e.g. terminal got resized down by 1 col, [Console]::WindowWidth
reported a smaller value, or the box width clamp dropped from 80
to 79) still pads to the previous max -- otherwise the previous
render's RIGHTMOST column lingers as a vertical ghost stripe of
`+`/`|`/`=` characters running down the right edge of the new
narrower render.

<!-- mios-src:64259c124cc2 from build-mios.ps1:1050-1057 -->

### Build sub-step denominator. In -BootstrapOnly mode we never...

Build sub-step denominator. In -BootstrapOnly mode we never run
the OCI build, so the 48 podman-build steps don't apply -- using
the full 48 makes the dashboard's "0/62" denominator nonsensical
for a 6-phase bootstrap run. Set to 0 here when bootstrap-only;
the full path (-FullBuild / -BuildOnly) bumps it back to 48 once
Phase 8 starts.

<!-- mios-src:a5fd63aaa06d from build-mios.ps1:1060-1065 -->

### ── Render throttle...

── Render throttle ──────────────────────────────────────────────────────
Show-Dashboard is invoked once per stdout line during heavy native
commands (podman build, dnf install, etc.) -- 100+ calls/second
during a layer pull. Each render writes ~25 rows via per-row
SetCursorPosition + Write, and the conhost / WT pseudo-console
tears visibly when repaints land mid-flush. Cap at 10 fps (100 ms
between renders) -- imperceptible lag, no tearing. Force overrides
for end-of-phase / state-change calls that must show NOW.

<!-- mios-src:0238c8c05382 from build-mios.ps1:1136-1143 -->

### ── Sizing -- max 80 cols (standard tty0/console)...

── Sizing -- max 80 cols (standard tty0/console) ──────────────────────────
Pad to BufferWidth, not just WindowWidth. The buffer can be wider
than the visible window (Windows console default = 120-col buffer
in a 80-col window), and log lines written before the dashboard
rendered may have left stale content at buffer columns past the
visible right edge. PadRight(WindowWidth) only clears up to the
visible width; PadRight(BufferWidth) clears every column the log
could have written to. Per the operator's "ics / oder:14b /
GB free)" right-edge bleed in repeated screenshots.

<!-- mios-src:d5561304ef66 from build-mios.ps1:1154-1162 -->

### ── Width strict-clamp...

── Width strict-clamp ────────────────────────────────────────────
The previous code did `winW = max(winW, bufW, DashLastWidth)` to
"blank stale columns from a wider previous render" -- but that
ratchet locks the padding wider than the live buffer for the
rest of the session.

Concrete failure mode (commit 53ac9d8 stacking screenshots):
  1. Load-time resize: 80x30 / 80x9000
  2. `Try-ResizeConsole -Cols 100 -Rows 40` (~line 4501)
     enlarges to 100x40 transiently
  3. First Show-Dashboard: winW=max(100, 100, 0)=100, rows padded
     to 100, DashLastWidth=100
  4. Defensive resize (~line 4395): back to 80x30 / 80x9000
  5. Every later Show-Dashboard: winW=max(80, 80, 100)=100
  6. Writing a 100-char row on an 80-col buffer auto-wraps at
     col 79; 20 chars overflow to the next buffer row; the next
     iteration overwrites cols 0-79 of that row but the
     now-orphaned wrap content from the previous iteration stays
     visible -> the stacked-banner artifact.

Strict-clamp: never pad wider than the LIVE current console.
Capped at 80 for tty0/console portability. If a previous render
was wider than the current, the ghost-row blanking pass below
handles those extra rows; we never need to keep padding wide.

<!-- mios-src:dd0677b60fd9 from build-mios.ps1:1166-1189 -->

### ── Phase table col widths...

── Phase table col widths ────────────────────────────────────────────────
Single table layout used by header / divider / data rows:

  "{0,2} {1,-6} {2,-nameW} {3,5}"
    idx  tag   name        time
    2  +1+ 6  +1+ nameW   +1+ 5  = 16 + nameW

Setting nameW = $in - 16 makes every row land at exactly $in
characters of content, so the right "|" border sits in the same
column on all three rows -- no more zigzag right edge.

<!-- mios-src:55773e7bcdaa from build-mios.ps1:1239-1248 -->

### Stamp the commit SHA in the title so every screenshot of...

Stamp the commit SHA in the title so every screenshot of the
dashboard makes it unambiguous which build-mios.ps1 is running.
Diagnoses Fastly cache lag at a glance: if the operator sees
"(commit abc1234)" but the latest fix you just pushed is def5678,
they're on stale code.

<!-- mios-src:8ed0503289c0 from build-mios.ps1:1257-1261 -->

### ── ONE counter, ONE bar...

── ONE counter, ONE bar ──────────────────────────────────────────────────
Single global step counter (phases + build sub-steps) rendered as
one progress bar. The textual "Phase [N/Total]" and "(step X/Y)"
rows used to duplicate this same metric three different ways and
are intentionally gone -- the bar's "N/M" suffix is THE counter.
Current operation + spinner share one row above the bar so the
operator sees what's running without a second phase-counter line.
Bounds-clamp $script:CurPhase against PhStat.Count -- defensive
against any code path that sets CurPhase past the end of the array
(e.g. Start-Phase 9 in a mode where TotalPhases=6 -- the BootstrapOnly
collapsed layout). Without this clamp, [Console]::Write fires a
"Index was outside the bounds of the array" that gets caught by
MAIN's try/catch and surfaces as the dashboard's FATAL banner.

<!-- mios-src:5981c7762be0 from build-mios.ps1:1288-1300 -->

### Per-row absolute cursor placement. The previous code relied...

Per-row absolute cursor placement. The previous code relied on
NewLine to advance to col 0 of the next row; in wider hosts
(110-160+ col terminals against an 80-cap buffer, or when the
background heartbeat slipped a write between rows) the cursor
could land mid-row, painting subsequent rows offset to the
right -- the visible "side-by-side ghost dashboard" symptom.
SetCursorPosition before each Write guarantees col=0.

<!-- mios-src:8fd6b49ea223 from build-mios.ps1:1364-1370 -->

### No ANSI \e[K -- the operator's terminal sometimes does NOT...

No ANSI \e[K -- the operator's terminal sometimes does NOT
process the escape, in which case the literal "[K" leaks
into the dashboard view (seen in paste). The
strict-clamp on $winW above caps every row at 80 chars
already, so stale content past col 80 from prior renders
is not the concern it was; rely on row-overwrite alone.

<!-- mios-src:a2686596b622 from build-mios.ps1:1375-1380 -->

### ── Ghost-row blanking...

── Ghost-row blanking ────────────────────────────────────────
If a previous render placed MORE rows than this one, blank
those tail rows with a $winW-wide space line so the previous
bottom of the dashboard doesn't linger underneath the new
render. Common cause: BootstrapOnly mode collapses the phase
table from 14 -> 6 rows mid-run; without this loop, phases
6-13 stay visible as orphan text below the new bottom border.

<!-- mios-src:8cb88e41a227 from build-mios.ps1:1383-1389 -->

### DashLastWidth is no longer ratcheted -- the strict-clamp on...

DashLastWidth is no longer ratcheted -- the strict-clamp on
$winW makes the ratchet harmful (locks padding wider than the
live buffer; see comment near top of Show-Dashboard).

<!-- mios-src:94d373834b02 from build-mios.ps1:1402-1404 -->

### Inline progress bar -- prints once at each phase boundary...

Inline progress bar -- prints once at each phase boundary
(called from End-Phase). Counts COMPLETED phases (PhStat
entries >= 2 i.e. OK/FAIL/WARN). 50-cell bar, operator-blue
filled, dim unfilled. NO ANSI cursor manipulation -- earlier
attempts at scroll-region pinning fought PowerShell's normal
output flow and produced garbled banners + interleaved bars.
The bar scrolls with the log; that's the trade-off.

<!-- mios-src:227304334d92 from build-mios.ps1:1457-1463 -->

### Scrub keys from $env:USERPROFILE\.wslconfig's [wsl2]...

Scrub keys from $env:USERPROFILE\.wslconfig's [wsl2] section that
don't belong there. The most common mis-placement is `systemd=true`,
which is a /etc/wsl.conf [boot] directive (per-distro, INSIDE the
distro's filesystem) -- never a .wslconfig [wsl2] directive
(host-side, Windows). When wsl.exe parses .wslconfig and finds an
unknown key it prints:

    wsl: Unknown key 'wsl2.systemd' in C:\Users\...\.wslconfig

Older wsl versions treat that as a warning, newer ones can fail
the parse entirely. Either way the line ends up in our Phase 3
podman-init pipeline capture and surfaces as a FATAL with the
warning text (because the dashboard displays the LAST stderr line
captured before podman exits non-zero).

This helper runs once at the end of Phase 0 so every subsequent
WSL/podman invocation in the build sees a clean .wslconfig.

<!-- mios-src:9eaa354839f4 from build-mios.ps1:1545-1561 -->

### BOM-free

BOM-free: PS 5.1 `Set-Content -Encoding UTF8` writes a UTF-8 BOM, and a
leading BOM makes WSL silently IGNORE the [wsl2] section (the operator's
memory/processor limits are dropped). WriteAllLines + UTF8Encoding($false)
is BOM-free on 5.1 AND pwsh 7. install-robustness.

<!-- mios-src:385f74fd1631 from build-mios.ps1:1597-1600 -->

### Invoke a native command with stderr collected into the...

Invoke a native command with stderr collected into the success stream
but WITHOUT the "$ErrorActionPreference='Stop' + 2>&1" trap that
causes a chatty stderr (git's "Cloning into ...", "From https://...",
"Receiving objects: ...") to surface as a fatal exception. Returns
the command's $LASTEXITCODE so callers can do their own checks. Kept
minimal -- callers that want to inspect stdout/stderr can swap to
Invoke-NativeQuiet's variable-capture variant below.

<!-- mios-src:b062c1fa7463 from build-mios.ps1:1606-1612 -->

### Post-bootstrap interactive menu. Called from the...

Post-bootstrap interactive menu. Called from the BootstrapOnly path
in MAIN after Install-MiosLauncher has dropped the Start Menu /
Desktop shortcuts -- the operator now has a fully-provisioned dev
VM + Windows-side surface and chooses what to do next from here:

  1. Continue to build      -> re-invoke this script with -BuildOnly
                               so the OCI image build runs against
                               the freshly-provisioned MiOS-DEV.
  2. Change settings         -> open the configurator HTML for an
                               interactive mios.toml edit pass
                               (Open-Configurator).
  3. System checks           -> run preflight.ps1 against the
                               current state (MiOS-DEV health,
                               mios.toml validation, .wslconfig,
                               disk space, GHCR token).
  4. Logs / reports          -> print the unified log path + the
                               last 30 lines.
  5. Close                   -> exit cleanly.

Skipped automatically when -Unattended is set (CI / non-interactive).

<!-- mios-src:40645f28a8fd from build-mios.ps1:1625-1644 -->

### Resolve the actual WSL distro name once -- podman-machine...

Resolve the actual WSL distro name once -- podman-machine prefixes
its distros with `podman-` (so the on-disk distro is podman-MiOS-DEV
by default), the auto-rename to plain MiOS-DEV is opt-in via
MIOS_RENAME_DISTRO=1, and operators commonly type `wsl -d MiOS-DEV`
only to hit `WSL_E_DISTRO_NOT_FOUND`. Print the live name so the
operator can copy-paste it.

<!-- mios-src:34fb348ce308 from build-mios.ps1:1648-1653 -->

### Clear the screen before every menu render so the canvas is...

Clear the screen before every menu render so the canvas is
always clean -- whether this is the first render after
bootstrap OR a re-render after the operator picked an
option (wsl entry, configurator, etc.) and returned. Any
output from the previous option (wsl session output, build
tail, etc.) is wiped so the menu draws against blank space.

<!-- mios-src:d2fbde1b1020 from build-mios.ps1:1664-1669 -->

### ── Windows -> MiOS-DEV handoff (per self-replication...

── Windows -> MiOS-DEV handoff (per self-replication contract) ──
The Windows side has finished its STRICT scope: ack +
MiOS-DEV podman-machine setup. The actual build (OCI +
WSL2/g + Hyper-V + QEMU + Live-CD + USB + RAW) runs
INSIDE MiOS-DEV. We open a fresh Windows Terminal tab
hosting `wsl.exe -d <distro>` -- the MiOS-DEV tty
renders the dashboard there directly, no streaming
back across the WSL/Windows boundary.

<!-- mios-src:eedbe07d2ea7 from build-mios.ps1:1697-1704 -->

### The driver lives in the MiOS image at...

The driver lives in the MiOS image at /usr/libexec/mios/mios-build-driver.
Phase 3's quadlet-overlay drops it into MiOS-DEV, so by the time the
operator picks "1" the file is present. We invoke it directly with a
SINGLE-LINE bash command -- multi-line heredocs survive PowerShell -> wt
-> wsl arg-parsing only if every layer quotes correctly, and previously
the chain shredded a heredoc into pseudo-args, surfacing as
    [error 2147942402 (0x80070002): The system cannot find the file specified.]
at wt.exe spawn time. Single-line, single-quoted-on-bash-side, no escapes.

<!-- mios-src:ef8180ec3d63 from build-mios.ps1:1717-1724 -->

### Open a NEW Windows Terminal window at exactly 80x30 to...

Open a NEW Windows Terminal window at exactly 80x30 to
match the dashboard frame (per feedback_mios_terminal_
dimensions.md). `wt.exe --size W,H -- <cmdline>` sets
the initial dimensions of a NEW wt window; `new-tab`
inherits whatever the parent window already has, which
is wrong for the build-pipeline tty.

<!-- mios-src:31b664b89caf from build-mios.ps1:1747-1752 -->

### Resolve which user actually exists in the distro before...

Resolve which user actually exists in the distro
before launching. Rootful machine-os ships with
`core` (and root) but no `mios` user until the
OCI build completes -- in which case --user mios
fails with WSL_E_USER_NOT_FOUND. Probe the
distro's /etc/passwd to pick the first available
account in priority order: mios > core > root.

<!-- mios-src:26cb6b998001 from build-mios.ps1:1827-1833 -->

### NB: Windows PowerShell 5.1 (the universal elevation...

NB: Windows PowerShell 5.1 (the universal elevation fallback in
Get-MiOS.ps1's chain) doesn't support the PS7 ternary operator,
so this stays as a plain if/else.

<!-- mios-src:d113c4e4e3da from build-mios.ps1:1862-1864 -->

### AI model menu prompt -- feature parity with build-mios.sh's...

AI model menu prompt -- feature parity with build-mios.sh's
prompt_model. Drives MIOS_LLAMACPP_BAKE_MODELS at build time and
MIOS_AI_MODEL in install.env at runtime. Same auto-accept
semantics as the rest of the Phase-6 prompts. The lineup is
sourced from mios.toml [ai.host_thresholds] (the RAM-tier table)
so the menu never drifts from the SSOT -- the three options map
1:1 onto small/mid/big_ram_model plus a custom escape hatch.

<!-- mios-src:da53c345efa6 from build-mios.ps1:1869-1875 -->

### Read [ai].model / [ai].embed_model / [ai].bake_models out...

Read [ai].model / [ai].embed_model / [ai].bake_models out of the
unified mios.toml dotfile. Walks the same layered overlay
build-mios.sh's resolve_profile_layers walks, so per-host edits
to /etc/mios/mios.toml or ~/.config/mios/mios.toml seed the
interactive prompt without re-cloning. Pure regex parser; no TOML
library dependency. Returns a hashtable -- caller picks fields.
Vendor fallbacks mirror the SSOT [ai] section (model / embed_model)
so an absent/unreadable card lands on the same values the canonical
mios.toml declares; bake = model + embed.

<!-- mios-src:9ce2526ea64d from build-mios.ps1:1900-1908 -->

### Open /usr/share/mios/configurator/mios.html for the...

Open /usr/share/mios/configurator/mios.html for the operator to
edit the unified mios.toml. Canonical path: launch Epiphany IN
MiOS-DEV via WSLg so the configurator runs inside the same
environment that built it. The window appears on the Windows
desktop; the saved mios.toml lands in the dev VM's FHS-compliant
~/Downloads (which IS the bootc-style home/user/Downloads
location, since MiOS-DEV mirrors the deployed MiOS layout). The
PowerShell side then picks up that file and overlays it as the
new source for the build pipeline -- so the operator's Epiphany
save IS the build's input.

Falls back to the operator's default Windows browser if MiOS-DEV
isn't reachable or Epiphany is unavailable (covers fresh installs
before the dev distro has finished provisioning).

<!-- mios-src:d53fc99f5db8 from build-mios.ps1:1965-1978 -->

### Seed the working mios.toml in ~/Downloads. The...

Seed the working mios.toml in ~/Downloads. The configurator's "Pick file"
button binds to it; "Save" overwrites in place (File System Access API)
or, if the WebKit build lacks FSA, the operator triggers a download that
also lands here.

<!-- mios-src:9a7c38aa2165 from build-mios.ps1:2055-2058 -->

### Pick up the saved mios.toml from MiOS-DEV's ~/Downloads and...

Pick up the saved mios.toml from MiOS-DEV's ~/Downloads and
promote it as the build source. We write to BOTH:
  1. %APPDATA%\MiOS\mios.toml   -- runtime per-user overlay
  2. mios-bootstrap clone root   -- seed-merge inputs to podman build
so the very next build/install pass uses the operator's edits.

<!-- mios-src:3b20932f4fa1 from build-mios.ps1:2120-2124 -->

### Legacy / fallback path

Legacy / fallback path: run the configurator in the operator's
default Windows browser. Used when MiOS-DEV isn't reachable yet
(e.g. fresh install before Phase 3 finishes) or when WSLg is
disabled. Saves go through the Windows Downloads folder via the
standard <input type="file"> + downloads flow.

<!-- mios-src:84d1d4f0c9b0 from build-mios.ps1:2147-2151 -->

### Detect host capability

Detect host capability: full CPU / RAM / disk / GPU surface.
Then apply mios.toml [bootstrap.dev_vm.host_reserve] to compute
the dev-VM allocation. The dev VM IS the builder (memory:
feedback_mios_dev_is_the_builder), so we err maximalist — give
it every resource the host can spare while keeping Windows
responsive.

Override sources (highest precedence first):
  1. $env:MIOS_DEV_VM_{CPUS,MEMORY_MB,DISK_GB} — explicit pin
     from mios.toml [bootstrap.dev_vm].* if not set to "max"
  2. $env:MIOS_DEV_VM_*_RESERVE_* — host reserve policy from
     mios.toml [bootstrap.dev_vm.host_reserve]
  3. Hardcoded fallbacks below

<!-- mios-src:aab89ba72c18 from build-mios.ps1:2226-2238 -->

### Pre-stage a podman-machine OCI image via direct HTTPS...

Pre-stage a podman-machine OCI image via direct HTTPS, bypassing
`podman machine init`'s pull-extraction pipeline. On podman 5.8.2
for Windows + WSL provider that pipeline fails with:
    Error: failed to pull quay.io/podman/machine-os@sha256:<...>:
           The system cannot find the path specified.
for ANY ref (6.0, 5.8, bundled default). Direct GET against the
OCI Distribution API works fine -- the bug is in podman's own
cache write step on Windows. Pre-staging the layer ourselves and
passing the result to `--image <local-path>` skips the broken
path entirely.

Returns the local file path on success; throws on failure. The
output filename follows the layer's
`org.opencontainers.image.title` annotation
(e.g. "podman-machine.x86_64.wsl.tar.zst") so podman recognizes
the format from the extension alone.

<!-- mios-src:ff51a2989ded from build-mios.ps1:2528-2543 -->

### ── Step 1: image index...

── Step 1: image index ───────────────────────────────────────────
PowerShell 5.1's Invoke-WebRequest -UseBasicParsing returns
.Content as a byte[] for non-text content types (anything not
in its hard-coded text list -- application/json IS text but
application/vnd.oci.image.index.v1+json is NOT, despite the
`+json` suffix). Piping the byte[] to ConvertFrom-Json
stringifies the array to "123 34 115 ..." and produces an empty
object -- which is exactly the "got mediaType=" symptom seen in
the 16:35 log. Force UTF-8 decode so ConvertFrom-Json sees the
actual JSON text.

<!-- mios-src:95d3bc0cb870 from build-mios.ps1:2565-2574 -->

### Force the podman-managed WSL2 distro VHDX onto M:\. WSL2...

Force the podman-managed WSL2 distro VHDX onto M:\. WSL2 ignores
XDG_DATA_HOME; it stores VHDXs at the path passed to `wsl --import`
(or under %LOCALAPPDATA%\Packages\<distro-id>\LocalState if podman
didn't pass an explicit path). The registry HKCU\...\Lxss\<guid>\
BasePath records where each distro's ext4.vhdx actually lives.

Procedure (idempotent, only fires when BasePath is NOT under M:\):
  1. Read BasePath from registry
  2. If already on M:\ -> no-op + log
  3. Else: wsl --shutdown, export tar, unregister, import to
     M:\MiOS\distros\<distroname> -- VHDX bytes now live on M:\

podman picks the distro back up because podman locates it by name
via wsl.exe -- the import path doesn't matter to podman's
connection state.

<!-- mios-src:9f9d7efd768d from build-mios.ps1:2684-2698 -->

### Redirect podman-machine state (the VHDX, registry, configs)...

Redirect podman-machine state (the VHDX, registry, configs) onto
M:\ when M:\ is mounted -- no admin required. Podman honors
XDG_DATA_HOME for storage paths on Windows (machine-state lands
at <XDG_DATA_HOME>\containers\podman\machine). This is the
non-admin path equivalent of Set-PodmanMachineStorageOn's
mklink /D approach (which requires elevation).
Without this, the dev distro's VHDX (multi-GB, grows during the
OCI build) lands on C: instead of the operator's M:\ partition.

<!-- mios-src:66af3c871081 from build-mios.ps1:2778-2785 -->

### $HW.RamGB is already the maximalist-minus-host-reserve...

$HW.RamGB is already the maximalist-minus-host-reserve allocation
computed by Get-Hardware (per mios.toml [bootstrap.dev_vm.host_reserve]).
Multiply to MB and clamp once more against the OS-reported total
(what podman validates; nominal Win32_PhysicalMemory rounds up and
would otherwise cause podman to reject the request) minus a 512 MB
safety margin. Floor of 4096 MB so the dev VM is always usable.

<!-- mios-src:382561e945bf from build-mios.ps1:2794-2799 -->

### ── Pre-stage machine-os via direct HTTPS...

── Pre-stage machine-os via direct HTTPS ──────────────────────────────────
On podman 5.8.2 (Windows + WSL provider) the in-process pull pipeline
fails for ANY machine-os ref with "system cannot find the path
specified". Direct OCI-Distribution GET against quay.io works fine,
so we fetch the wsl-x86_64 layer ourselves and hand podman a local
`.tar.zst` path -- no registry pull happens inside podman at all.

Default tag: 6.0 (per operator instruction). Override with
MIOS_MACHINE_TAG=<tag> or MIOS_MACHINE_IMAGE=<docker:// url> for a
specific ref; pre-stage runs in both cases.
Default machine image sourced from mios.toml [bootstrap.dev_vm].
base_image (vendor default: quay.io/podman/machine-os:6.0). Env var
MIOS_MACHINE_TAG / MIOS_MACHINE_IMAGE still wins for ad-hoc overrides.

<!-- mios-src:45675a8e83ed from build-mios.ps1:2809-2821 -->

### Retry-with-backoff loop. quay.io has been intermittently...

Retry-with-backoff loop. quay.io has been intermittently
502/503-ing during peak hours; without retry, a 5-minute
outage kills the entire bootstrap. 3 attempts with 5s/15s/30s
backoff covers most transient registry blips. Cache-hit
short-circuit inside Get-PodmanMachineOsImage means a
successful prior fetch makes subsequent retries instant.

<!-- mios-src:81948ac249a7 from build-mios.ps1:2842-2847 -->

### Retry schedule from mios.toml...

Retry schedule from mios.toml [network.retry].delays_seconds
(vendor default: 0s, 5s, 15s, 30s). Operator can lengthen for
known-flaky upstreams via the configurator HTML.

<!-- mios-src:c4ef08ff7928 from build-mios.ps1:2850-2852 -->

### Build the arg list dynamically so --image is only passed...

Build the arg list dynamically so --image is only passed when the
operator (or env override) has supplied one. With no --image,
podman init uses its bundled default -- always compatible with
the installed client version.

<!-- mios-src:a310dfefa426 from build-mios.ps1:2890-2893 -->

### Wrap the init invocation in a fresh child scope with...

Wrap the init invocation in a fresh child scope with
$ErrorActionPreference='Continue'. Without this, podman's normal
post-start stderr line (e.g. "API forwarding for Docker API
clients is not available...") trips the script's outer EAP=Stop
via the 2>&1 stream merge and surfaces as a Phase 3 FATAL even
though `podman machine init` exited 0 and the machine is fully
up. $LASTEXITCODE survives the scope exit (it's an automatic
variable populated globally by every native command invocation),
so the if-($initRc -ne 0) check below sees the real exit code,
not a phantom from a stream-merged warning.

<!-- mios-src:efbb3fecb135 from build-mios.ps1:2906-2915 -->

### ── Recovery branch 1: pull failed on a pinned --image...

── Recovery branch 1: pull failed on a pinned --image ──────────────────
Pinning $MachineImage to a tag the operator's installed podman client
can't pull (typical: docker://quay.io/podman/machine-os:6.0 against a
podman 5.8 client) produces:
    Error: failed to pull quay.io/podman/machine-os@sha256:<digest>:
           The system cannot find the path specified.
init exits 125 BEFORE creating any registration, so there's no
cleanup needed -- just retry without --image so podman uses its
bundled default (which the client always knows how to handle).
The fallback is logged so the operator sees they're on a
fallback tag and can `winget upgrade Podman.Podman` to actually
land on their requested pin.

<!-- mios-src:5300ae160168 from build-mios.ps1:2935-2946 -->

### "VM already exists" -- recover by starting (or treating as...

"VM already exists" -- recover by starting (or treating as already
running) instead of failing. Caller's outer loop already tried to
detect a running machine; we got here because the registration
exists but `podman machine ls` didn't expose it as running, which
also matches Windows Subsystem for Linux's transient ghost state
right after a previous interrupted init. Best response is just to
try starting it and verify the API.

<!-- mios-src:02043a63124c from build-mios.ps1:2977-2983 -->

### MUST wrap in EAP=Continue +...

MUST wrap in EAP=Continue + PSNativeCommandUseErrorActionPreference=$false:
podman returns non-zero on "already running" (which IS our happy
path here), and PS 7.4+ defaults PSNativeCommandUseErrorActionPreference
to $true -- so a non-zero exit throws BEFORE the regex match below
can downgrade it to a Log-Ok. The init call uses the same wrap; this
one was missing it and threw straight to the outer FATAL handler.

<!-- mios-src:efb648afb228 from build-mios.ps1:2986-2991 -->

### Start failed too -- registration is stale or the VM is in a...

Start failed too -- registration is stale or the VM is in
a half-provisioned state from a SIGINT'd previous run.
Force-remove the registration and re-init from scratch.
Safe at this point in the pipeline: no MiOS image / no
operator data lives in the build VM yet.

<!-- mios-src:0910197e9d58 from build-mios.ps1:3009-3013 -->

### v3: WSL unregister chain + final `wsl --shutdown` to fully...

v3: WSL unregister chain + final
`wsl --shutdown` to fully reset the WSL2 service state
before retry-init.  Previous v2 (commit c434302) got
past the getpwnam crash but the retry-init then hit
`Wsl/Service/RegisterDistro/E_FAIL ... Error code: 6,
failure step: 2` (= WSL_E_VM_MODE_INVALID_STATE) --
the WSL service was in a transient bad state from
the unregister + reparse-point-removal cycle, and
`wsl --import` to the M:\ path failed.  `wsl
--shutdown` forces a clean lifebooot of the WSL2
subsystem so import lands cleanly.  Whole block in
EAP=Continue so non-zero exits don't throw to FATAL.

<!-- mios-src:55cac30c51ae from build-mios.ps1:3017-3028 -->

### Sweep ALL candidate podman-machine storage paths...

Sweep ALL candidate podman-machine storage paths
unconditionally. A previous run (admin or otherwise)
may have left:
  * a dangling symlink ([Test-Path] returns false on
    these because PS resolves the target -- so the
    prior dangling-only check missed them entirely)
  * a non-dangling symlink to a now-stale target
  * a real directory with stale machine state
ANY of these can make podman init's Mkdir() fail
with "Cannot create a file when that file already
exists". After `podman machine rm --force` the VM
registration is gone, so the on-disk state in these
paths is unambiguously safe to wipe.

DirectoryInfo lets us probe both regular dirs AND
reparse points without follow-the-link semantics --
Test-Path's "exists" check fails on dangling links.

<!-- mios-src:3e32e8cb1226 from build-mios.ps1:3052-3068 -->

### Tolerate a non-zero rmdir exit

Tolerate a non-zero rmdir exit: the junction may already be gone
(dangling target / prior run / race). Under PS7 a native non-zero
exit THROWS under EAP=Stop, which previously FATAL'd the whole
install here ("The system cannot find the file specified"). Isolate
it in an EAP=Continue scope (same guard as the retry-init below) so
an already-absent link is a no-op, not a fatal.

<!-- mios-src:507c478432b9 from build-mios.ps1:3099-3104 -->

### ── Force the podman-MiOS-DEV WSL distro onto M:\...

── Force the podman-MiOS-DEV WSL distro onto M:\ ────────────────────
Operator: "podman-MiOS-DEV MUST also be located on M:\". XDG_DATA_HOME=
(4th time): "I have told you the broken
MiOS-DEV machine is due to relocation and renaming breaking
the connections!!!".  Move-PodmanWslDistroToM does a
wsl --export + unregister + import which breaks podman's
internal machine state (podman's config files reference the
old VHDX path; after import the distro has the same name but
podman doesn't recognize it as the same machine -- subsequent
`podman machine` commands fail with "machine not found" /
`wsl ... getpwnam(root) failed 5`).

Per memory feedback_mios_distro_name_locked +
feedback_mios_dev_on_m_drive: junctions ONLY, never re-import.
The XDG_DATA_HOME=M:\podman set at the top of New-BuilderDistro
+ the reparse-point junctions on every podman-machine candidate
path (Set-PodmanMachineStorageOnM, called from Initialize-DataDisk)
already redirect new VHDX writes to M:\ at podman init time --
no migration needed.

Gated behind $env:MIOS_FORCE_VHDX_MIGRATE=1 for the rare case
where the junction approach fails on a host (e.g., admin denied
symlink creation).  Default is to SKIP the migration entirely.

<!-- mios-src:80c8955a2515 from build-mios.ps1:3147-3169 -->

### Use `podman machine inspect --format {{.State}}` -- it...

Use `podman machine inspect --format {{.State}}` -- it returns the
canonical state string ("running" / "starting" / "stopped"). The
older `podman machine ls --format {{.Running}}` boolean is broken on
podman 5.8: it returns "false" for several seconds AFTER the machine
is actually up (LastUp shows "Currently starting" while State is
already "running"). Inspect.State flips first and is what podman
itself uses for socket-readiness gating.

<!-- mios-src:c290bf1781ad from build-mios.ps1:3184-3190 -->

### DEPRECATED bare invocation is a silent no-op. Original...

DEPRECATED bare invocation is a silent no-op.

Original purpose: read mios.toml packages.* sections
from the cloned mios.git checkout and run `dnf5 install` per
block inside MiOS-DEV. Replaced by Invoke-MiosQuadletOverlay
(which makes / a git working tree of mios.git) plus
automation/lib/packages.sh (which resolves mios.toml
[packages.<section>].pkgs as the SSOT).

Per project_mios_self_replication_vision.md the package surface
is now baked into the OCI image at build time and made live on
MiOS-DEV via `bootc switch` + reboot at the end of the
mios-build-driver flow. There's no more "live overlay" install
step on the Windows side -- the dev VM gets the same packages
by becoming the OCI image, not by running dnf at the host level.

Force-enable for testing-only via MIOS_FORCE_LEGACY_PACKAGES_MD=1
(intentionally undocumented in the operator-facing flow).

<!-- mios-src:9698fff64a1a from build-mios.ps1:3213-3230 -->

### Resolve the dev-overlay section list from the user's...

Resolve the dev-overlay section list from the user's mios.toml. The
layered resolver (highest wins): per-user (~/.config/mios/mios.toml),
host (/etc/mios/mios.toml), bootstrap clone, vendor. The PowerShell side
stages the highest-precedence layer at $SRC_TOML before invoking us.
Falls back to a hardcoded minimal list if no [packages.dev_overlay].sections
array is present.

<!-- mios-src:46ee232f34d4 from build-mios.ps1:3288-3293 -->

### Hard always-skip list. This wins even if the operator typed...

Hard always-skip list. This wins even if the operator typed e.g.
"kernel" into mios.toml -- those sections are WSL-incompatible or
anti-pattern fences and refusing them is the right move.

<!-- mios-src:06fc3e1c1c18 from build-mios.ps1:3368-3370 -->

### Install a wrapper at /usr/local/bin/mios-dev-seed so the...

Install a wrapper at /usr/local/bin/mios-dev-seed so the operator can
re-run the overlay manually inside the dev distro after editing
mios.toml (e.g. `wsl -d podman-MiOS-DEV -- sudo mios-dev-seed`).

<!-- mios-src:98885466ea32 from build-mios.ps1:3403-3405 -->

### Materialize the script + a copy of mios.toml inside the...

Materialize the script + a copy of mios.toml inside the distro
via stdin; avoids cross-FS quoting headaches and works for both
/mnt/c-mounted paths and rootful machines.
CRLF -> LF: PowerShell @'...'@ here-strings produce CRLF on
Windows; without normalization the bash shebang becomes
"#!/usr/bin/env bash\r" -> "env: 'bash\r': No such file or
directory" -> the entire overlay silently no-ops on the dev VM.

<!-- mios-src:913f7bc40689 from build-mios.ps1:3424-3430 -->

### Mirror the MiOS FHS overlay (Quadlets, systemd units...

Mirror the MiOS FHS overlay (Quadlets, systemd units, sysusers,
tmpfiles, libexec, profile.d, /etc/mios config templates) onto the
dev distro so MiOS-DEV runs the same container surface as a deployed
MiOS host. After this:
  - Podman Desktop (Windows) sees mios-cockpit-link, mios-forge, etc.
    under the MiOS-DEV machine connection -- each carries
    io.podman_desktop.openInBrowser labels for one-click access.
  - Cockpit on the dev VM (https://localhost:9090, mirrored networking)
    renders the same containers + system services as a deployed host.

Idempotent via /var/lib/mios/.quadlet-overlay-seeded; re-runs are no-ops
unless the source mios.git Containerfile has been touched since the
sentinel. Set MIOS_SKIP_DEV_QUADLETS=1 to bypass entirely.

<!-- mios-src:47343ab389ac from build-mios.ps1:3446-3458 -->

### NOTE

NOTE: an earlier version of this function early-returned here based
on podman machine inspect.Rootful, on the theory that rootful
machine-os distros aren't wsl.exe-accessible. Modern WSL handles
rootful machine-os fine and the contract `MiOS-DEV ≡ MiOS` requires
the dev VM to have the same Quadlets / containers / units as a
deployed MiOS host AS EARLY AS POSSIBLE -- not deferred to the OCI
build phase. Letting the wsl.exe probe below decide gates the
overlay on actual capability rather than an a-priori assumption.
(The OCI build path still re-applies the overlay later via the
baked-in image; if the install-time overlay succeeds, it's a no-op
post-bootc-switch via the sentinel check.)

<!-- mios-src:2c1942fb557b from build-mios.ps1:3466-3476 -->

### Probe wsl.exe with a hard timeout. Rootful machine-os...

Probe wsl.exe with a hard timeout. Rootful machine-os distros
are NOT wsl.exe-accessible, and `wsl.exe --exec` on them hangs
indefinitely instead of erroring -- which made the build freeze
at "Overlaying MiOS Quadlets + systemd units" with no progress.
8-second timeout per candidate; if both time out, the overlay
is deferred (matches the rootful-machine-os documented behavior).

<!-- mios-src:bab3afc6cdbb from build-mios.ps1:3485-3490 -->

### PROJECT INVARIANT

PROJECT INVARIANT: MiOS treats the deployed root `/` AS the git
working tree of mios.git on EVERY deploy shape -- bare-metal,
Hyper-V, QEMU, WSL distro, AND the Windows-side podman-WSL2 dev VM.
`git init` at `/`, point origin at the cloned mios.git checkout
(later swappable to the self-hosted Forgejo at localhost:3000),
`fetch + reset --hard`, and now every mios.git tracked file is at
its FHS path on `/` in one operation -- no tar-list to maintain,
no missing-file bugs, full parity with the deployed system.

Safety: `git reset --hard FETCH_HEAD` only touches FILES TRACKED
IN mios.git. Untracked Fedora-base paths (/etc/passwd, /var/lib/
dnf, ~/.bash_history, /var/log, etc.) are left alone -- they are
not in mios.git and git's reset doesn't enumerate them. The repo's
root .gitignore further declares which `/etc/*`, `/var/*`, etc.
subtrees stay host-managed.

<!-- mios-src:2c50a9fcdbbc from build-mios.ps1:3557-3571 -->

### ── Universal mios.git overlay sync...

── Universal mios.git overlay sync ──────────────────────────────────────────
Works identically across every MiOS deploy shape:
  - Bare-metal bootc (mios:latest deployed)
  - Hyper-V VHDX / QEMU qcow2 / RAW disk image
  - WSL2/g distros (mios:latest imported via wsl --import)
  - Podman-WSL dev VM (the canonical podman-MiOS-DEV pre-bootc-switch)
  - Podman / Podman Desktop (Windows + Linux native)
  - Traditional FHS installs (mios.git overlaid into / via install.sh)

Architectural Law 3 ".git IS /": the deployed root is always a git
working tree of mios.git. This sync brings / up to origin/main using
the FASTEST available source given the deploy context.

Per WSL filesystem-performance guidance
(learn.microsoft.com/en-us/windows/wsl/filesystems):
  "For the fastest performance speed, store your files in the WSL
   file system if you are working in a Linux command line."
So all git operations target a NATIVE-ext4 bare-clone cache at
$CACHE_DIR; /mnt/m (DrvFs / 9P) is only ever consulted as a one-shot
offline-bootstrap source for the cache itself.

<!-- mios-src:5a164b94c9f1 from build-mios.ps1:3573-3592 -->

### Statically enable mios-ai-firstboot via a .wants symlink...

Statically enable mios-ai-firstboot via a .wants symlink rather than
`systemctl enable --now`. During the overlay the VM's system bus is
transitional ("Transport endpoint is not connected"), so enable --now for
this long-running oneshot fails; a symlink is D-Bus-independent and lets the
firstboot run on the FIRST CLEAN BOOT, when the bus + ollama are up. It
self-heals (sentinel only on full success) and builds the venv + GGUFs there.

<!-- mios-src:ffbd9ec7d2f2 from build-mios.ps1:3701-3706 -->

### Globally enable the OPERATOR-side launcher broker...

Globally enable the OPERATOR-side launcher broker (mios-launcher.service, a
USER unit) the same D-Bus-independent way: a .wants symlink in the GLOBAL
user target dir so the operator's user manager starts it (ConditionUser=mios
gates it to that user). Without this the broker ships DISABLED -> the socket
/run/mios-launcher/launcher.sock is never created -> EVERY OS-control verb
(open_app, etc.) fails "broker socket missing" and the agent cannot drive
Windows/Linux apps ("open notepad" -> "LIAR"). The broker
is what lets MiOS AI actually control the OS. install-robustness.

<!-- mios-src:980530ad6404 from build-mios.ps1:3712-3719 -->

### Top-of-root SSOT shortcuts

Top-of-root SSOT shortcuts: mios.toml + configurator HTML at /
so operators can `cat /mios.toml` and open `file:///configurator.html`
from the dev VM browser. The deployed root IS the git working tree
of mios.git, so these symlinks live in the same view as /.git --
the operator's "single source of truth" surface is one cd / away.

<!-- mios-src:cfa674036243 from build-mios.ps1:3737-3741 -->

### Render Quadlet ${MIOS_*} placeholders BEFORE systemd's...

Render Quadlet ${MIOS_*} placeholders BEFORE systemd's podman
generator runs at daemon-reload. The .container files at
/etc/containers/systemd/*.container ship raw `${VAR:-default}`
placeholders (Image=, PublishPort=, User=, Group=, Network=, ...);
systemd's Quadlet generator does NOT expand them, so podman gets
the literal string `${MIOS_PORT_LLM_LIGHT` (split on the `:` of
`:-8450`) and dies with:
    Error: cannot parse "${MIOS_PORT_LLM_LIGHT" as an IP address
Every Quadlet stays in `activating auto-restart` and `podman ps`
is empty. Operator-flagged (containers all dead after
install).

automation/34-render-quadlets.sh walks the four Quadlet search
dirs, resolves the placeholders against the layered mios.toml
(vendor < host < user) via tools/lib/userenv.sh, and writes the
rendered files back in place. The deployed bootc image builds run
this at image-build time; the dev-VM overlay path does NOT, so
we run it here. Idempotent: re-runs against an already-rendered
.container are a no-op (envsubst sees no remaining placeholders).
install-robustness the dev-VM overlay never ran 59-tools.sh
(which deploys tools/lib/userenv.sh -> /usr/lib/mios/userenv.sh, the env-bridge
resolver) NOR mios-sync-env -- so /etc/mios/install.env was never generated,
leaving the AI plane INERT on a fresh install: empty bake_models -> no GGUFs ->
mios-llm-light skipped, and unresolved MIOS_PORT_* templates -> agent-pipe 502.
Deploy the resolver + generate the bridge HERE so 15-render-quadlets below AND
the firstboot services (EnvironmentFile=/etc/mios/install.env) see resolved
values. Both idempotent; LIVE-verified this is the keystone that brought a
fresh dev VM's MiOS AI fully operational on the GPU.

<!-- mios-src:aa73e4728910 from build-mios.ps1:3746-3773 -->

### Realize sysusers + tmpfiles, then reload systemd so the new...

Realize sysusers + tmpfiles, then reload systemd so the new units
(and Quadlet-generated *.service files) are visible.

Critical: `wsl --exec` lands in the OUTER WSL namespace, not the
nested process namespace where systemd actually runs (per the
podman-machine welcome banner). Bare `systemctl daemon-reload`
from this context fails with "Failed to set unit properties:
Transport endpoint is not connected" / "Reload daemon failed".
nsenter into systemd's PID with -a (all namespaces) gives the same
view an interactive `wsl -d <distro>` session has, so systemctl
reaches its bus and units register correctly.

<!-- mios-src:7acdd37cbaf1 from build-mios.ps1:3792-3802 -->

### Set MiOS-DEV's default WSL2 user to mios (sysusers just...

Set MiOS-DEV's default WSL2 user to mios (sysusers just created uid
1000=mios above). Without this, `wsl -d podman-MiOS-DEV` lands on
whatever the machine-os tarball seeded as default (typically a bare
`user` UID 1000, which exists but has none of the mios HOME / shell
/ groups setup). /etc/wsl.conf is read once at distro start, so the
next `wsl --terminate podman-MiOS-DEV` + reentry picks this up.
Idempotent: only ADDS [user] block if not already present.

<!-- mios-src:0d0b048a2fd2 from build-mios.ps1:3817-3823 -->

### [boot].systemd=true is REQUIRED for `systemctl...

[boot].systemd=true is REQUIRED for `systemctl is-system-running`,
Quadlet generators, mios-flatpak-install.service, and every other
systemd-coupled feature inside the WSL distro. Without it, WSL boots
without systemd as PID 1; smoke tests then see state='offline' and
the build pipeline can't poll service state. WSL >= 0.67.6 honors
this directive on next `wsl --terminate` + reentry.

<!-- mios-src:badef5535588 from build-mios.ps1:3825-3830 -->

### Container-host prerequisites for the mios user. Manifesto...

Container-host prerequisites for the mios user. Manifesto says MiOS-DEV
"should have the mios user appended as it will be needed for this MiOS-DEV
machine to host its containers (mirroring the layered containers in MiOS
at build time; guacamole, ollama, forgejo, cockpit etc-etc)". The
systemd-sysusers run above creates the mios login user (uid 1000); the
three steps below complete the container-hosting plumbing:

  1. subuid/subgid append -- rootless podman needs an unprivileged uid
     range available for user-namespace mapping. Standard convention is
     one 64K-uid range starting at 524288 (well outside the host's
     regular uid space). Idempotent: skip if mios is already present.

  2. linger enable -- so systemd --user services (the Quadlets) start
     at boot without an active interactive login session. Required for
     `systemctl --user enable mios-forge.service` etc. to actually
     launch the daemon at boot rather than waiting for a TTY login.

  3. /var/home/mios skeleton seeded from /etc/skel -- FCOS / atomic-
     desktops home convention; the deployed MiOS image uses
     /var/home/<user> as $HOME so /etc 3-way merge doesn't have to
     manage home-dir state. Establish the same on MiOS-DEV so any
     operator-side configs (.bashrc, .config/) match across substrates.

<!-- mios-src:0165f2149e56 from build-mios.ps1:3862-3883 -->

### Idempotent

Idempotent: `cp -an` (no-clobber) copies entries that are
MISSING in /var/home/mios without overwriting operator-edited
dotfiles. Previous guard (only-on-first-boot via missing
.bashrc) prevented newly-added skel entries (XDG user-dir tree,
user-dirs.dirs) from propagating to existing users on
`mios update`. Switched to per-file no-clobber so re-runs are
safe AND new skel content reaches existing users.
`cp -a` instead of rsync -- podman-machine-os 6.0 base does
NOT ship rsync, so the prior rsync call silently no-op'd.
Operator-flagged.

<!-- mios-src:f11f494c32a0 from build-mios.ps1:3902-3911 -->

### Expose flatpak .desktop entries to WSLg's auto-publisher....

Expose flatpak .desktop entries to WSLg's auto-publisher. WSLg scans
/usr/share/applications/ + ~/.local/share/applications/ on each
distro start and creates Windows Start Menu shortcuts under
%APPDATA%\Microsoft\Windows\Start Menu\Programs\<distro>\<App>
(on <distro>).lnk -- WITH the app's real icon and no terminal popup.
Flatpak installs its entries to /var/lib/flatpak/exports/share/
applications/ which WSLg does NOT scan, so symlink each into the
WSLg-watched dir. Operator-flagged flatpak apps weren't
in Start Menu STILL after the custom Linux Apps shortcuts were
fixed -- WSLg's quality (icons + no terminal) is the canonical
user expectation, our custom .lnks are a fallback only.

<!-- mios-src:e9fa06fa2287 from build-mios.ps1:3918-3928 -->

### ALWAYS-ON LIGHTWEIGHT SET

ALWAYS-ON LIGHTWEIGHT SET: Cockpit (web console at :9090), the
Podman-Desktop discovery shim that surfaces MiOS containers in PD's
UI, and the self-hosted Forgejo forge (small SQLite-backed git host).
Plus NVIDIA CDI plumbing (mios-cdi-detect + nvidia-cdi-refresh) so
Podman containers on MiOS-DEV can claim /dev/dxg (WSL2 GPU surface)
via the same Container Device Interface spec a deployed bare-metal
MiOS host uses. mios-cdi-detect.service auto-no-ops when no GPU is
present (no /dev/nvidia0 / no /dev/dxg) and explicitly passes
--mode=wsl to `nvidia-ctk cdi generate` when systemd-detect-virt
reports wsl, so it works correctly on the dev VM out of the box.
Each enable is best-effort -- a unit that ConditionVirtualization-skips
itself just no-ops with status=inactive (success).
Quadlet-generated *.service files (from etc/containers/systemd/*.container)
live at /run/systemd/generator/ and are AUTO-WANTED via the [Install]
section Quadlet's generator already processed at daemon-reload time.
`systemctl enable` on them errors with "transient or generated" -- use
`start` instead. Native systemd units (cockpit.socket, mios-cdi-detect,
nvidia-cdi-refresh.path) take the standard `enable --now` path.

mios-ai-firstboot.service is DELIBERATELY EXCLUDED from this set: it is a
long-running oneshot (builds the AI venv + pulls GGUFs) that MUST run on the
FIRST CLEAN BOOT, not during the overlay. `enable --now` on it synchronously
starts + WAITS for that firstboot, blocking the whole install indefinitely on
the transitional system bus ("Transport endpoint is not connected"). It is
already enabled the D-Bus-independent way via the .wants symlink above (see
"Statically enable mios-ai-firstboot"). Do NOT re-add it here.

<!-- mios-src:0abf39da9927 from build-mios.ps1:3941-3966 -->

### "now to finally fix none of the containers existing or...

"now to finally fix none of the containers
existing or properly launching on boot.. in podman-MiOS-DEV".
Plus: "bake into mios.toml so operators can edit the list --
EVERYTHING is sourced from the mios.toml file and edited in the
mios.html in live environments browser".

Quadlet-generated services have [Install] WantedBy=multi-user.target
in their .container files, so they SHOULD auto-start at boot. On the
WSL podman-machine substrate the dependency chain doesn't reliably
fire for every service -- explicit `systemctl start --no-block` is
the fix. --no-block returns immediately so overlay doesn't wait on
multi-GB image pulls; each Quadlet's Restart=on-failure handles the
retry.

Both lists are TOML-sourced: mios-bootstrap/mios.toml
[containers.quadlets].autostart + .optin. Operators edit via
mios.html in the browser; build-mios.ps1's PowerShell side reads
these on every overlay pass and substitutes them here. The
PowerShell-side substitution replaces __MIOS_QUADLET_AUTOSTART__
and __MIOS_QUADLET_OPTIN__ with literal bash-array entries.

<!-- mios-src:1cdd5f5b4116 from build-mios.ps1:3969-3988 -->

### Install the operator-facing terminal flatpak so MiOS-DEV...

Install the operator-facing terminal flatpak so MiOS-DEV mirrors a
deployed MiOS host's UX: open Ptyxis on the Windows desktop via WSLg
-> default tab spawns into the host shell via flatpak-spawn --host
-> the operator types `mios "..."` and hits the local AI plane on
:8640 directly. Idempotent (--or-update). Also pulls the few other
substrate-class flatpaks (Nautilus, Bazaar, Flatseal) so the
emulated MiOS environment carries its file manager and app store.
Run the same canonical automation scripts the build pipeline uses,
now that `/` IS mios.git's working tree. One install path, no
parallel fetch logic to drift. Each script is best-effort
(rc != 0 doesn't kill the overlay) and self-skips when the relevant
binary already exists.

56-fonts.sh         Geist (Vercel) + Symbols-Only Nerd Font
62-oh-my-posh.sh    Oh-My-Posh static binary -> /usr/bin/oh-my-posh

<!-- mios-src:6b6cb0367c1a from build-mios.ps1:4030-4044 -->

### Flatpak here runs as ROOT (uid 0), but WSLg exports...

Flatpak here runs as ROOT (uid 0), but WSLg exports XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir owned
by uid 1000 -> dbus refuses ("runtime dir owned by uid 1000, not our uid 0") and spams that on
EVERY system-wide install/remote op. Give root its OWN runtime dir + drop the inherited session
bus so all `sudo flatpak --system` calls below are quiet + correct. sudo propagates XDG_RUNTIME_DIR
(that is how the uid-1000 path leaked in), so exporting the root path here reaches the child.

<!-- mios-src:6a1e72573893 from build-mios.ps1:4058-4062 -->

### Two flatpak remotes

Two flatpak remotes:
  flathub -- community / third-party flatpaks (Flatseal, VSCodium, etc.)
  fedora  -- Fedora's own flatpak registry, ships CURRENT GNOME apps
             built against the current libadwaita runtime. Critical for
             Nautilus + Epiphany because Flathub's versions are EOL
             (pinned to GNOME 3.28 runtime, years out of date) which
             gives operators the "old GTK / CSS / decorations" look.

<!-- mios-src:0bbfd5c58fa4 from build-mios.ps1:4067-4073 -->

### Substrate-class Flatpaks

Substrate-class Flatpaks: terminal (Ptyxis), file manager (Nautilus
from fedora), Flatpak permissions UI (Flatseal), default browser
(Epiphany from fedora), GNOME shell extensions, VSCodium. Each
routes through WSLg as a Windows desktop window; the
gnome-flatpak-runtime RPM section provides the host-side
portals/audio/theming these need to render correctly.

Entries with a "fedora:" prefix install from the fedora remote
(current libadwaita / GNOME 50.x); plain entries install from
flathub. Operator directive "just enable newer fedora
repos for the flatpaks" / "you hard coded an old version of gnome
files flatpak -- THAT'S why it's old looking!!"

<!-- mios-src:d763317befde from build-mios.ps1:4098-4109 -->

### Drop a /usr/local/bin/<short> wrapper so operators can run...

Drop a /usr/local/bin/<short> wrapper so operators can run
`nautilus`, `epiphany`, `ptyxis` directly instead of the
`flatpak run org.gnome.<App>` long form. /var/lib/flatpak/exports/
bin already publishes the AppID-named symlink; this adds the
short alias on top.

The wrapper delegates to /usr/libexec/mios/flatpak-launch, which
restores the WSLg / Wayland / X11 / PulseAudio / D-Bus environment
whenever the parent shell stripped it (`su -`, `nsenter -m`, sudo
without -E, systemd-run, cron). Login shells under WSL pick those
vars up via /etc/profile.d/mios-wslg.sh, but a `bash -c 'nautilus'`
from a non-login context bypasses profile.d entirely -- which was
the failure mode the operator hit when `epiphany` errored with
"Cannot autolaunch D-Bus without X11 \$DISPLAY" after `su - mios`
under nsenter. The helper is idempotent: it only sets variables
that are unset, so a bare-metal GNOME session that already has a
working environment passes straight through.

If /usr/libexec/mios/flatpak-launch is absent (older deployment
before this fix landed), fall back to the original direct-exec
form so the wrapper still launches the flatpak -- it just won't
benefit from the env restore.
Look up short alias by the ORIGINAL key (with potential remote: prefix).

<!-- mios-src:7e6bc0d1e79a from build-mios.ps1:4155-4177 -->

### Regenerate the shim if it's missing OR if it doesn't...

Regenerate the shim if it's missing OR if it doesn't reference
the flatpak-launch helper -- a previous bootstrap run before the
WSLg-env-restore fix landed produced shims that just `exec flatpak
run`, and those leave the operator with silent-window-failures
whenever they invoke the shim from a non-login shell. The grep
below makes the regeneration idempotent: re-runs are no-ops once
the shim already points at the helper.

<!-- mios-src:8b0b57c14952 from build-mios.ps1:4179-4185 -->

### Passwordless sudo for the dev VM's regular user account...

Passwordless sudo for the dev VM's regular user account (uid 1000)
so `sudo -u mios -i` and similar account-switch commands work without
the mios user having a password set. /etc/sudoers.d/00-mios-dev is
installed mode 0440 (the only mode sudoers.d will load) and has
both the dev `user` account and the canonical `mios` account in the
wheel-equivalent set.

<!-- mios-src:7ad06727356d from build-mios.ps1:4203-4208 -->

### Default dev passwords for both `user` (uid 1000) and `mios`...

Default dev passwords for both `user` (uid 1000) and `mios` (uid >=1000
system user from sysusers.d) so Cockpit's PAM auth at https://localhost:
9090/ works without manual passwd setup. The MiOS dashboard prints these
credentials inline next to the Cockpit endpoint so the operator doesn't
have to remember them. Single-tenant dev VM trust model -- documented
on the dashboard, never used outside the dev surface.

Placeholder __MIOS_LOGIN_PASSWORD__ is substituted at heredoc-bake
time by Invoke-MiosQuadletOverlay from mios.toml [auth].password
(SSOT, operator-editable via mios.html). Vendor default is 'mios'.
DO NOT inline 'mios' here -- the substitution pass is what makes
the toml the single source of truth.

<!-- mios-src:e7fa6145e69e from build-mios.ps1:4226-4237 -->

### Verify

Verify: drive `su - mios -c id` through a pty so we can actually
type the password. If this succeeds, Cockpit's PAM stack (which
uses the same /etc/shadow lookup) will accept the same credential.
Operator-flagged dashboard said `mios / mios` but the
Cockpit login rejected those credentials because an earlier chpasswd
silently set the hash to something else (likely a CRLF leak from a
prior PowerShell heredoc, since fixed). The verify step catches a
silent failure here instead of letting the operator hit it at login.

<!-- mios-src:3dd07e48fff9 from build-mios.ps1:4246-4253 -->

### ── Layer the FULL mios.toml [packages].sections set into...

── Layer the FULL mios.toml [packages].sections set into MiOS-DEV ───────
Per feedback_mios_dev_equals_mios.md and the directive
"MIOS MUST CONTAIN EVERYTHING NEEDED TO SELF; dev, build, run, host,
hosting, etc-etc TOML/HTML SHOULD BOTH REFLECT EACHOTHER AND DICTATE
ANY AND ALL MIOS DEPLOYMENTS AND ENTRIES INCLUDING DEPLOYING MIOS DEV":
the same package set that lands in a deployed MiOS host must land in
MiOS-DEV at Phase 3 time, NOT deferred to mios-build-driver. Operator
expects `just`, `btop`, `fastfetch`, `ripgrep`, etc. to be available
the moment they enter the dev distro.

Approach: parse /usr/share/mios/mios.toml [packages].sections (master
inclusion list, configurator-controlled), filter by per-section
.enable, dedupe pkgs, layer them via `rpm-ostree install` (machine-os
is FCOS-based + ostree-managed; rpm-ostree is the canonical layered-
package mechanism). --idempotent skips already-installed, --allow-
inactive doesn't fail when a layered package's services can't start
yet (e.g. needs reboot or kernel module not in WSL kernel).

Best-effort: a non-zero rpm-ostree exit doesn't abort the seed. The
dashboard MOTD's `untracked 28` cosmetic note is unrelated and
unaffected.

<!-- mios-src:870d27a5e6ed from build-mios.ps1:4286-4306 -->

### Pure-awk TOML parser. machine-os 6.0's stripped FCOS base...

Pure-awk TOML parser. machine-os 6.0's stripped FCOS base often
ships without python3, so the previous tomllib-based approach
silently skipped (visible in the 19:24 log as "WARN: rpm-ostree
or python3 not available"). Awk is in coreutils-equivalents on
every Linux base.

Two-stage parse:
  1. Read [packages].sections array -> the master inclusion list.
  2. For each section name, read [packages.<name>].pkgs IF
     [packages.<name>].enable != false. Append to the global
     package list.
Output: deduped space-separated package names on stdout.

<!-- mios-src:f41e9237a3e8 from build-mios.ps1:4319-4330 -->

### Re-resolve the systemd PID NOW. The dnf transaction we just...

Re-resolve the systemd PID NOW. The dnf transaction we just ran
upgraded the `systemd` RPM (a transitive dep of dozens of the 297
packages in mios.toml). On WSL2's nested-systemd-in-WSL the new
binary respawns inside the user namespace and PID 1's PID number
changes -- so the $NS we captured at overlay start (line ~3658)
points at a /proc/<old-pid> entry that no longer exists. Every
subsequent `nsenter -t <old-pid> -a` then dies with:
    nsenter: stat of /proc/<old-pid>/ns/user failed: No such file
tripping the reap-on-failure trap and wiping the install.
Operator-flagged.

<!-- mios-src:c14f972423fe from build-mios.ps1:4443-4452 -->

### ── Dev-VM host networking drop-ins...

── Dev-VM host networking drop-ins ──────────────────────────────────
Operator-flagged localhost:3000 / :8888 from Windows
(and from inside the dev VM) timed out even though the containers
were `Up` per `podman ps` and bound 0.0.0.0:NNNN per `ss -tlnp`.
Root cause: netavark was installed at /usr/libexec/podman/netavark
but failed to install its per-container DNAT chain in the nat table
(probably due to firewall_driver=iptables vs iptables-nft +
nftables-only ruleset on the podman-machine-os base). conmon's host
proxy listener accepted TCP but had no DNAT rule to forward to the
container netns -> HTTP request hangs.

Workaround that actually works on the dev VM: Network=host. The
container shares the VM's main netns, listens directly on
0.0.0.0:NNNN, and wslrelay (Windows-side) picks up the listener via
/proc/net/tcp scanning + forwards Windows localhost:NNNN -> VM port.
This is the standard practice for single-tenant dev VMs.

The deployed MiOS image (real Fedora bootc) doesn't have this
problem -- netavark is wired through systemd-networkd and the
firewall driver matches the host firewall backend. So the drop-ins
below ONLY land on the dev VM (their parent units are guarded by
the existing overlay flow, which only runs in podman-MiOS-DEV).

Per-container env overrides for host-network mode. In host netns,
every container shares the VM's main netns -- so bind ports collide
AND inter-container DNS (e.g. mios-hermes resolution) no longer
works (no aardvark; bridge networks aren't used). Override each
image's bind/upstream env vars to talk over localhost on the
canonical MiOS port from mios.toml [ports].*. Discovered live
while shaking out the operator's first install.

  ollama: HOME=/var/lib/ollama -- without this ollama tries to
      mkdir /.ollama in the read-only container root and dies with
      "permission denied". The Quadlet already mounts /var/lib/ollama
      (writable for UID 815), so point HOME at it.
  webui:  WEBUI_SECRET_KEY=<random> (env.py:611 requires non-empty
      when WEBUI_AUTH=true), PORT=3030, OPENAI_API_BASE_URL=
      http://localhost:8642/v1 (mios-hermes:8642 doesn't resolve in
      host netns; use localhost instead).
  hermes: PORT=8642 (otherwise picks an upstream default).
  searxng: BIND_ADDRESS=0.0.0.0:8888 (granian default is :8080 which
      collides with mios-ai).
Hermes-Agent on the dev VM uses host networking, so the
container-name DNS that the vendor /etc/mios/hermes/config.yaml
relies on (mios-ollama, mios-ai, mios-searxng) does NOT resolve.
Drop a config.local.yaml that overrides each base_url to talk over
the VM's loopback instead. The vendor config has a trailing
`include: /etc/hermes/config.local.yaml` so this auto-merges on
top without touching the upstream file.

<!-- mios-src:f5ec6db058c5 from build-mios.ps1:4462-4510 -->

### MiOS-DEV is a WSL2 podman machine -- bridge networking +...

MiOS-DEV is a WSL2 podman machine -- bridge networking + PublishPort
on this substrate binds container-loopback (127.0.0.1) on the WSL VM
side, which the Windows-side netsh portproxy (0.0.0.0 -> WSL-VM-eth0-IP)
can't reach. Network=host makes each container bind the WSL VM's real
eth0 + loopback directly, so wslrelay relays loopback->Windows-host
localhost AND the portproxy relays eth0->LAN.

Architecture /14 (operator-directed):
  * hermes-agent: DIRECT host install (automation/38 + hermes-agent.
    service) -- NOT a container, so it gets NO dropin here.
  * mios-hermes + mios-hermes-dashboard: container Quadlets SHELVED
    ([quadlets.enable]=false) -- dropped from this list.
  * mios-hermes-workspace: REMOVED entirely -- dropped.
  * mios-open-webui: the chat UI. Its container listens on 8080
    internally (parent Quadlet remapped host:3030->container:8080 via
    PublishPort). Under host-net PublishPort is a no-op, so it MUST
    get PORT=3030 or it binds 8080 and collides with mios-code-server
("[Errno 98] address already in use" -- operator-confirmed).
  * Bind addresses: 0.0.0.0 everywhere (NOT 127.0.0.1). The old
    "127.0.0.1 forces AF_INET for localhostForwarding" theory is
    superseded -- the portproxy->WSL-VM-IP path needs eth0 binds.

<!-- mios-src:f87a5689aa4a from build-mios.ps1:4551-4571 -->

### Open the MiOS service ports in the dev VM's firewalld. The...

Open the MiOS service ports in the dev VM's firewalld. The deployed
bootc image runs automation/44-firewall-ports.sh at OCI build time
(firewall-offline-cmd), but the MiOS-DEV overlay path does NOT go
through an image build -- it's provisioned from podman-machine-os
(firewalld active, public zone: only ssh/mdns/dhcpv6) and overlaid.
Without this, every MiOS port is dropped on eth0 -- services bind but
are unreachable from the WSL-VM-IP, so the Windows-side portproxy
(0.0.0.0 -> WSL-VM-IP) hits a closed door (operator-confirmed
LAN access dead until firewalld was opened by hand).
firewall-cmd (online) here mirrors what 44-firewall-ports.sh bakes
offline. Tolerant: no-op if firewalld isn't running.

<!-- mios-src:3e71b77696d3 from build-mios.ps1:4598-4608 -->

### Use $NS (nsenter into systemd's namespace) instead of bare...

Use $NS (nsenter into systemd's namespace) instead of bare `sudo` so
the reload reaches the running PID 1's bus. Bare `sudo systemctl
daemon-reload` runs in the OUTER WSL ns and gets "Transport endpoint
is not connected" -- same root cause as the early-overlay daemon-
reload that already routes through $NS. Operator-flagged
the bare-sudo call here tripped the reap-on-failure trap and wiped
their install after a 9-minute Phase-3 build.

<!-- mios-src:5a4b838ae423 from build-mios.ps1:4620-4626 -->

### Apply the MiOS systemd-preset so cockpit.socket / pmcd /...

Apply the MiOS systemd-preset so cockpit.socket / pmcd / pmlogger /
pmproxy and other MiOS-preset-enabled units land at enabled=enabled
on the dev VM. The deployed bootc image processes presets at image-
build time; the dev-VM overlay path does NOT, so without this every
preset-`enable`d unit stays at upstream Fedora's `disabled` default.
Operator-flagged cockpit metrics page showed "pmlogger.
service is not running" because PCP units were stuck disabled. The
preset is the SSOT for "what should be on by default"; applying it
here keeps the dev VM behavior identical to the deployed image.

<!-- mios-src:333b0c42578a from build-mios.ps1:4629-4637 -->

### Mask dev-VM-hostile services. These are baked into mios.git...

Mask dev-VM-hostile services. These are baked into mios.git for the
bare-metal bootc image but cannot work in podman-machine-os WSL:
  * audit-rules / auditd       -- WSL2 kernel has no audit subsystem
  * fapolicyd                  -- needs kernel fanotify FAN_REPORT_FID
  * usbguard                   -- no USB devices in WSL
  * bootloader-update          -- no bootloader on WSL distros
  * greenboot-healthcheck      -- bootc-specific rollback machinery
  * mios-aichat-build          -- builds a Distrobox image that doesn't
                                  apply on dev VM (used on bare metal)
  * mios-wslg-permissions-fix  -- chmod /mnt/wslg fires before WSLg is
                                  mounted on this machine-os build;
                                  harmless to mask, Quadlets handle
                                  /tmp/.X11-unix via /etc/profile.d.
  * mios-wsl-init              -- the legacy first-boot init shim;
                                  superseded by mios-cdi-detect +
                                  mios-wsl-runtime-dir on the dev VM.
Each shows up as "Failed to start" in cockpit's Services panel
otherwise, which is operator-visible noise that suggests the
install is broken. Masking is idempotent and reversible
(systemctl unmask <unit>). Operator-flagged.

<!-- mios-src:c8ef50375cdc from build-mios.ps1:4650-4669 -->

### Quadlet autostart / opt-in lists -- SSOT

Quadlet autostart / opt-in lists -- SSOT: mios.toml
[containers.quadlets]. Operator-editable via mios.html. The
bash heredoc has __MIOS_QUADLET_AUTOSTART__ /
__MIOS_QUADLET_OPTIN__ placeholders; resolve them here against
the layered TOML cascade and substitute as literal bash array
entries. Vendor default is the workstation-core set (cockpit-
link + forge + searxng + webui + ai + ollama). Operator opt-in
services land in the .optin list (per mios.toml).
Operator directive 'forget open webui for now -- Ollama
>> hermes agent >> hermes-workspace app is the front-end'. Swap
mios-webui out, swap mios-hermes + mios-hermes-workspace in.

<!-- mios-src:ef7e9bf82fa3 from build-mios.ps1:4688-4698 -->

### MIOS_FIREWALL_PORTS__ -- dev-VM firewalld open-port list...

__MIOS_FIREWALL_PORTS__ -- dev-VM firewalld open-port list for the
quadlet overlay. Service ports flow from the [ports] SSOT (operator
override-aware); the infra ports (ssh, forgejo-ssh, qdrant grpc/http,
hermes-dashboard, metrics) are not operator-tunable [ports] service
keys so they carry vendor defaults here. Mirrors the offline
44-firewall-ports.sh surface baked into the OCI image.

<!-- mios-src:6533e0c3f730 from build-mios.ps1:4715-4720 -->

### MIOS_LOGIN_PASSWORD__ -- the operator-facing dev-VM login...

__MIOS_LOGIN_PASSWORD__ -- the operator-facing dev-VM login (also
the credential Cockpit web at https://localhost:9090/ accepts).
SSOT: mios.toml [auth].password (plain) or [auth].password_hash
(pre-hashed for hardened deploys). Default 'mios' if both blank.
The dashboard banner shows the literal string, so resolving it
from the same place the chpasswd line consumes guarantees the
advertised credential is the actual credential.

<!-- mios-src:b868732ed783 from build-mios.ps1:4763-4769 -->

### Stage the seed to a file on M:\ instead of base64-inlining...

Stage the seed to a file on M:\ instead of base64-inlining it
through `bash -c`. f67e5ad (rpm-ostree install + python3 toml
parse) pushed the seed past Windows' CreateProcess arg-length
cap (~32K), and `wsl.exe -d <distro> --exec bash -c $stage`
died with "FATAL: Program 'wsl.exe' failed to run: The
filename or extension is too long" before the seed could even
touch the distro. Writing to a file + invoking by path keeps
the command line tiny.

<!-- mios-src:268270b07b30 from build-mios.ps1:4782-4789 -->

### DEPRECATED

============================================================================
DEPRECATED: Invoke-WindowsPodmanBuild
----------------------------------------------------------------------------
This function (and its sibling helpers Invoke-WslBuild,
Invoke-DeployPipeline, New-MiosHyperVVm below) belongs to the
pre-self-replication architecture where Windows ran `podman build`
directly. As of v0.2.4 (memory: feedback_mios_dev_is_the_builder)
the dev VM IS the builder; Windows is provisioning + handoff ONLY.
All Phase 9 Build paths run inside MiOS-DEV via mios-build-driver,
triggered by the `mios build` verb (M:\MiOS\bin\mios-build.ps1).

These functions are now UNREACHABLE: -BuildOnly / -FullBuild are
force-deprecated at line 202 ($BootstrapOnly = $true), and every
control-flow gate (`if ($BootstrapOnly)` returns; `if (-not
$BootstrapOnly)` blocks) routes around them.

Kept in-tree for one release cycle so git-blame still resolves the
legacy callers; a follow-up commit will delete them outright.
============================================================================

<!-- mios-src:ee84530bd427 from build-mios.ps1:4824-4842 -->

### ── Universal MiOS-SEED merge...

── Universal MiOS-SEED merge ────────────────────────────────────────────
The Phase 2 overlay (lines ~4823+) already robocopies mios-bootstrap.git
onto $MiosRepoDir, so by the time we reach podman build the bootstrap
files (etc/skel/.config/mios/, etc/mios/profile.toml, mios.toml at root,
agent entry-point .md files) are already present in the build context.
seed-merge.ps1 is kept as a defensive idempotent re-run -- if the
operator added new files to mios-bootstrap.git between Phase 2 and
this phase, they get pulled in.

<!-- mios-src:7007542f1df7 from build-mios.ps1:4851-4858 -->

### Run via cmd.exe so 2>&1 merges stderr (podman build...

Run via cmd.exe so 2>&1 merges stderr (podman build progress) into stdout stream.
Build args propagate operator selections from the Phase-6 prompts
(or layered mios.toml [ai] defaults) into the Containerfile ARGs of
the same name.

<!-- mios-src:140dd00b2b85 from build-mios.ps1:4877-4880 -->

### ── Universal MiOS-SEED merge (inside WSL distro)...

── Universal MiOS-SEED merge (inside WSL distro) ─────────────────────────
Sync-RepoToDistro brought mios.git into / via `git fetch + reset --hard`.
That path strips untracked files, so we can't pre-merge on the Windows
side -- the merge has to happen INSIDE WSL after the sync, before
`just build` invokes podman build. Clone mios-bootstrap into
/tmp/mios-bootstrap, run seed-merge.sh against /, then build.

<!-- mios-src:fc404840ef6a from build-mios.ps1:4956-4961 -->

### Note

Note: NO `set -e` here -- a transient clone failure must DEGRADE
(warn + skip the overlay) rather than abort the whole build. The
clone is wrapped in a 3x exponential-backoff retry loop so a flaky
network doesn't kill an otherwise-good build on the first failure.

<!-- mios-src:cd5ce43ebb64 from build-mios.ps1:4967-4970 -->

### Stream build output line-by-line

Stream build output line-by-line: update dashboard Step, write to log.

Quoting note: the bash script body is wrapped in OUTER double
quotes (CreateProcess-recognized) so the script body stays a
single argv element through the wsl.exe / podman.exe handoff.
The inner single quotes around $BaseImage / $AiModel are then
bash-literal quoting -- preserved verbatim because CreateProcess
treats them as ordinary characters inside the "..." block.

Earlier the script wrapped the whole thing in single quotes
(`'A=''val'' B=''val'' just build'`) which CreateProcess does
NOT recognize as quoting, so it split on the spaces between the
env-var pairs and bash got an unbalanced fragment, failing with:
  MIOS_AI_MODEL='':'-c: line 1: unexpected EOF...

<!-- mios-src:c5c1d52767f6 from build-mios.ps1:4999-5012 -->

### Pre-create the output directory on the BUILDER MACHINE...

Pre-create the output directory on the BUILDER MACHINE filesystem.
podman volume bind-mounts require the host-side path to exist before
the container starts; otherwise crun fails with `statfs ENOENT`.
CRITICAL: must run on the dev distro itself -- running `mkdir`
inside a transient alpine container only creates the dir in the
container's ephemeral fs, which evaporates before BIB starts.
Routed through Invoke-DistroSh so it works in both rename states.

<!-- mios-src:f30a5d59e7b2 from build-mios.ps1:5114-5120 -->

### Smoke-test the freshly-provisioned MiOS-DEV podman machine...

Smoke-test the freshly-provisioned MiOS-DEV podman machine before
we commit to renaming it. Verifies:
  1. wsl.exe can reach the distro (basic VM bootstrap done)
  2. systemd is running inside (services can be enabled)
  3. /usr tree has the MiOS overlay (33-mios-overlay sentinel present)
  4. podman API socket is reachable from the Windows host

Returns $true on full success, $false otherwise (caller decides
whether to abort the rename or warn-and-continue). Errors bubble
up as warnings -- does NOT throw, so a partial-overlay state
doesn't kill the bootstrap.

<!-- mios-src:1e0fb5dbd400 from build-mios.ps1:5296-5306 -->

### 1. Basic responsiveness. Retried with backoff: Phase 3's...

1. Basic responsiveness. Retried with backoff: Phase 3's wsl --shutdown
restarts the distro right before this smoke check, so the FIRST echo-ready
probe races the VM cold-start (operator-flagged smoke warned
"did not respond to echo ready" on a freshly-shutdown distro). Match the
systemd/podman probes' retry pattern. SSOT: [smoke_tests].

<!-- mios-src:5d7063a30842 from build-mios.ps1:5321-5325 -->

### 4. Podman API reachable. Skipped post-rename (podman client...

4. Podman API reachable. Skipped post-rename (podman client
speaks to the SSH socket regardless of WSL distro name).
Retried with backoff: Phase 3's wsl --terminate (added in
4a8e7f6 to make /etc/wsl.conf [user] default=mios take effect)
restarts the distro right before this smoke check runs, so
the podman API is warming up. Without retry the check fires
before the API socket is ready and emits a confusing warning.

<!-- mios-src:0763e73568c4 from build-mios.ps1:5372-5378 -->

### Same reason as systemd retry above

Same reason as systemd retry above: podman machine takes 15-30s
to warm up after wsl --terminate. Operator's 16:01 install
showed 5x2s=10s wasn't enough.
SSOT: attempts + interval resolve through mios.toml [smoke_tests].

<!-- mios-src:4967a15c2469 from build-mios.ps1:5382-5385 -->

### Run a bash snippet inside the dev distro, picking the right...

Run a bash snippet inside the dev distro, picking the right
transport based on the rename state:

  * Pre-rename (distro = "podman-MiOS-DEV"): use `podman machine
    ssh` -- works because podman's WSLDistroName() = podman-<name>.
  * Post-rename (distro = "MiOS-DEV"):       use `wsl -d MiOS-DEV`
    directly -- `podman machine ssh` here fails because podman
    hardcodes the `podman-` prefix in WSLDistroName().

Both transports base64-encode the script to avoid CRLF mangling
by stdin pipelines, then `echo BASE64 | base64 -d | bash`
decodes and pipes the script to a fresh bash via stdin (bash
auto-execs when stdin is a pipe).

Returns: the inner script's stdout. After invocation,
$LASTEXITCODE holds the inner bash exit code (set by the
native wsl.exe / podman.exe process, which propagates the
last pipeline stage).

Callers MUST NOT do `return Invoke-DistroSh ...` if they want
both stdout and exit code -- assign to a variable and check
$LASTEXITCODE separately:

    $out = Invoke-DistroSh -Bash "echo hello"
    if ($LASTEXITCODE -ne 0) { ... }

All build-pipeline call sites that previously called
`podman machine ssh $BuilderDistro -- sudo bash -c "..."`
should route through this helper so the rename is transparent.

<!-- mios-src:15c295c3ec11 from build-mios.ps1:5406-5434 -->

### Write / merge $env:USERPROFILE\.wslconfig with the keys...

Write / merge $env:USERPROFILE\.wslconfig with the keys MiOS-DEV
needs from the WSL2 utility VM:
  * networkingMode=mirrored  -- containers' 0.0.0.0:NNNN binds
    show up on Windows' loopback (and physical NICs once the
    LAN firewall rules let them through).
  * firewall=false           -- bypass Hyper-V Firewall (we don't
    ship per-port New-NetFirewallHyperVRule rules).
  * dnsTunneling=true        -- VM DNS matches Windows-native.
  * autoProxy=true           -- inherit Windows proxy settings.
  * guiApplications=true     -- WSLg compositor for flatpaks.
  * memory/processors/swap   -- right-sized for the detected host.

CRITICAL: must run BEFORE Phase 3 initializes the dev VM. WSL2
reads .wslconfig at WSL2-utility-VM-START, so if we write it
AFTER podman-machine-init has spawned the VM, the VM keeps its
boot-time settings (legacy NAT mode) until the next `wsl --
shutdown`. Symptom the operator hit cockpit + every
other port timed out from Windows because the dev VM came up
in NAT mode while .wslconfig (set in Phase 4) said mirrored.
Idempotent: re-invoking from Phase 4 sees the same key set and
writes nothing new.

<!-- mios-src:4bfc7057e0ac from build-mios.ps1:5469-5489 -->

### Networking

Networking: NAT + localhostForwarding (NOT mirrored). MS labels
mirrored as "beta" and operator confirmed on Windows
build 28020 (Canary): mirrored sets up the VM IP correctly
(vm-side `ip addr` shows Windows' Wi-Fi + Tailscale IPs), but
the documented localhost-forwarding silently breaks -- every
container port times out from Windows. NAT mode + the legacy
localhostForwarding=true bridge is what reliably forwards
0.0.0.0:NNNN binds inside the VM to Windows' loopback. LAN-side
access from phone/other devices is then handled by the Windows
Firewall rules + netsh portproxy (added by Set-MiosLanFirewall
Rules + Set-MiosLanPortProxy in Phase 4).

<!-- mios-src:269a0aa11146 from build-mios.ps1:5493-5503 -->

### `firewall` is mirrored-mode-specific and useless in NAT...

`firewall` is mirrored-mode-specific and useless in NAT mode;
strip it on every merge so .wslconfig stays small. (Switch back
to ('localhostForwarding',) the day mirrored mode is the default
again -- right now NAT + localhostForwarding is the reliable
combo per operator's testing on Win 11 build 28020.)

<!-- mios-src:c6e801626313 from build-mios.ps1:5525-5529 -->

### Windows Firewall inbound rules so OTHER devices on the...

Windows Firewall inbound rules so OTHER devices on the operator's
LAN (phone, tablet, laptop) can reach the dev VM's container ports
at <Windows-host-IP>:NNNN -- not just from the same Windows box.

Why this is needed even with WSL2 mirrored networking + .wslconfig
firewall=false:
  * Mirrored mode shares Windows' IP stack with the WSL VM, so a
    container bound to 0.0.0.0:NNNN inside the dev VM appears as
    Windows-side 0.0.0.0:NNNN automatically -- LISTEN visible in
    `netstat -ano | findstr :9090`.
  * .wslconfig firewall=false bypasses Hyper-V Firewall enforcement
    for the VM's vSwitch, so Windows-side localhost reaches the
    port without an extra Hyper-V allow rule.
  * BUT incoming connections from a LAN device still traverse the
    standard Windows Defender Firewall on the host's physical NIC.
    Defender default-denies inbound TCP for unknown listeners --
    so without an explicit per-port allow rule, the phone's
    browser hangs on connect even though Windows itself reaches
    localhost fine.

SSOT: mios.toml [ports].* (port numbers) + [ports.lan_firewall].*
(profiles + expose list). Vendor defaults below; operator edits
mios.html to flip exposure on / off per service or narrow
profiles.

Operator-flagged "windows installation should also
open the containers ports / forward them on windows side so that
we can access open webui, searxng, hermes, etc -- from my phone
or another device(s) on the local network."

<!-- mios-src:622661edbc55 from build-mios.ps1:5564-5592 -->

### Windows-side `netsh interface portproxy` mappings so OTHER...

Windows-side `netsh interface portproxy` mappings so OTHER devices
on the LAN can reach the dev VM's container ports.

Why this is needed alongside Set-MiosLanFirewallRules:
In NAT networking mode (.wslconfig networkingMode=NAT, which MiOS
uses because mirrored mode silently breaks loopback forwarding on
the operator's Win11 build 28020), services bound to 0.0.0.0
inside the dev VM are reachable ONLY at Windows-side 127.0.0.1
(via the localhostForwarding=true bridge). The host's external
NIC (Wi-Fi / Ethernet) has nothing listening on those ports, so
connections from a phone on the same Wi-Fi hang on connect.
netsh portproxy makes Windows listen on 0.0.0.0:<port> and
forward to 127.0.0.1:<port>, which then bounces into the dev VM
via WSL's loopback bridge. Net effect: phone -> Win NIC ->
portproxy -> WSL distro container.

Operator-flagged "none of my services are available
on my local wifi network".

SSOT: same [ports].* + [ports.lan_firewall].expose list as the
firewall rules above, so opening / closing a service in mios.html
affects BOTH layers in lock-step. Idempotent: deletes the old
mapping before adding so re-runs converge cleanly without
accumulating duplicate listeners.

<!-- mios-src:83a136647573 from build-mios.ps1:5676-5699 -->

### CRITICAL FIX -- bind 0.0.0.0:PORT (covers Windows-host...

CRITICAL FIX -- bind 0.0.0.0:PORT (covers Windows-host
localhost AND LAN clients in one rule), connect to the WSL VM's
eth0 IP. Earlier attempts:
  v0 (broken): listen=0.0.0.0 + connect=127.0.0.1 -- hijacked
    wslhost AND landed on dead Windows-host loopback. Every
    Windows-host curl localhost:PORT timed out.
  v1 (incomplete): listen=<LAN-IP> + connect=<WSL-VM-IP> -- LAN
    clients worked, Windows-host localhost broke because nothing
    bound 0.0.0.0:PORT (and WSL2's native localhostForwarding
    turned out to silently fail under NAT mode).
  v2 (current): listen=0.0.0.0 + connect=<WSL-VM-IP>. No hijack
    because target is the WSL VM, not Windows loopback. Windows-
    host localhost:PORT and LAN client <host-lan-ip>:PORT both
    hit the portproxy and forward into the WSL VM. Operator-
confirmed 8/8 MiOS services reachable from
    Windows browser via this rule shape.
WSL VM eth0 IP resolution. wsl.exe emits UTF-16LE by default --
capturing that in PowerShell mangles it (operator-confirmed
produced "20172.21.194.158", a garbage-prefixed IP, in
the live netsh portproxy table -> every LAN connect failed).
Two-part fix:
  1. $env:WSL_UTF8=1 makes wsl.exe emit clean UTF-8.
  2. [regex] extracts ONLY a valid dotted-quad from the output --
     belt-and-suspenders against any stray byte that still slips
     through, so connectaddress is ALWAYS a clean N.N.N.N or empty.

<!-- mios-src:bbf8ef9e5353 from build-mios.ps1:5720-5744 -->

### Recovery

Recovery: if a previous run of Rename-PodmanDevDistro renamed
the WSL distro from `podman-MiOS-DEV` to `MiOS-DEV`, every
subsequent `podman machine start/init/ssh` invocation fails
with WSL_E_DISTRO_NOT_FOUND -- podman hardcodes the `podman-`
prefix in WSLDistroName() and can't see the renamed distro.

This function detects the renamed-but-broken state and reverses
the rename via export -> unregister -> import-with-prefix.
User-facing surfaces (dashboard, mios-dev launcher, icons)
already hide the prefix, so the operator still sees "MiOS-DEV"
everywhere they look.

Idempotent: bails if podman-$DevDistro already exists or if
$DevDistro isn't registered at all.
Bypass: $env:MIOS_SKIP_PODMAN_RESTORE=1.

<!-- mios-src:996966b69fcc from build-mios.ps1:5789-5803 -->

### Drops the `podman-` prefix that `podman machine init`...

Drops the `podman-` prefix that `podman machine init` auto-adds
to its WSL2 distro: renames podman-MiOS-DEV -> MiOS-DEV so the
operator-facing distro name matches the project name everywhere
(Start Menu, dashboard, `wsl -d MiOS-DEV`, mios-dev shortcut).

Procedure: export -> unregister -> import-with-new-name. Only
safe to call AFTER all `podman machine ssh` and `podman build`
operations have completed (subsequent `podman machine start/ssh`
commands will FAIL because podman hardcodes the `podman-` prefix
in WSLDistroName(); the operator's daily workflow uses `wsl -d
MiOS-DEV` or the `mios-dev` shortcut, both of which work).

The Windows-side podman client connection (a fixed SSH URI at
127.0.0.1:<port>/run/podman/podman.sock) is unaffected: the
socket lives inside the distro, the port-forward survives the
rename, and `podman cp / commit / build` continue to work as
long as the distro is started via `wsl -d MiOS-DEV`.

Idempotent: if `podman-$DevDistro` is already absent and
`$DevDistro` is registered, skip with a no-op.

Default behavior INVERTED skipping the rename is now
the default. Reason: the rename breaks Podman Desktop's machine
visibility (Podman Desktop tracks the distro by its podman- prefix
registration; the rename + M:\ relocation orphans the machine
database entry, so the dev VM appears Stopped / un-launchable in
Podman Desktop even when wsl -l -v shows it Running). Operator-
facing UX continues to read "MiOS-DEV" via the Windows Terminal
profile name, Start Menu labels, and the `mios-dev` helper.

TOML-first per AGENTS.md §3 / mios.toml is THE singular SSOT.
Resolve via [bootstrap.dev_vm].rename_distro from the layered
overlay; env var $MIOS_RENAME_DISTRO remains as a runtime override
for ad-hoc operator use (overrides TOML when set).

<!-- mios-src:bc8cffce6011 from build-mios.ps1:5842-5875 -->

### IMPORTANT

IMPORTANT: parameter was previously named $Args, which is one of
PowerShell's reserved superglobals (automatically populated with
the function's UNBOUND positional args). Inside the function body
$Args was therefore ALWAYS empty -- the test `if ($Args)` failed
and Arguments never made it onto the.lnk. Symptom
MiOS Linux Apps Start Menu shortcuts had TargetPath=wsl.exe but
Arguments="" so clicking "Files" / "Web" / etc. launched a bare
wsl.exe shell instead of `wsl -d podman-MiOS-DEV --user mios --
flatpak run <appid>`. Renamed to $ArgList so callers' --Args
passes actually land on the shortcut.

<!-- mios-src:bbfdbd2e924b from build-mios.ps1:5962-5971 -->

### Body extracted to src/install-host-tools.ps1 per operator...

Body extracted to src/install-host-tools.ps1 per operator directive
"TOLD YOU A MONOLITH INSTALL.ps1 SCRIPT WAS A BAD IDEA
AND THAT THE BOOTSTRAP SHOULD BE DOING MOST OF THE HOST_SIDE SETUP
AND INSTALLATIONS". Dot-sourced from disk at first call so the
360-line winget install logic is no longer inline in this monolith
(also reduces AMSI heuristic surface).

<!-- mios-src:047a8da3ddde from build-mios.ps1:5981-5986 -->

### Mirror MiOS's Linux branding (Geist + Symbols-Only Nerd...

Mirror MiOS's Linux branding (Geist + Symbols-Only Nerd Font +
oh-my-posh) onto the Windows host so PowerShell, Windows Terminal,
and any Windows-side terminal that opens MiOS-DEV (Ptyxis flatpak
via WSLg, or just `wsl -d podman-MiOS-DEV`) renders the same
MiOS-themed prompt with the same glyphs.

Installs:
  1. Geist + Symbols-Only Nerd Font in %LOCALAPPDATA%\Microsoft\
     Windows\Fonts (per-user, no admin needed). Registered via
     HKCU registry so all Windows apps see them.
  2. oh-my-posh.exe in %LOCALAPPDATA%\Programs\oh-my-posh\bin\
     and added to the user's PATH.
  3. PowerShell profile snippet that initializes oh-my-posh with
     the MiOS theme (mios.omp.json from the cloned mios.git repo,
     copied to %APPDATA%\MiOS\mios.omp.json so the profile can
     reach it without depending on $MiosRepoDir resolution).

Idempotent: each step probes for existing installs first.
Bypass: $env:MIOS_SKIP_WINDOWS_BRANDING=1.

<!-- mios-src:45726d79756c from build-mios.ps1:6005-6023 -->

### Re-resolve the install root

Re-resolve the install root: if the MIOS-DEV data disk is up
(M:\ by default) ALL install paths move onto it (full-partition
overlay). On a re-run that started before the data disk
existed, this is also where leftover C:\MiOS content gets
auto-migrated onto M:\MiOS so the operator never has to clean
up split-state across drives.

<!-- mios-src:3d39c3fe114d from build-mios.ps1:6029-6034 -->

### ── 1. Fonts (TOML-first per AGENTS.md §3)...

── 1. Fonts (TOML-first per AGENTS.md §3) ───────────────────────
Sources + install scope all resolve from mios.toml [theme.font].*
so operators can pin URLs / force scope via mios.html. Geist is the
MiOS GLOBAL font ("Linux and Windows Font is
Geist font (system-wide -- terminals, apps, UI, etc-etc)") so the
default scope is "auto" => system-wide when elevated.

<!-- mios-src:2a32ca0ce9f4 from build-mios.ps1:6044-6049 -->

### SendMessageTimeout, NOT SendMessage: a synchronous...

SendMessageTimeout, NOT SendMessage: a synchronous HWND_BROADCAST of
WM_FONTCHANGE blocks the installer FOREVER if ANY top-level window is
hung/unresponsive -- the stuck-install root cause (hung after
"Symbols-Only Nerd Font installed"). SMTO_ABORTIFHUNG|SMTO_NORMAL (0x0002)
+ 1000ms/window makes the broadcast non-blocking. 0xFFFF=HWND_BROADCAST,
0x001D=WM_FONTCHANGE.

<!-- mios-src:a2e7ac4709fa from build-mios.ps1:6141-6146 -->

### Substitute powerline glyphs from mios.toml [theme.prompt]...

Substitute powerline glyphs from mios.toml [theme.prompt] (SSOT).
The on-disk omp.json ships with vendor-default rounded caps
( / ); operators who switch to sharp triangles or
flat separators via mios.html overwrite [theme.prompt].
powerline_right / .powerline_left / .leading_diamond / .trailing_diamond
which we patch into the staged copy here. Per operator: "no
hardcoding ANYWHERE -- everything from the toml/html".

<!-- mios-src:8e8bc4ddfa38 from build-mios.ps1:6192-6198 -->

### ── Color substitution from mios.toml [colors] (SSOT) ───...

── Color substitution from mios.toml [colors] (SSOT) ───
Per "oh my posh and other settings
should source from the same toml sections for all
platform for theme/branding to be truly unified in code."
The on-disk omp.json ships with vendor-default Hokusai
palette hex codes that EXACTLY match the [colors] vendor
defaults; substituting by literal hex lets operator
palette overrides via mios.html flow into every MiOS
terminal without touching this script.  Brand colors
(Python yellow, Node green, Rust orange, Go cyan) stay
hardcoded -- they're universal language identity, not
MiOS palette.

<!-- mios-src:b1bde49c8276 from build-mios.ps1:6232-6243 -->

### Inject (or refresh) a thin REDIRECTOR in the user's...

Inject (or refresh) a thin REDIRECTOR in the user's PowerShell
profile. The redirector dot-sources M:\MiOS\powershell\profile.ps1
(the SSOT). Per operator: "EVERYTHING MIOS RELATED--EVEN WINDOWS
COMPONENTS INSTALLED--ARE ALL INSTALLED ON THE CREATED M:\
Drive/Partition!!!". The previous behaviour wrote the full
oh-my-posh init body into $PROFILE.CurrentUserAllHosts (i.e.
%USERPROFILE%\Documents\PowerShell\profile.ps1, on C:\) which
duplicated logic between the redirector and the M:\ profile.
Now $PROFILE is a 4-line shim: M:\ has the actual body. Marker
comments delimit the MiOS-managed block so re-runs are
idempotent (we replace the block, not append).

<!-- mios-src:c02a75615846 from build-mios.ps1:6268-6278 -->

### Generate one multi-size .ico (16/32/48/64/256) styled to...

Generate one multi-size .ico (16/32/48/64/256) styled to match the
MiOS dashboard ASCII art: an isometric 3D cube (top + left-front +
right-front faces) with `/:\`-style hatch marks on each face,
echoing the wireframe blocks of the MIOS letters in the dashboard
banner. The cube is rendered in the MiOS palette (Hokusai bg,
cream front, accent orange top), with an optional badge in the
bottom-right corner for action-verb shortcuts.

Visual rationale: at 16-32 px the letter "M" is unrecognizable,
but the iso-cube silhouette + hatched faces stay readable and
clearly map back to the dashboard art. The badge layer
disambiguates verbs (mios-build vs mios-pull etc.).

<!-- mios-src:dec0a11909dd from build-mios.ps1:6319-6330 -->

### MiOS palette (Hokusai + operator): bg = #282262 deep...

MiOS palette (Hokusai + operator):
  bg     = #282262   deep Hokusai blue (canvas)
  fg     = #E7DFD3   warm cream (front-left face)
  accent = #F35C15   sunset orange (top face -- "lit" surface)
  shade  = #14112E   near-black blue (right face -- shadowed)
  green  = #3E7765   forest green (non-destructive verb badges)

<!-- mios-src:3a93b6293129 from build-mios.ps1:6346-6351 -->

### Builds out the Windows-side MiOS install tree and...

Builds out the Windows-side MiOS install tree and shortcuts:

  $MiosInstallDir/                 (= C:\MiOS for admin installs,
    bin/                            %LOCALAPPDATA%\MiOS otherwise)
      oh-my-posh.exe               (already staged by Install-WindowsBranding)
      mios-dash.ps1                Windows dashboard
      mios-dev.ps1                 wsl -d <dev-distro> launcher
      mios-pull.ps1                wsl --user root sudo /usr/bin/mios-pull
      mios-update.ps1              re-runs build-mios.ps1 to refresh
    icons/                         per-verb .ico files (M + badge)
      mios.ico, mios-dev.ico, mios-pull.ico, mios-dash.ico,
      mios-build.ico, mios-update.ico, mios-config.ico
    themes/mios.omp.json           (already staged by Install-WindowsBranding)

  Start Menu\Programs\MiOS\        $StartMenuDir
    MiOS.lnk                       (main launcher; wt -p MiOS or pwsh)
    MiOS Dev VM.lnk                (wsl into MiOS-DEV)
    MiOS Update.lnk                (mios-pull)
    MiOS Dashboard.lnk             (standalone dash)
    MiOS Configurator.lnk          (HTML configurator on MiOS-DEV WSLg)

  Desktop\MiOS.lnk                 single primary shortcut
  PowerShell profile               mios-dash / mios-dev / mios-pull functions
  Windows Terminal settings.json   "MiOS" profile + color scheme

Idempotent: regenerates / replaces in place.
Bypass: $env:MIOS_SKIP_LAUNCHER=1.

<!-- mios-src:8cdac1a44da3 from build-mios.ps1:6505-6531 -->

### ── 2. Bin scripts: mios-dash + mios-dev + mios-pull +...

── 2. Bin scripts: mios-dash + mios-dev + mios-pull + mios-update ──
"the dashboards are still too big!!!... but
if I open a new tab in MiOS apps' terminal window--I get a perfectly
fitting dashboard and piping!!!".

The "too big" dashboard was THIS file's previous contents -- a
verbose Show-MiosDashboard with full ASCII logo + Self-replication
endpoint probes + dev-VM state + build-pipeline arrow. The new-tab
"perfectly fitting" dashboard is the Show-MiosDashboard inside
M:\MiOS\powershell\profile.ps1 (auto-runs on each tab open).

Unify: mios-dash.ps1 is now a thin wrapper that dot-sources the
profile body and calls the SAME Show-MiosDashboard. One canonical
dashboard rendered everywhere -- typing `mios dash` is identical
to opening a new tab. SSOT: profile body comes from Get-MiOS.ps1's
Install-MiOSPowerShellProfile (which reads mios.toml [dashboard]
rows + [terminal] dims + [theme] palette).

<!-- mios-src:a649d81ee44a from build-mios.ps1:6567-6583 -->

### <MiOSRoot>\bin\mios-dash.ps1 `mios dash` verb -- delegates...

<MiOSRoot>\bin\mios-dash.ps1
`mios dash` verb -- delegates to the canonical Show-MiosDashboard
defined in M:\MiOS\powershell\profile.ps1 so the dashboard rendered
here is byte-identical to the one that auto-renders on each MiOS
terminal tab open. Operator's directive ONE dashboard
globally, dictated by mios.toml.

<!-- mios-src:e546f5879a09 from build-mios.ps1:6586-6591 -->

### Pre-set the auto-MOTD guard BEFORE dot-sourcing the profile...

Pre-set the auto-MOTD guard BEFORE dot-sourcing the profile so the
profile body's auto-render is suppressed -- we explicitly call
Show-MiosDashboard ourselves below. Without this, fresh `pwsh`
processes (launched from a Start Menu shortcut, a new WT tab, or
any non-nested context) re-source the profile, which triggers its
auto-render, which then runs in addition to our explicit call --
producing two dashboards in a row. Operator-flagged
"DOUBLE DASHBOARD still when running 'mios dash'".

<!-- mios-src:c4f6ae050cc9 from build-mios.ps1:6594-6601 -->

### The original verbose mios-dash body (full ASCII logo +...

The original verbose mios-dash body (full ASCII logo + Self-replication
endpoint probes + WSL distro state + build pipeline arrow) was
operator-rejected too tall for the 80x20 portal. The
block below is dead code retained as a textual marker only -- the
heredoc above is what gets staged.

<!-- mios-src:552a1ca8b258 from build-mios.ps1:6619-6623 -->

### mios-dev.ps1 / mios-pull.ps1 -- self-resolving wrappers....

mios-dev.ps1 / mios-pull.ps1 -- self-resolving wrappers.
The Rename-PodmanDevDistro pass at the end of build-mios.ps1
drops the `podman-` prefix, so the canonical post-install name
is `$DevDistro` (= "MiOS-DEV"). These wrappers probe at RUNTIME
so they Just Work whether the rename has happened yet or not
(e.g. during a partial install or after a failed rename), and
they pick up future renames without needing regeneration.

<!-- mios-src:ad3196c7d677 from build-mios.ps1:6625-6631 -->

### Bare invocation -> mios user, login shell at /, with the...

Bare invocation -> mios user, login shell at /, with the MiOS Linux-side
dashboard rendering on entry (banner + ASCII logo + fastfetch + framing).
The dashboard is wired by /etc/profile.d/zz-mios-motd.sh inside the dev
VM (seeded by Phase 3 of the bootstrap) which auto-runs
/usr/libexec/mios/mios-dashboard.sh on every interactive bash login.
`bash -l` (login shell) ensures /etc/profile.d/* is sourced.

Args pass through verbatim so callers can still do `mios-dev --user user
-- some-cmd` etc.

<!-- mios-src:9f7a9bb10624 from build-mios.ps1:6645-6653 -->

### user mios matches the WT MiOS-DEV profile so dashboard /...

--user mios matches the WT MiOS-DEV profile so dashboard / theming
/ mios.toml resolution all hit the per-user MiOS layout. --cd /
because `.git IS /` (Architectural Law 3) -- the dev VM's git
working tree is the filesystem root.

<!-- mios-src:1aab04d05a8b from build-mios.ps1:6656-6659 -->

### <MiOSRoot>\bin\mios-pull.ps1 -- refreshes BOTH the...

<MiOSRoot>\bin\mios-pull.ps1 -- refreshes BOTH the Windows-side M:\
overlay AND the dev VM root (/) from origin/main. Two distinct git
working trees:
  1. M:\ (Windows-side mios.git overlay) -- backs every M:\usr/share/mios
     lookup, M:\usr/share/mios/configurator/mios.html (MiOS Config
     shortcut), and what the dev VM sees at /mnt/m/.
  2. / inside MiOS-DEV (the dev VM's mios.git working tree per
     Architectural Law 3, ".git IS /") -- /usr/bin/mios-pull does the
     git fetch + reset --hard inside the dev distro.
Operator confirmed bug previous mios-pull.ps1 only did
step 2, leaving M:\ stale -> `mios build` rendered an old MiOS.

<!-- mios-src:88ceddb36b95 from build-mios.ps1:6668-6678 -->

### Step 2

Step 2: dev VM root refresh.
Pre-bootc-switch the dev VM doesn't have /usr/bin/mios-pull yet (that
binary lands via the OCI image overlay during `mios build`). Inline
the equivalent bash so this verb works on day-0 -- before, during, and
after the OCI image is built. The work is identical to what
/usr/bin/mios-pull does post-bootc-switch: ensure / is a git working
tree of mios.git (Architectural Law 3, ".git IS /"), then
fetch + reset --hard origin/main.
NOTE: this whole heredoc is INSIDE the outer @"..."@ that builds
mios-pull.ps1. The @'...'@ below does NOT create a nested literal
section -- it's just literal chars in the outer here-string. Every
bash `$` that should reach the rendered file as a literal `$` must
be escaped with a backtick or PS evaluates it.

Earlier attempt passed `bash -c \$inlinePull` -- PowerShell's native-
command argument quoting mangled the multi-line string (operator-
observed install: ": invalid option namefail / -c: line
20: syntax error: unexpected end of file from `if' command on line
8"). The robust pattern is stdin-piping: write the script to bash's
stdin via the pipeline, with LF normalization so CRLF doesn't make
bash see `\r` as part of identifiers.

<!-- mios-src:95d4e615e5d1 from build-mios.ps1:6706-6726 -->

### Normalize CRLF -> LF (Windows authoring of this PS file may...

Normalize CRLF -> LF (Windows authoring of this PS file may leave
CRLF in `$inlinePull which would corrupt bash identifiers like `\r`
being treated as part of variable names) and pipe to bash via stdin
(bash -s reads the script from stdin; arguments after `--` reach the
script as `\$1 \$2 ...`). This avoids the native-cmd quoting bugs
`bash -c <multi-line>` exhibited.

<!-- mios-src:7b5a8bdf3ecb from build-mios.ps1:6749-6754 -->

### mios-update.ps1 -- self-updates the bootstrap from origin...

mios-update.ps1 -- self-updates the bootstrap from origin BEFORE
re-running build-mios.ps1. This is what makes `mios update` actually
pick up upstream changes: previously it ran the LOCAL stale
build-mios.ps1 directly, so any fix shipped to origin/main never
reached the operator until they manually re-paste the irm|iex
one-liner. The new flow:

  1. git -C M:\MiOS\bootstrap-shadow fetch + reset --hard origin/main
  2. robocopy mios-bootstrap shadow -> M:\ overlay (refreshes the
     build-mios.ps1 the next step will run)
  3. pwsh -File <freshly-overlaid build-mios.ps1>

Step 1 is idempotent (no-op if the shadow's HEAD already matches
origin/main); step 2 is destructive over the overlay paths but
those are managed by mios-bootstrap anyway.

<!-- mios-src:e00c6a9f63be from build-mios.ps1:6759-6773 -->

### 1. Self-update the shadow if .git is present and the...

1. Self-update the shadow if .git is present and the operator's
   network can reach origin. Falls through silently on failure --
   the next step still runs the (possibly stale) local copy.

<!-- mios-src:b8b62583fe28 from build-mios.ps1:6785-6787 -->

### mios-config.ps1 -- opens the HTML configurator in the...

mios-config.ps1 -- opens the HTML configurator in the operator's
default browser. Walks a candidate list so we hit the M:\ overlay
(canonical operator-edit copy) first, then bootstrap-shadow, then
legacy paths. Per operator: "have the MiOS config link open the
webpage directly in the local browser (opens the mios.html
directly installed on the newly created M:\ directories)".

<!-- mios-src:ed0bdd6d849d from build-mios.ps1:6825-6830 -->

### mios-config.ps1 -- the `mios config` verb / MiOS Config...

mios-config.ps1 -- the `mios config` verb / MiOS Config app.
Resolves mios.html in priority order and shell-executes it so the
operator's default browser opens the page. Edit fields, save -- the
browser writes a copy to %USERPROFILE%\Downloads; `mios build` step 2
promotes it back to M:\etc\mios + M:\usr\share\mios.

<!-- mios-src:d2b6c4368fd1 from build-mios.ps1:6835-6839 -->

### mios-build.ps1 -- THE operator-typed `mios build` verb. The...

mios-build.ps1 -- THE operator-typed `mios build` verb. The Day-0
contract: Windows host does ack + MiOS-DEV provisioning, then
STOPS. `mios build` is the operator-triggered next step that
promotes any operator edits saved to %USERPROFILE%\Downloads, syncs
the M:\ overlay to origin/main, then SSHes into MiOS-DEV and
ignites mios-build-driver. The dev VM is THE builder; Windows is
provisioning + handoff ONLY.

<!-- mios-src:6d88f1a3b51b from build-mios.ps1:6996-7002 -->

### <MiOSRoot>\bin\mios-build.ps1 -- the operator-triggered...

<MiOSRoot>\bin\mios-build.ps1 -- the operator-triggered `mios build` verb.
Self-replication contract: edit mios.toml in mios.html (browser saves
it to %USERPROFILE%\Downloads on Windows because file:// can't write
back), then run this script. It promotes the newest mios*.toml /
*mios*.html from Downloads into M:\etc\mios + M:\usr\share\mios,
archives the source as .imported-<timestamp>, syncs the M:\ overlay
to origin/main, then SSHes into MiOS-DEV to run mios-build-driver
(the actual build pipeline). Architectural Law 5 + the .git IS /
invariant flow through end-to-end.

<!-- mios-src:3b11d38d52d5 from build-mios.ps1:7007-7015 -->

### Sync M:\ overlay to origin/main BEFORE the dev VM handoff....

Sync M:\ overlay to origin/main BEFORE the dev VM handoff. Two
distinct git working trees need refreshing:

  1. M:\ (the Windows-side mios.git overlay) -- THIS is what backs
     M:\usr\share\mios\configurator\mios.html (opened by MiOS Config),
     M:\usr\share\mios\mios.toml (read by every Get-MiosTomlValue),
     and what the dev VM sees at /mnt/m/. Without a Windows-side
     `git fetch + reset --hard origin/main` here, M:\ stays frozen
     to whatever was on origin at the LAST install run, so:
       - MiOS Config opens an OLD mios.html
       - mios.toml reads return OLD values
       - the dev VM's build-driver via /mnt/m/ uses OLD overlay
Operator confirmed bug `mios build` rendered an
     "old MiOS build" because M:\ was stale.
  2. / inside MiOS-DEV (the dev VM's mios.git working tree -- Architectural
     Law 3, ".git IS /") -- mios-pull.ps1 delegates to
     /usr/bin/mios-pull inside the dev distro for this.

Step 1 (M:\ Windows-side) MUST run BEFORE step 2 because the dev
distro's mios-build-driver reads from /mnt/m/ for some inputs (e.g.
mios.toml lookups via Get-MiosTomlValue). Refreshing M:\ first
guarantees the dev VM build sees the latest overlay.

<!-- mios-src:ff0e88c28377 from build-mios.ps1:7045-7066 -->

### Start the WSL-Podman machine. `wsl.exe -d <distro>` later...

Start the WSL-Podman machine. `wsl.exe -d <distro>` later will
auto-start the WSL distro alone, but the podman MACHINE wraps the
distro with the rootful podman daemon + OCI builder services that
mios-build-driver uses to actually build MiOS. Without this explicit
start, the build can fail on first invocation after a reboot with
"Cannot connect to Podman" because the daemon isn't up yet.
Idempotent: no-op if the machine is already running. Operator-confirmed
`mios build` should actually open the WSL-Podman machine
AND build MiOS AND overlay newest MiOS repos at /ROOT.

<!-- mios-src:030df01f18d4 from build-mios.ps1:7099-7107 -->

### `podman machine` and `wsl.exe -d` use DIFFERENT names for...

`podman machine` and `wsl.exe -d` use DIFFERENT names for the same VM:
  wsl.exe -d expects the WSL distro registration name -- 'podman-MiOS-DEV'
  podman machine expects the machine name without prefix -- 'MiOS-DEV'
Resolve-MiosDevDistro returns the WSL distro name (because it iterates
`wsl -l -q`), which is correct for wsl.exe but causes `podman machine
start podman-MiOS-DEV` to fail with 'VM does not exist'. Strip the
'podman-' prefix for podman-machine calls.

<!-- mios-src:7c2635b577aa from build-mios.ps1:7109-7115 -->

### Pre-warm the WSL distro so its kernel + systemd are up...

Pre-warm the WSL distro so its kernel + systemd are up BEFORE we ask
podman to start the machine. Without this, `podman machine start`
races and frequently emits:
  "could not start api proxy since expected pipe is not available:
   podman-MiOS-DEV"
  "Error: machine did not transition into running state: ssh error"
A no-op `wsl.exe -d <distro> --user mios -- true` triggers WSL to
(re)launch the distro, which creates the AF_VSOCK / pipe endpoints
podman then attaches to.

<!-- mios-src:7827604bfd47 from build-mios.ps1:7118-7126 -->

### SSH handoff into MiOS-DEV. mios-build-driver is THE build...

SSH handoff into MiOS-DEV. mios-build-driver is THE build pipeline:
fetch + overlay newest mios.git at / (Architectural Law 3 ".git IS /")
-> account/identity -> install -> smoketest -> build -> deploy -> boot.
The build dashboard renders here in this WT tab (live, not proxied).
We pass --user mios because the WT MiOS-DEV profile and operator
expectations land on the mios login user (uid 1000) -- created by the
seed script in Phase 3, with passwordless sudo for the build pipeline's
privileged steps.
First-run staging: on a fresh MiOS-DEV the OCI image hasn't been built
yet, so /usr/libexec/mios/mios-build-driver doesn't exist inside the
distro. The canonical source lives in mios.git at
usr/libexec/mios/mios-build-driver (mios-dev/MiOS layout: FHS-shaped
tree directly at repo root, NO 'system_files/' prefix). Per the
"M:\ IS git" layout (build-mios.ps1 Update-MiosInstallPaths),
mios.git's working tree is overlaid AT M:\ root, so the file is at
M:\usr\libexec\mios\mios-build-driver, which is
/mnt/m/usr/libexec/mios/mios-build-driver from inside WSL. Copy it in
(idempotent -- overwrites any older staged copy) before invoking. Once
the OCI image is built and bootc switch deploys it, the file is also
present at the same path from the image overlay; this copy step
becomes a no-op on subsequent re-builds.

<!-- mios-src:24d3f5ab7ae5 from build-mios.ps1:7160-7180 -->

### Install-robustness surface the driver's REAL exit code....

Install-robustness surface the driver's REAL exit code. Without
this the `mios build` verb reported SUCCESS even when the OCI build failed
inside MiOS-DEV -> the operator believed the image built and MiOS AI would come
up, when it never did. Propagate the failure so it is visible + scriptable.

<!-- mios-src:de8c6b006e4d from build-mios.ps1:7190-7193 -->

### mios.ps1 -- THE MiOS app dispatcher. "U.N.I.F.I.E.D...

mios.ps1 -- THE MiOS app dispatcher.
"U.N.I.F.I.E.D EVERYTHING MiOS related!!!".  This file used to
render a SECOND, NON-UNIFIED layout (a numbered TUI menu) when
the operator typed `mios <anything>` -- diverging from the
canonical Show-MiosDashboard ([dashboard].rows) layout the
M:\MiOS\powershell\profile.ps1 renders.  The redundancy is
gone: `function mios <verb>` in the profile body now dispatches
to mios-<verb> directly, so this file just exists as a
thin pass-through (some legacy code paths Start-Process this
script).  The body re-defines the per-verb mios-<name> wrapper
functions and dispatches the requested verb.  No TUI menu, no
divergent dashboard.

<!-- mios-src:e6f655148dd1 from build-mios.ps1:7217-7228 -->

### <MiOSRoot>\bin\mios.ps1 -- thin verb-dispatch pass-through....

<MiOSRoot>\bin\mios.ps1 -- thin verb-dispatch pass-through.
Auto-installed by mios-bootstrap (Install-MiosLauncher).  Operator
"U.N.I.F.I.E.D EVERYTHING MiOS related!!!". This file
used to render its own Show-MiosApp TUI menu (a different layout
from the canonical Show-MiosDashboard that [dashboard].rows
drives) -- that has been REMOVED.  Now the file dot-sources the
canonical M:\MiOS\powershell\profile.ps1 (so the operator gets
the same Show-MiosDashboard render + `mios <verb>` dispatcher
every other entry path uses) then dispatches the verb passed as
argv if any.  No TUI menu, no second dashboard layout.

<!-- mios-src:fb7ee67cba21 from build-mios.ps1:7231-7240 -->

### If a verb was passed (e.g. `mios.ps1 build`), dispatch...

If a verb was passed (e.g. `mios.ps1 build`), dispatch through the
`mios` function the profile body just defined; else just leave the
operator at the loaded prompt.

<!-- mios-src:ff43254da3f3 from build-mios.ps1:7253-7255 -->

### Auto-generated by mios-bootstrap/build-mios.ps1. Block is...

Auto-generated by mios-bootstrap/build-mios.ps1. Block is replaced
on every re-run between the markers. ONLY the per-verb script
wrappers live here.  The `mios <verb>` dispatcher lives in
Get-MiOS.ps1's M:\MiOS\powershell\profile.ps1 -- this redirector
dot-sources that profile FIRST, then runs this block.  Previous
revisions had a `function mios { ... mios.ps1 ... }` here that
REDEFINED the canonical dispatcher to call the legacy
Show-MiosApp TUI hub -- "not unified
dashboards!!!" (TWO different layouts rendering: the legacy hub
AND the [dashboard].rows-driven Show-MiosDashboard).  Removed
`function mios` here so the canonical dispatcher (which routes
to mios-<verb> functions sharing the same Show-MiosDashboard
layout) wins.

<!-- mios-src:972afcc29966 from build-mios.ps1:7456-7468 -->

### mios-dash + mios-mini are defined as INLINE FUNCTIONS in...

mios-dash + mios-mini are defined as INLINE FUNCTIONS in the
Get-MiOS.ps1 profile body above (mios-dash = FULL render with
ASCII banner + services + sys specs; mios-mini = compact 80x20
framed banner + fastfetch). We don't override them with bin-
script wrappers here because the FULL render needs to query the
running MiOS-DEV state via wsl.exe -- inlining keeps it co-
located with the rest of the verb implementations and leaves
the bin-script staging point for legacy direct-invocation only.

<!-- mios-src:d2636ec7c4b8 from build-mios.ps1:7470-7477 -->

### Set-MiosWindow -- resize + re-center the CURRENT MiOS...

Set-MiosWindow -- resize + re-center the CURRENT MiOS terminal
window between [terminal] and [terminal.reading] modes from
mios.toml. "a centered 100x50 window called
MiOS 'reading mode' invoked with a command to resize (and re
center) the window between the sizes". Used by `mios portal` /
`mios reading` verbs and by the `btop` function which auto-flips
to reading mode.

<!-- mios-src:b02c744bc1e0 from build-mios.ps1:7485-7491 -->

### ── 4. Windows Terminal "MiOS" profile (settings.json patch)...

── 4. Windows Terminal "MiOS" profile (settings.json patch) ──────

The canonical implementation now lives in mios-bootstrap/Get-MiOS.ps1
(Install-MiOSGeistFont + Install-MiOSTerminalProfile + Get-MiOSCenteredWindowPosition).
Get-MiOS.ps1 runs FIRST on the irm|iex entry path, before this script
even starts, so the WT profile is already in place by the time
build-mios.ps1 lands here. The only thing we still rebind here is
the profile's commandline, so launching the "MiOS" tab from a
standalone WT (after install) opens the staged hub script (mios.ps1)
rather than a bare pwsh. Get-MiOS.ps1's commandline is just `pwsh
-NoLogo`; once the install dir exists we want it to launch the menu.

<!-- mios-src:126f156b1063 from build-mios.ps1:7632-7642 -->

### Per operator (clarified): "MiOS app opens to a windows...

Per operator (clarified): "MiOS app opens to a windows
terminal wherein 'mios *' invocations are done on the windows
host first and relevant MiOS-DEV 'mios *' invocations are
directly passed through to the podman-MiOS-DEV machine and then
the terminal is sshd in to the MiOS-DEV environment directly".

So MiOS profile commandline = Windows-side pwsh (loads MiOS PS
profile body with dashboard + `mios <verb>` dispatcher). The
dispatcher decides per-verb: Windows-host or pass-through to
MiOS-DEV via wsl/ssh. MiOS and MiOS-DEV WT profiles are
DIFFERENT entry points to the SAME branded experience -- MiOS
= Windows terminal, MiOS-DEV = direct dev VM shell.

Get-MiOS.ps1's Install-MiOSTerminalProfile owns commandline +
startingDirectory; we ONLY refresh the icon here (Pass-2 has
access to mios.ico after Generate-MiosIcons ran).

<!-- mios-src:13c33fae8c09 from build-mios.ps1:7648-7663 -->

### NOTE

NOTE: New-MiosShortcut + its shortcut-metadata helper code that
used to live here have been REMOVED. They were dead code -- the
only callers were the hub MiOS.lnk creator + the per-verb shortcut
loop, both of which were removed in earlier commits when shortcut
creation moved to Get-MiOS.ps1's FINAL STEP block. Removing the
dead Win32-interop code also eliminates AMSI heuristic flag bait.

<!-- mios-src:75fc9ffbe273 from build-mios.ps1:7711-7716 -->

### Install-root drive letter (SSOT...

Install-root drive letter (SSOT: [bootstrap.host_storage].drive_letter,
env override MIOS_DATA_DISK_LETTER). Substituted into the __MIOS_DRIVE__
placeholder of the staged launcher + gui-watch sources so the operator's
data-disk letter -- not a baked 'M' -- drives the install-root paths.

<!-- mios-src:65701a3f4455 from build-mios.ps1:7737-7740 -->

### ── ONE shortcut: MiOS (the hub)...

── ONE shortcut: MiOS (the hub) ─────────────────────────────────
Native-app behavior: the .lnk targets a tiny launcher script
(mios-launch.ps1) staged under $MiosBinDir. The launcher source
lives in src/mios-launch.ps1 in the repo (NOT inline here) so
AMSI heuristics don't see Win32-interop strings as part of the
.ps1 script content. build-mios.ps1 reads the source from disk
and writes it to $MiosBinDir at install time.

<!-- mios-src:c344714e6214 from build-mios.ps1:7743-7749 -->

### Requires -Version 5.1

Requires -Version 5.1

<!-- mios-src:bc35b223480a from build-mios.ps1:7835-7835 -->

### Shortcut targets WT.EXE DIRECTLY -- no pwsh launcher...

Shortcut targets WT.EXE DIRECTLY -- no pwsh launcher pre-flash.
Operator-reported regression: "opening apps shouldn't open a regular
windows terminal/powershell window before launching the MiOS app
ecosystem(s) -- MiOS app icons opens the app windows directly -- no
flashing a prompt that then launches the correct MiOS terminal
profile/application(s)".

The previous launcher pwsh.exe -NoProfile -WindowStyle Hidden -File
mios-launch.ps1 still produced a brief conhost flash before wt.exe
spawned (Windows shows the host process briefly even with
WindowStyle=Hidden). wt.exe is itself a windowed application -- the
.lnk pointing at wt.exe with the right args produces zero flash
because there's no intermediate console host.

Trade-off: lose the centering retry loop that mios-launch.ps1
provided. WT's --pos flag honors the initial position; the post-
bootstrap auto-launch path (in Get-MiOS.ps1's elevation block) still
runs the persistent re-center for the post-install spawn, but the
ongoing daily-shortcut path leans on WT's own positioning. If WT's
placement drifts the operator can edit globals.initialPosition in
mios.toml or right-click + drag.

<!-- mios-src:92b23b129d39 from build-mios.ps1:7958-7978 -->

### Fallback

Fallback: no wt.exe found -- run the bare hub script in a pwsh
console (still pre-flashes but at least gives the operator a
working shell). This branch should be unreachable on a
successful install since WT is a Phase 5 prerequisite.

<!-- mios-src:03ab2af810c1 from build-mios.ps1:7989-7992 -->

### ── Shortcut creation deferred to FINAL STEP of Get-MiOS.ps1...

── Shortcut creation deferred to FINAL STEP of Get-MiOS.ps1 ────────────
"applications and icons should be installed AFTER
everything--at the end!!!! LAST STEPS". The canonical 4-shortcut set
(MiOS, MiOS-WIN, MiOS Help, Uninstall MiOS) is created by
Get-MiOS.ps1's end-of-script block AFTER bootstrap.ps1 + build-mios.ps1
succeed. build-mios.ps1's Install-WindowsBranding does NOT create
shortcuts at all -- if it did, partial-install failures would leave
broken shortcuts pointing at a half-built dev VM.

<!-- mios-src:9a0c599c7d1f from build-mios.ps1:7997-8004 -->

### ── Per-verb native-app shortcuts...

── Per-verb native-app shortcuts ────────────────────────────────
Per operator: every MiOS verb appears as its own native Windows
app so MiOS-DEV / Dashboard / Configurator / Build are findable
in Start search and pinnable to taskbar/Start individually --
not just as items inside the hub menu. Each shortcut targets the
corresponding bin/mios-*.ps1 script with its dedicated icon.
The main MiOS.lnk above stays as the unified hub.
Per-verb shortcuts -- minimal, operator-curated set.
The hub 'MiOS.lnk' is created earlier at line ~5743 (the terminal
itself). Operator-typed verbs (build / dash / update / pull) are
NOT separate apps -- they're commands typed inside the MiOS
terminal. The native-app surface is exactly five:

  1. MiOS              The Windows-side terminal (themed WT MiOS
                       profile, dashboard on launch). Created at
                       line ~5743 as the hub.
  2. MiOS-DEV          Drops directly into podman-MiOS-DEV with
                       the Linux-side dashboard rendering at
                       login (full piping/framing/ASCII logo,
                       all theming).
  3. MiOS Config       Opens mios.html (the configurator) in the
                       operator's default browser. Browser saves
                       edited mios.toml to %USERPROFILE%\Downloads;
                       `mios build` step 2 promotes Downloads
                       edits into M:\etc\mios + M:\usr\share\mios.
  4. MiOS Help         Full verb + functionality reference.
  5. Uninstall MiOS    Created in the legacy block ~line 7126.

Both Start Menu .lnk AND Desktop .lnk for each.
The native-app catalog resolves through mios.toml [apps] (SSOT).
Operator-renames the apps via mios.html -- the configurator writes
mios.toml -- next install regenerates Start Menu / Desktop shortcuts
against the new name+bin+icon set. Vendor fallback below mirrors
what mios.toml [apps] ships with for cold first-run before any
operator edit.
canonical 4-shortcut set: MiOS / MiOS-WIN /
MiOS Help / Uninstall MiOS, all created in Get-MiOS.ps1's
Install-MiOSNativeApp. NO per-verb shortcut creator here -- the
entire [apps.shortcuts] toml-driven loader was a duplicate creator
that re-seeded MiOS-DEV.lnk / MiOS Config.lnk / MiOS Help.lnk on
every install (caught in the 15:27 install screenshot).
The previous "$verbShortcuts = @()" guard was racy: any operator
mios.toml [apps.shortcuts] section would re-populate it. Removed
entirely. Per operator: "JUST FUCKING LISTEN".

<!-- mios-src:487814dd4c55 from build-mios.ps1:8007-8050 -->

### Garbage-collect every shortcut OUTSIDE the canonical 4-set...

Garbage-collect every shortcut OUTSIDE the canonical 4-set
(MiOS / MiOS-WIN / MiOS Help / Uninstall MiOS). Per operator
MiOS-DEV.lnk and MiOS Config.lnk are NOT canonical --
the MiOS shortcut already targets the dev VM, and `mios config`
is a typed verb. Idempotent: if absent, skip.

<!-- mios-src:b19e87233537 from build-mios.ps1:8054-8058 -->

### Removed verbs (now operator-typed inside the MiOS terminal):

Removed verbs (now operator-typed inside the MiOS terminal):

<!-- mios-src:fabf9eb9d8ae from build-mios.ps1:8062-8062 -->

### ── MiOS Linux Apps (Start Menu subfolder)...

── MiOS Linux Apps (Start Menu subfolder) ─────────────────────────
"no MiOS Linux apps in windows start menus".
Two-prong fix: (a) /etc/wsl.conf adds [gui] guiApplications=true
so WSLg auto-exports .desktop entries (handled in mios.git);
(b) we ALSO create explicit Windows .lnk shortcuts here, because
WSLg auto-export depends on the distro's user-systemd being
healthy and the operator's preferred friendly names (Files / Web
/ VSCodium / etc.) don't survive the "(on podman-MiOS-DEV)"
suffix WSLg appends. Explicit shortcuts under
  Start Menu\Programs\MiOS\Linux Apps\<FriendlyName>.lnk
are bulletproof + match the operator's mental model.

Each shortcut targets wsl.exe with the dev distro:
  wsl.exe -d podman-MiOS-DEV --user mios -- flatpak run <appid>
Source of truth: mios.toml [desktop].flatpaks (operator-editable
via mios.html; new entries auto-surface on next bootstrap).

<!-- mios-src:2efd10707c95 from build-mios.ps1:8080-8095 -->

### Prefer wslg.exe (part of WSL since 2021) over wsl.exe so...

Prefer wslg.exe (part of WSL since 2021) over wsl.exe so the
shortcuts launch the GUI app DIRECTLY with no console popup
and Windows-Terminal-style chrome -- matches the exact UX
that WSLg's own auto-published `App (on podman-MiOS-DEV).lnk`
entries give the operator. wsl.exe spawns a host console;
wslg.exe is a pure GUI launcher.

<!-- mios-src:57b471c71256 from build-mios.ps1:8114-8119 -->

### AppId -> friendly-name mapping. Operator-edit-friendly...

AppId -> friendly-name mapping. Operator-edit-friendly: short
name appears in Start Menu, app id resolves the actual flatpak.
Unknown entries fall back to the last segment of the app id.

<!-- mios-src:93b306638ce5 from build-mios.ps1:8132-8134 -->

### Pull current flatpak picks from mios.toml...

Pull current flatpak picks from mios.toml [desktop].flatpaks.
Get-MiosTomlValue's regex is SINGLE-line (`(?<val>.+?)$`),
so a multi-line `flatpaks = [\n  "a",\n  "b",\n]` array
returns just `[` (the opening bracket on the same line as
the assignment). That stray `[` then propagated as a
phantom entry, producing a `[.lnk` shortcut in the
operator's Linux Apps folder (21:39).

Use the same multi-line array parser the overlay flatpak
loop uses upstream at line ~7945: regex-grab the bracket
body across newlines, strip TOML comments, split on commas,
trim quote/whitespace decoration.

<!-- mios-src:a763ea1b674a from build-mios.ps1:8146-8157 -->

### wslg.exe takes the same -d / --user / -- arg shape as...

wslg.exe takes the same -d / --user / -- arg shape as
wsl.exe BUT must be invoked with the FULL command path
(it doesn't run a login shell), so use /usr/bin/flatpak
explicitly. Matches WSLg's own auto-published shortcut
args exactly (e.g. for Ptyxis it writes:
  -d podman-MiOS-DEV --cd "~" -- /usr/bin/flatpak run
    --branch=stable --arch=x86_64 --command=ptyxis
    app.devsuite.Ptyxis).

<!-- mios-src:45ff5741f820 from build-mios.ps1:8192-8199 -->

### ── MiOS Services (web links via default browser)...

── MiOS Services (web links via default browser) ──────────────────
Start Menu\Programs\MiOS\Services\<Name>.url -- Internet Shortcut
files that open in the operator's default browser (Zen / Edge /
Firefox / Chrome). Operator-flagged "Should also
include shortcuts to all our containers and services as webapps/
weblinks using local browser(s)". .url files are Start Menu
indexable and respect the operator's BrowserChoice without us
having to detect the installed browser.
SSOT: mios.toml [ports].* + a label/url map of the same shape.

<!-- mios-src:28e17ff9e071 from build-mios.ps1:8248-8256 -->

### Internet Shortcut (.url) -- ASCII INI format that Windows...

Internet Shortcut (.url) -- ASCII INI format that
Windows Explorer + the Start Menu treat as a clickable
browser link. The [{000214A0-...}] block is the
ShellLinkPropertyBag GUID; Prop3=19,2 sets the file
as a Browse-shortcut (not Web-shortcut), which makes
Open With... behave correctly.

<!-- mios-src:ece676bc496c from build-mios.ps1:8296-8301 -->

### ── 7. Re-run Get-MiOS.ps1's Install-MiOSPowerShellProfile +...

── 7. Re-run Get-MiOS.ps1's Install-MiOSPowerShellProfile +
Install-MiOSTerminalProfile so EVERY install path (irm|iex Get-MiOS,
mios-update, build-mios.ps1 BootstrapOnly, etc.) deterministically
re-substitutes:
  - M:\MiOS\powershell\profile.ps1 (Show-MiosDashboard frame_width /
    right_margin / cell budget literals from current mios.toml
    [terminal])
  - WT settings.json globals (root launchMode, profiles.defaults
    scrollbarState/padding/useAcrylic/opacity/systemBackdrop/
    suppressApplicationTitle/disableAnimations/useAtlasEngine/
    experimental.* from current mios.toml [theme])
Before this hook, ONLY the irm|iex Get-MiOS.ps1 entry path triggered
those substitutions. Every install.ps1 / mios-update / re-run of
build-mios.ps1 left the deployed dashboard + WT settings.json STALE,
so toml/omp.json edits looked like they had no effect (operator
iteration loop on, which uninstalled + reinstalled
multiple times waiting for the dashboard to update -- it never did
because the Step 1-8 chain never ran).

Operator pivot "irm|iex is the main entry point for ALL
things MiOS... FIX all in code!" -> all entry paths now route through
the same Install-MiOS* function bodies, sourced from the canonical
Get-MiOS.ps1 via the MIOS_GETMIOS_FUNCTIONS_ONLY=1 dot-source gate.

<!-- mios-src:2381b9e1eabd from build-mios.ps1:8338-8360 -->

### CRITICAL

CRITICAL: do NOT use `. $path` -- PowerShell's parser
default encoding is cp1252 in many host configs (PS 5.1
always; pwsh 7 only when launched from a non-UTF8
console), and Get-MiOS.ps1 contains UTF-8 box-drawing
chars (│ ╭ ╮ ╰ ╯ ─). cp1252 reads `│` (UTF-8 E2 94 82)
as `â”‚` (mojibake) which crashes the parser with
"Unexpected token 'â”‚'". Read the file as explicit
UTF-8 and create a scriptblock from the string. dot-
sourcing the scriptblock runs in caller scope so all
function defs land here (build-mios.ps1's scope).

<!-- mios-src:0f67710b9694 from build-mios.ps1:8370-8379 -->

### ── Window resize (best-effort) + dashboard mode...

── Window resize (best-effort) + dashboard mode ──────────────────────────────
Default = 'log' (linear, sequential phase + step log lines). The
framed in-place dashboard has been a recurring source of
host-compat issues -- some hosts honor [Console]::SetCursorPosition
only intermittently, the probe can't catch every misbehavior, and
the failure mode (frames stacking forever) is awful. Linear log is
always correct.

Operators who specifically want the framed live dashboard can
opt in by setting $env:MIOS_DASHBOARD_MODE='interactive' before
launching. The probe is still run as a sanity-check in that case
so the opt-in falls back to log mode if the host is genuinely
broken.
80x30 EXACTLY -- per feedback_mios_terminal_dimensions.md: "every
spawned window must open at exactly 80 cols x 40 rows to match the
dashboard frame." Anything wider creates transient state that the
dashboard's strict-clamp width logic in Show-Dashboard would have
to compensate for; cleaner to never go wide in the first place.

<!-- mios-src:28e4d7a1667c from build-mios.ps1:8409-8426 -->

### Linear-log mode is the DEFAULT. Operator complaint: "the...

Linear-log mode is the DEFAULT. Operator complaint:
  "the spawned powershell window from irm|iex mios.bat entry still
   flickers/pins to shells top row and flashes everytime a new print
   occurs"
That's the symptom of interactive (in-place repaint) mode -- every
Show-Dashboard call rewrites the framed dashboard at the cursor-tracked
top row, and conhost/WT pseudo-console tears visibly on per-row
SetCursorPosition + Write. Linear log mode just streams Write-Host
lines, no repaint, no flicker. Operators who specifically want the
framed live dashboard opt in via $env:MIOS_DASHBOARD_MODE='interactive'.

<!-- mios-src:5e9e635133f9 from build-mios.ps1:8428-8437 -->

### Box-row helper -- guarantees every banner row is exactly...

Box-row helper -- guarantees every banner row is exactly $DW visible
chars wide, regardless of content length, so the right border lines
up with the top/bottom corners. Previous hand-rolled padding used
the wrong length for the inner string (counted "MiOS $version ..."
instead of "'MiOS' $version ..." -- the apostrophes added 2 chars
the pad math missed, so the title row was 2 cols wider than the
top frame -- the operator's "framing is broken" symptom).

<!-- mios-src:3a18f5cb572a from build-mios.ps1:8449-8455 -->

### Top-of-script banner. Title + tagline lines resolve through...

Top-of-script banner. Title + tagline lines resolve through mios.toml
[messages.installer_banner] (SSOT). Operator rebrands via mios.html.
Vendor fallbacks below preserve the existing wording when no TOML
is reachable. {version} placeholder substitutes $MiosVersion.

<!-- mios-src:f438de4e5314 from build-mios.ps1:8465-8468 -->

### Background spinner heartbeat. Writes a single character at...

Background spinner heartbeat. Writes a single character at
(SpinnerRow, SpinnerCol) every 120 ms so the operator sees the
script is still alive even when the main render loop is blocked
on a long sub-process.

Race protection: dashSync.Rendering is set to $true by the main
thread immediately before Show-Dashboard writes its rows, and
cleared afterwards. The heartbeat skips its write while that
flag is set.

<!-- mios-src:d56db4d47f65 from build-mios.ps1:8509-8517 -->

### NO-LOCAL-DEPS direct installer for the Phase-0 platform...

NO-LOCAL-DEPS direct installer for the Phase-0 platform prereqs (operator
"without ANY local dependencies"). Used when winget is absent OR
its install failed -- everything pulls from upstream GitHub releases or the
built-in `wsl --install`, so a clean machine bootstraps with nothing
pre-installed. Fail-soft: returns $false on any miss so the caller falls
through to the existing required-prereq failure (never worse than before).

<!-- mios-src:93d488c2bd66 from build-mios.ps1:8568-8573 -->

### Auto-install Phase 0 prerequisites. Per operator "without...

Auto-install Phase 0 prerequisites. Per operator "without ANY local
dependencies": winget is an OPTIONAL accelerator; each prereq also has a
direct path (git -> PortableGit, wsl -> built-in `wsl --install`, podman ->
containers/podman release), so a fresh machine with no winget still
bootstraps end-to-end. The prereq catalog resolves through mios.toml
[bootstrap.prereqs] (SSOT) so operators can swap implementations via mios.html.

<!-- mios-src:bd6e38ef2030 from build-mios.ps1:8626-8631 -->

### Provision .wslconfig FIRST, before any podman-machine init....

Provision .wslconfig FIRST, before any podman-machine init.
WSL2 reads .wslconfig at utility-VM start; if we write it after
podman has already spawned the VM, mirrored mode + firewall=false
never apply until the next `wsl --shutdown`. Operator-flagged
cockpit + every other container port timed out from
Windows because the VM came up in NAT mode while Phase 4's
post-hoc .wslconfig write said mirrored. Phase 4 still re-calls
this (idempotent) so any path that skips Phase 3 still lands
the config.

<!-- mios-src:377e61b450cf from build-mios.ps1:8896-8904 -->

### Check via Podman API first (covers rootful machine-os...

Check via Podman API first (covers rootful machine-os distros inaccessible via wsl.exe).
Accept BOTH the canonical "MiOS-DEV" and the legacy "MiOS-BUILDER" names so existing
installs don't get redundantly recreated. If only the legacy name is found we adopt it
in-place by re-pointing $BuilderDistro -- the operator can `podman machine rm` and
re-run for the canonical name.

<!-- mios-src:c997616d3e6a from build-mios.ps1:8909-8913 -->

### `(?i)` = case-insensitive. Different podman versions print...

`(?i)` = case-insensitive. Different podman versions print
the Running column as `true`/`false` (lowercase) or
`True`/`False` (capitalized); the previous regex was
case-sensitive on `true` and silently missed running
machines on capitalized-output builds, leading the script
to fall through into init and then hit "vm already exists".

<!-- mios-src:a2272e4c0732 from build-mios.ps1:8917-8922 -->

### Generic start failure -- registration exists but won't...

Generic start failure -- registration exists but won't start.
Force-remove so the subsequent New-BuilderDistro init has a
clean slate. This catches cases where the previous run was
SIGINT'd mid-init and left the machine in an unstartable
half-provisioned state. podman machine rm with --force is
destructive of THE BUILD VM only -- no MiOS image / no
operator data lives there yet at Phase 3, so this is
always safe at this point in the pipeline.

<!-- mios-src:3df50ee4a2ac from build-mios.ps1:8961-8968 -->

### Belt-and-braces sweep

Belt-and-braces sweep: even if NONE of the three detection
paths above (Running probe, Stopped+start probe, wsl.exe
legacy probe) flagged the machine as live, podman may still
have a registration on disk for $BuilderDistro from a prior
SIGINT'd / aborted run. Hitting `podman machine init` on an
existing registration produces:
    Error: vm "MiOS-DEV" already exists on hypervisor
which the dashboard surfaces as a Phase 3 FATAL with no
recovery path that the operator can act on.

Pre-purge: ask `podman machine ls` (any state, any case) for
the registration. If it exists we KNOW the previous detection
paths considered it not-startable, otherwise $machineRunning
would already be $true. Force-remove so init has a clean
slate. Safe at Phase 3: no MiOS image / operator data lives
in the dev VM yet, and the rebuild is what the operator
signed up for by re-running the bootstrap.

<!-- mios-src:8cd4e4ef48bc from build-mios.ps1:8986-9002 -->

### Even if podman-machine has NO registration, the underlying...

Even if podman-machine has NO registration, the underlying
WSL distro side can still hold a leftover registration --
especially after `podman machine rm` succeeded but the
WSL distro unregister step failed (or was never reached
by an interrupted run). The init then explodes with:
    Error: vm "MiOS-DEV" already exists on hypervisor
because the WSL-side hypervisor already has the distro.
Sweep both candidate names: the canonical "podman-MiOS-DEV"
that podman init creates, and the bare "MiOS-DEV" that the
rename step (Rename-PodmanDevDistro) produces.

<!-- mios-src:2d4bac423d0d from build-mios.ps1:9010-9019 -->

### Invoke-MiosOverlaySeed is deliberately NOT called anymore....

Invoke-MiosOverlaySeed is deliberately NOT called anymore.
It was the legacy PACKAGES.md fenced-block parser that ran
`dnf5 install` per ```packages-*``` block. As of the
SSOT is mios.toml `[packages.<section>].pkgs` (resolved via
automation/lib/packages.sh), and PACKAGES.md was relegated to
docs at usr/share/doc/mios/reference/PACKAGES.md. The legacy
function's path check now warns "overlay seed skipped" on every
run because it looks at the moved path -- pure noise that
confused the operator's "ignition failed" reading on.
Removed from the call chain. The function body itself is left
in place under a deprecation guard so any stale external caller
still loads cleanly; bare invocation is now a no-op.

The actual overlay work happens below in Invoke-MiosQuadletOverlay,
which `git fetch + reset --hard FETCH_HEAD`s mios.git to / inside
MiOS-DEV (the canonical "/ IS the git working tree" surface).

<!-- mios-src:371f904803dd from build-mios.ps1:9033-9048 -->

### Quadlet/systemd overlay -- mounts mios.git into MiOS-DEV's...

Quadlet/systemd overlay -- mounts mios.git into MiOS-DEV's / via
`git fetch + reset --hard`, enables sysusers/tmpfiles, runs the
canonical fetcher set (fonts, oh-my-posh, ollama). Heavy services
(mios-ai, mios-forgejo-runner) are opt-in via MIOS_DEV_ENABLE_AI=1
/ MIOS_DEV_ENABLE_RUNNER=1. Idempotent via
/var/lib/mios/.quadlet-overlay-seeded sentinel.

<!-- mios-src:2b2fb551336f from build-mios.ps1:9050-9055 -->

### Layer MiOS build essentials onto MiOS-DEV. Per...

Layer MiOS build essentials onto MiOS-DEV.

Per feedback_mios_dev_equals_mios.md: the dev VM is MiOS in full
parity. machine-os 6+ is the LOCKED base (per operator), but it
ships stripped down -- no mkpasswd, no openssl, no passlib, no
bootc -- so MiOS content has to LAYER ON TOP at provisioning time
(NOT at runtime inside the driver, which would paper over broken
provisioning). Install the minimum the build pipeline needs so the
driver can assume "everything MiOS has" is present when it starts.

Full feature parity (every package, container, flatpak, model)
still happens via `bootc switch localhost/mios:latest + reboot`
at the end of mios-build-driver -- this step is just the seed for
the build to RUN.

<!-- mios-src:729c9be88b9f from build-mios.ps1:9058-9071 -->

### NB: on Fedora 44 the `mkpasswd` binary moved out of `whois`...

NB: on Fedora 44 the `mkpasswd` binary moved out of `whois` into
its own `mkpasswd` package -- include both so the build essentials
set is correct on every Fedora vintage the dev VM might run.

iptables/nftables: machine-os 6+ ships without a firewall backend,
which makes podman's netavark networking refuse to set up the
build-container's network ("Must provide a valid firewall backend,
got iptables"). Without one, every `podman build` in the dev VM
dies at the first RUN step that needs network. Install BOTH so
netavark picks whichever is preferred on a given Fedora vintage.

MUST wrap in EAP=Continue + PSNativeCommandUseErrorActionPreference=$false:
dnf emits "Failed to set locale, defaulting to C.UTF-8" to stderr
(a harmless warning when LANG isn't set in the WSL distro), and
also "Transaction failed:" lines for non-critical post-scriptlet
errors (e.g. whois symlink-creation, which doesn't actually break
the install). Under PS 7.4+ defaults (EAP=Stop +
PSNativeCommandUseErrorActionPreference=$true), either of those
throws straight to the outer FATAL handler. The actual install
success is checked via $LASTEXITCODE below.
SSOT: dev VM essentials list comes from the layered mios.toml
chain. Per operator: Epiphany configurator HTML edits flow
through to every consumer.

Layered resolution (highest → lowest precedence):
  1. M:\etc\mios\mios.toml          -- HOST overlay (Epiphany
                                       configurator's save target;
                                       visible from Windows AND
                                       from MiOS-DEV via /mnt/m/)
  2. M:\usr\share\mios\mios.toml    -- VENDOR copy from mios.git
First layer with a non-empty [packages.dev_vm_essentials] wins.

<!-- mios-src:455c019ac7ce from build-mios.ps1:9074-9104 -->

### dnf's exit code is unreliable on rootful machine-os: %post...

dnf's exit code is unreliable on rootful machine-os: %post / %triggerin
scriptlets fail with "Transport endpoint is not connected" because there's
no systemd PID 1 to take daemon-reload, and harmless cosmetic ones (e.g.
whois-man alternatives symlink) also exit non-zero. Verify by `rpm -q`
against the actual package names instead. Note: `iptables` resolves to
`iptables-legacy` on Fedora 44; rpm -q on the source name returns
"package iptables is not installed" even when the alternatives provider
IS installed -- so query the resolved provider too.

<!-- mios-src:bdf89324501c from build-mios.ps1:9157-9164 -->

### ── Full MiOS OCI image parity at overlay time...

── Full MiOS OCI image parity at overlay time ──────────────────
"podman-MiOS-DEV machine doesn't have the
full packages list and flatpaks installed at overlay time --
ALL sourced from the toml embeds ... podman-MiOS-DEV = full
MiOS OCI image(s) parity".  This step iterates
[packages.dev_overlay].sections (22 sections by default --
base/security/utils/build-toolchain/containers/cockpit/storage/
virt/gpu-*/gnome-flatpak-runtime/ai/sbom-tools/self-build/
network-discovery/updater/cockpit-plugins-build/k3s-selinux-build/
uki) and layers every [packages.<section>].pkgs into the dev VM.
Then installs every ref in [desktop].flatpaks.

Toggle via mios.toml [bootstrap].dev_overlay_full = false for a
minimal overlay (essentials only).  Default = full parity per
operator directive.  The trade-off is bootstrap time -- full
parity adds 20-40 min of dnf + flatpak network/disk work on
first install.  The reward: every layered RPM and flatpak the
MiOS OCI image carries is already present in podman-MiOS-DEV
without a `bootc switch` reboot.

<!-- mios-src:293647e62132 from build-mios.ps1:9194-9212 -->

### Process each section. Read [packages.<section>].pkgs. NOTE...

Process each section. Read [packages.<section>].pkgs.
NOTE: build the regex via SINGLE-QUOTED concat so `$`
inside the pattern stays a literal `$` for PS-string-eval
then resolves to the regex line-end anchor.  The previous
double-quoted `"...\$..."` form had PowerShell collapse
`\$` to `$` which the regex engine then treated correctly
-- BUT the `$` mid-string was being seen as a sub-expr
opener by some PS hosts (operator's run hit zero matches
on every section), so single-quoted is the safer shape.

<!-- mios-src:56ed5044aebd from build-mios.ps1:9245-9253 -->

### Per-ref install with explicit exit-code check. "NOT AT ALL...

Per-ref install with explicit exit-code check.
"NOT AT ALL A MIOS OVERLAY...
nautilus / epiphany not found".  Previous version
silently succeeded on every flatpak install
regardless of actual outcome (the inner bash used
`command -v flatpak ... && flatpak install ... ||
echo deferred` which always exits 0 because of the
`|| echo`).  Now we run flatpak directly, capture
the exit code, and log Pass / Fail per ref so the
operator can see exactly what made it into the dev
VM.  `rpm -q flatpak` first to gate -- if flatpak
isn't even installed (machine-os 6.0 base ships
without it), skip the whole pass with one warn
instead of N "deferred" lines.

<!-- mios-src:11747fbd7ccf from build-mios.ps1:9306-9319 -->

### dbus-launch must be on PATH before any `flatpak install`...

dbus-launch must be on PATH before any
`flatpak install` runs. The podman-machine-os
6.0 base image ships dbus-broker (system bus
only) but NOT dbus-x11 (session bus launcher),
so flatpak's pre-install token-request step
fails with:
    error: Failed to execute child process
    "dbus-launch" (No such file or directory)
The retry-with-arch path then dies the same
way and the install loop reports 0/N OK.
Operator-flagged. Cheap fix: install
dbus-x11 (and its xauth dep) here once, before
any flatpak call -- under 200 KB, runs in
~2-3s. Idempotent: dnf no-ops on second run.

<!-- mios-src:6dda4497297c from build-mios.ps1:9332-9345 -->

### Pre-install GNOME runtime + SDK ONCE before the per-app...

Pre-install GNOME runtime + SDK ONCE before the
per-app loop. org.gnome.Software (and other GNOME
apps) fail with "no compatible runtime" if the
platform isn't already pulled. Running this here
avoids 6x parallel runtime resolution in the
per-ref loop. Errors are non-fatal -- if the
GNOME apps don't need it, this is a no-op.

<!-- mios-src:da5d16ca867d from build-mios.ps1:9354-9360 -->

### Refresh flathub's appstream so the per-app loop resolves...

Refresh flathub's appstream so the per-app loop resolves
cleanly. The old explicit `org.gnome.Platform//master` pre-pull
errored "Nothing matches org.gnome.Platform in remote flathub"
(//master is a gnome-nightly branch, NOT flathub -- flathub uses
versioned branches;). Runtimes are pulled as deps by
each per-app install below, so the pre-pull was redundant anyway.

<!-- mios-src:0a4c64221216 from build-mios.ps1:9366-9371 -->

### Parse "remote:appid" form; default to flathub when no...

Parse "remote:appid" form; default to flathub when no prefix.
Operator-flagged nautilus/ptyxis shims
errored "app/<id>/x86_64/master not installed" because
the install loop hardcoded `flathub` and our toml
entries used `gnome-nightly:org.gnome.Nautilus.Devel`
+ `fedora:org.gnome.Epiphany`.

<!-- mios-src:9f15e3952fde from build-mios.ps1:9401-9406 -->

### `dbus-run-session --` spawns a one-shot D-Bus session bus...

`dbus-run-session --` spawns a one-shot D-Bus
session bus, runs the command, then tears it
down. Without it, flatpak's pre-install token-
request step ("Requesting tokens for remote
fedora") tries to dbus-launch into a session
that doesn't exist and dies with:
    error: Could not connect:
    No such file or directory
which is what killed `fedora:org.gnome.Epiphany`
for the even after dbus-x11
was installed. dbus-run-session is part of dbus
(always present on Fedora-base machine-os).

<!-- mios-src:af7ca00a8730 from build-mios.ps1:9421-9432 -->

### ── NVIDIA WSL userland (gated on /dev/dxg present in dev...

── NVIDIA WSL userland (gated on /dev/dxg present in dev VM) ───
"WSLg + GPU-PV or CDI" -> "WSLg + NVIDIA
Vulkan ICD". Installs NVIDIA's userspace Vulkan ICD + GLX/EGL
libs from the official CUDA repo. Userland-only; no kernel
modules. The script self-detects /dev/dxg + /mnt/wslg presence
and exits cleanly on non-WSLg substrates (bare-metal / Hyper-V
/ OCI). Idempotent.

<!-- mios-src:887ac5d80838 from build-mios.ps1:9479-9485 -->

### Disable netavark's firewall management. WSL2's kernel...

Disable netavark's firewall management. WSL2's kernel doesn't ship
the iptables/nf_tables netfilter modules that netavark expects, so
even with the iptables BINARY present (whois package above) the
build container's network setup fails with:
  "setup network: netavark: Must provide a valid firewall backend"
The build doesn't need iptables-managed isolation -- it just needs
outbound network for package pulls. firewall_driver=none tells
netavark to skip firewall rule installation; the bridge interface
still works for outbound traffic via WSL2's normal NAT.

<!-- mios-src:087e4a4b72d7 from build-mios.ps1:9503-9511 -->

### ── MiOS terminal experience seed inside dev VM...

── MiOS terminal experience seed inside dev VM ──────────────────
Symlink /usr/libexec/mios + /usr/share/mios to the M:\ overlay
(mios.git's working tree visible at /mnt/m/ via WSL automount)
so mios.git's existing /etc/profile.d/mios-*.sh scripts can find
/usr/libexec/mios/mios-dashboard.sh + /usr/share/mios/oh-my-posh/
at the canonical paths -- without doing a heavy file-by-file
copy. After bootc switch at end-of-build, the OCI image's real
/usr/{libexec,share}/mios ride on top via composefs and the
symlinks become irrelevant.

Drop a single bridge in /etc/profile.d/ that sources mios.git's
profile.d scripts FROM /mnt/m/ on every interactive login. Auto-
disables once /usr/share/mios is real (post-bootc-switch).

<!-- mios-src:1182483c47ad from build-mios.ps1:9535-9547 -->

### ── Ensure the `mios` user exists (idempotent)...

── Ensure the `mios` user exists (idempotent) ────────────────────────
Per (`getpwnam(mios) failed 17 / User not found`):
in BootstrapOnly mode, the OCI build's quadlet-overlay step (which
runs systemd-sysusers and creates uid 1000=mios) is DEFERRED and
never executes. Without the mios user, /etc/wsl.conf default=mios
fails on the next `wsl -d podman-MiOS-DEV` invocation (the prior
behaviour log message "[Phase 3] -- next entry uses mios as default"
was a lie -- the user didn't exist yet). Create it here so every
verb that enters the dev distro (mios dev, mios-dev.lnk, the
mios-launch.ps1 -Verb dev path) lands as a real user.

<!-- mios-src:c5299e99f47a from build-mios.ps1:9561-9570 -->

### Set a known password so Cockpit PAM and operator-typed sudo...

Set a known password so Cockpit PAM and operator-typed sudo
prompts work. Operator can change it any time inside the dev
VM with `passwd`. The MiOS canonical default is `mios`.

<!-- mios-src:0ee09a452d68 from build-mios.ps1:9578-9580 -->

### ── /etc/wsl.conf [boot] systemd=true + [user] default=mios...

── /etc/wsl.conf [boot] systemd=true + [user] default=mios ─────────
[boot] systemd=true MUST be set or the distro boots without systemd
as PID 1; smoke tests then see state='offline' and Quadlets / the
flatpak first-boot service / every service-coupled bootstrap step
fails. WSL >= 0.67.6 honors this on next terminate+reentry.
[user] default=mios so `wsl -d podman-MiOS-DEV` / `wsl -d MiOS-DEV`
land in the mios shell; only written if the user exists or the
distro entry breaks.

<!-- mios-src:3c7a4e613cdd from build-mios.ps1:9593-9600 -->

### ── btop MiOS theme + 80x20 preset for the dev VM...

── btop MiOS theme + 80x20 preset for the dev VM ─────────────────────
image #15: btop reports "Width = 75 Height = 18,
Needed 80 x 24". btop runs INSIDE the dev VM (Linux) so the Windows
config at M:\MiOS\btop doesn't apply -- it reads ~/.config/btop/.
Source files are exposed via WSL automount at /mnt/m/MiOS/btop/.
Stage to BOTH the mios user (canonical) and root (in case of root
sessions). Symlink approach so operator edits to mios.toml -> rebuild
omp.json + theme flow through automatically.

<!-- mios-src:79eb876d0b02 from build-mios.ps1:9652-9659 -->

### System-wide fallback first. mios-btop.sh exports...

System-wide fallback first. mios-btop.sh exports
BTOP_CONFIG_DIR=/etc/btop when the user has no ~/.config/btop,
so this guarantees the MiOS preset/palette renders even if the
per-user copy is missing (e.g. /=git home edge case).
screenshot: btop launched with btop's
compiled-in defaults (preset 3 = cpu+net, update_ms=2000)
because no config was found at $HOME/.config/btop. With this
/etc/btop/ copy in place, the resolver hits it unconditionally.

<!-- mios-src:36063df6b42d from build-mios.ps1:9661-9668 -->

### ── Flatpak convenience symlinks (operator: epiphany /...

── Flatpak convenience symlinks (operator: epiphany / nautilus etc. should work) ─
ran `nautilus` and `epiphany` after install, got
"command not found" -- "LIAR!!!!!!". Install log said the flatpaks
installed OK; they did, but flatpak exports binaries as their full
app IDs (org.gnome.Epiphany, etc.) under /var/lib/flatpak/exports/bin/,
NOT as short names. Operator expects `epiphany`, `nautilus`, etc.
to work directly. Symlink the canonical short names into /usr/local/bin/
pointing at the flatpak wrappers.

<!-- mios-src:dbc8dbde2c2c from build-mios.ps1:9698-9705 -->

### Write the seed script to a tempfile on M:\ (visible inside...

Write the seed script to a tempfile on M:\ (visible inside the dev
VM at /mnt/m/) and invoke bash on the path. Piping the script to
`bash` via PowerShell stdin gets CRLF-mangled -- bash sees `set -\r`
and aborts with "set: -: invalid option" on line 1, killing the
whole script before any work runs (operator log: "bash: line 1:
set: -: invalid option ... syntax error: unexpected end of file
from `if' command on line 9").

<!-- mios-src:3c05b104ebd3 from build-mios.ps1:9727-9733 -->

### Compile MiOS dconf overrides into the system-db cascade....

Compile MiOS dconf overrides into the system-db cascade.  The
files at /etc/dconf/db/local.d/00-mios-theme + /etc/dconf/profile/
user ship in mios.git's overlay but only take effect after
`dconf update` builds the binary system-db.  Without this, the
adw-gtk3-dark + prefer-dark defaults stay inert and every GTK
app boots with the upstream light Adwaita fallback (operator-
flagged "not the mios.toml defined prefer-dark mode
yet").

<!-- mios-src:152d6e5d03ff from build-mios.ps1:9762-9769 -->

### bash -c (NOT -lc) -- the dconf update step must not trigger...

bash -c (NOT -lc) -- the dconf update step must not trigger
/etc/profile.d/ cascade (zz-mios-motd.sh -> mios mini -> fastfetch
render) which can hang here under WSL's pre-systemd boot state
and stall the entire install. dconf is in $PATH at /bin/dconf
without login-shell PATH-extension.
Operator-flagged install "stuck here" at this step.
NOTE: keep this bash -c free of embedded double-quotes and parens --
PowerShell's native-arg quoting mangles them passing to wsl.exe (the
'syntax error near unexpected token (' came from the old
echo message's "(...)"). Plain words only.

<!-- mios-src:0f23a11c7ad3 from build-mios.ps1:9776-9785 -->

### Bibata-Modern-Classic cursor install. mios.git's...

Bibata-Modern-Classic cursor install. mios.git's automation/57-gnome.sh
bakes Bibata into the bootc OCI image MANDATORILY, but the dev VM
(podman-MiOS-DEV = podman-machine-os Fedora 44 + MiOS overlay) doesn't
run that automation. Without this overlay step, dconf points at
'Bibata-Modern-Classic' but the theme dir doesn't exist -> libXcursor
silently falls back to default (operator-flagged "not
seeing bibata cursor that is the GLOBAL MiOS defaults"). Match the
image install path so the dev VM has the same cursor surface.

<!-- mios-src:718769453bbc from build-mios.ps1:9791-9798 -->

### Base64-wrap the bibata script. Passed inline, its embedded...

Base64-wrap the bibata script. Passed inline, its embedded
double-quotes/parens/$(...) get mangled by PowerShell's native-arg
quoting into bash syntax errors ("unexpected token ("
on the size echo). Encoding the whole script means ONLY base64 chars
reach the bash -c argument -- nothing to mangle. LF-normalize first.
Also guards the version/download/tar steps with || (a bare
`var=$(pipeline)` exits under set -e when the pipeline fails).

<!-- mios-src:ab82135e404c from build-mios.ps1:9816-9822 -->

### MiOS AI CLI install

MiOS AI CLI install: Claude Code + Gemini CLI globally via npm.
Both are Node.js CLIs distributed via npm, so they don't fit RPM
packaging. The helper script reads mios.toml [packages.ai].
npm_globals to discover what to install -- operators can extend
the list via /etc/mios/mios.toml or ~/.config/mios/mios.toml.
ON by default; MIOS_SKIP_AI_CLIS=1 to skip.

<!-- mios-src:cc6bd05d2ddf from build-mios.ps1:9869-9874 -->

### ── Unified mios-home + locale reconcile (single root pass)...

── Unified mios-home + locale reconcile (single root pass) ──────────────
Every Phase-3 seed step above ran against the LIVE distro, which still
defaults to the bundled `user` (UID 1000) -- /etc/wsl.conf [user]=mios only
takes effect after the shutdown below. So any step that wrote under
/var/home/mios as the default user left files owned by UID 1000, and the
mios user (UID 992) then hits "path ... not owned by the current user" +
oh-my-posh "permission denied" writing ~/.cache. Separately, the
podman-machine-os base ships only `C.utf8` (NOT `C.UTF-8`), so the image's
/etc/locale.conf LANG=C.UTF-8 makes every login emit
`setlocale: cannot change locale`. Reconcile BOTH here, from one root pass,
so the dev VM deploys clean every time. Dev-substrate only -- the bootc
image keeps its own Fedora C.UTF-8 locale.conf and bakes home ownership.

<!-- mios-src:9bbd976cb5e8 from build-mios.ps1:9886-9897 -->

### The overlay seed wrote /etc/wsl.conf [user] default=mios so...

The overlay seed wrote /etc/wsl.conf [user] default=mios so future
`wsl -d podman-MiOS-DEV` invocations land in the mios user (not the
bundled `user` UID 1000). But /etc/wsl.conf is read at distro
START -- the live instance running RIGHT NOW was launched with the
pre-seed config and still defaults to `user`. Terminate the distro
so the next entry (menu option 1 or 5) re-launches with the new
default user. Idempotent: if the distro isn't running, --terminate
is a no-op.
Full `wsl --shutdown` (utility VM + all distros) instead of just
`wsl --terminate <distro>`. The terminate path only restarts the
distro process, leaving the WSL2 utility VM running with whatever
networkingMode it booted in. Symptom if the utility
VM started in NAT mode earlier in the install (e.g. due to a
wsl --list -v probe in Phase 1 firing before .wslconfig was on
disk), .wslconfig's mirrored mode never takes effect and every
container port stays unreachable from Windows. shutdown forces
a clean utility-VM restart so the operator's next MiOS terminal
launch picks up mirrored + firewall=false + the /etc/wsl.conf
[user]=mios default user in one shot.

<!-- mios-src:7f2112589e35 from build-mios.ps1:9911-9929 -->

### ── Phase 4 -- WSL2 .wslconfig...

── Phase 4 -- WSL2 .wslconfig ───────────────────────────────────────────
Phase 3 already wrote .wslconfig BEFORE initializing the dev VM
(so mirrored networking + firewall=false applied at first boot).
This phase is the idempotent re-check + post-Phase-3 firewall
rules. Set-MiosWslConfig is a no-op if all required keys already
match.

<!-- mios-src:c95657189c3b from build-mios.ps1:9937-9942 -->

### Windows Firewall inbound rules for MiOS container ports....

Windows Firewall inbound rules for MiOS container ports. SSOT is
mios.toml [ports].* + [ports.lan_firewall].profiles/.expose.
Without these, mirrored networking carries the WSL port bind onto
Windows' all interfaces but Defender blocks inbound from any LAN
device (phone, tablet, second laptop). Operator-flagged.

<!-- mios-src:bcc14942f788 from build-mios.ps1:9946-9950 -->

### ── Bootstrap finalize: smoke test -> Windows install ->...

── Bootstrap finalize: smoke test -> Windows install -> launcher ───────
The auto-rename (podman-MiOS-DEV -> MiOS-DEV) is OFF by default
because podman's WSLDistroName() hardcodes the `podman-` prefix
-- a renamed distro breaks every `podman machine start/init/ssh`
with WSL_E_DISTRO_NOT_FOUND. User-facing surfaces (dashboard,
mios-dev launcher, icons, app menu) already hide the prefix, so
operators see "MiOS-DEV" everywhere they look while the actual
WSL distro stays as "podman-MiOS-DEV" for podman's sake. Set
$env:MIOS_RENAME_DISTRO=1 to opt in.

<!-- mios-src:04ea8ecbc61b from build-mios.ps1:9969-9977 -->

### ── -BootstrapOnly: exit cleanly here...

── -BootstrapOnly: exit cleanly here ─────────────────────────────────────
The curl/iex entry path stops here. The operator now has:
  * MiOS-DEV WSL2 distro (renamed, podman-managed, overlay applied)
  * Windows-side oh-my-posh / Geist / Nerd Font / theme installed
  * MiOS install root on M:\MiOS\ (or fallback) with bin/icons/themes
  * Desktop + Start Menu shortcuts including "Build MiOS"
They can now click "Build MiOS" to drive the OCI image build (which
re-runs this script with -BuildOnly).

<!-- mios-src:825122d9e0e2 from build-mios.ps1:9989-9996 -->

### Hard gate the script-level auto-chain at line ~6915. The...

Hard gate the script-level auto-chain at line ~6915. The
`return` below exits this function but the script-level
epilogue still fires the auto-chain unless we set the env
sentinel here. Per feedback_mios_bootstrap_stops_at_dev_ready:
bootstrap MUST stop at the hint banner; build is operator-
triggered via `mios build`.

<!-- mios-src:2a29af26fa7c from build-mios.ps1:9999-10004 -->

### ── Operator-facing end-of-Pass-2 summary...

── Operator-facing end-of-Pass-2 summary ────────────────────
The bootstrap STOPS here. The operator decides when to fire
the build pipeline by typing `mios build` (or clicking the
MiOS Build shortcut). Per
feedback_mios_bootstrap_stops_at_mios_dev_ready memory: the
Windows entry installs everything UP TO MiOS-DEV being a
native app, then prints hint lines and returns. No auto-chain.

<!-- mios-src:b6c3ac97d9f1 from build-mios.ps1:10006-10012 -->

### Banner title + bullet list resolve through mios.toml...

Banner title + bullet list resolve through mios.toml
[messages.install_complete] (SSOT). Operator edits via mios.html
for any custom branding text. Vendor fallback below is the cold
first-run set when no TOML is reachable.

<!-- mios-src:5e6778448428 from build-mios.ps1:10015-10018 -->

### Frame chars come from mios.toml...

Frame chars come from mios.toml [branding.dashboard].frame_chars
so the install-complete banner matches every other framed surface
(Show-MiosDashboard, mios-dashboard.sh, agreement gate, etc.).
Per "headers and dashboards and framing/
piping are all scattered and not fitting because they aren't
TRULY based off the toml code as source for everything".
Vendor default '╭─╮│╰╯' if mios.toml is unreachable.

<!-- mios-src:ea3490a36718 from build-mios.ps1:10031-10037 -->

### Verb list resolves through mios.toml [verbs] (SSOT)....

Verb list resolves through mios.toml [verbs] (SSOT). Operator
edits mios.html -> mios.toml -> this banner regenerates on the
next install. No hardcoded verb names. Per operator: "toml is
the SSOT for code too!!! no hardcoding ANYWHERE!!!"

<!-- mios-src:54f3789322cb from build-mios.ps1:10065-10068 -->

### Operator can pre-fill mios.toml fields via the HTML page...

Operator can pre-fill mios.toml fields via the HTML page; the
Phase-6 prompts that follow then default to whatever was saved.
Skipped when -Unattended or MIOS_NO_CONFIGURATOR=1.

<!-- mios-src:8c43d046ece9 from build-mios.ps1:10108-10110 -->

### Bake-set policy

Bake-set policy: the MINIMAL set from mios.toml [ai].bake_models
(small Qwen + the embedding model) is ALWAYS baked into the OCI
image so a fresh install is usable fully offline without bloating
the image layer. Larger models stay SELECTABLE -- offered here as
an opt-in. This prompt only runs in the interactive local-build
path (build-mios.ps1); the Forgejo CI build sources
MIOS_LLAMACPP_BAKE_MODELS straight from install.env, so cloud/CI
builds always get just the minimal set. If the operator's chosen
default model isn't already in the minimal set, offer to bake it
too; declining means it first-boot-pulls instead of bloating the
image.

<!-- mios-src:b2644995f4a2 from build-mios.ps1:10140-10150 -->

### SINGLE-quote every value

SINGLE-quote every value: install.env is SOURCED by services (many under
`set -u`), and the sha512crypt hash is `$6$salt$digest` -- double-quotes let
the shell expand $6/$salt as unbound vars -> "line 3: $6: unbound variable"
-> EVERY install.env-sourcing service fails to start (mios-forge-firstboot,
sys-env-refresh, podman-mnt-bindings, ...). Single quotes keep the literal.
(crypt hashes + model specs never contain a single quote, so the wrap is safe.)

<!-- mios-src:138953c843cb from build-mios.ps1:10176-10181 -->

### DisplayName / Publisher / URLInfoAbout all resolve through...

DisplayName / Publisher / URLInfoAbout all resolve through mios.toml
so operators rebrand the Add/Remove Programs entry via mios.html.
Per "the Applications tag/description when
installed 'MiOS - Immutable Fedora AI Workstation' should be
defined as My Personal Operating System or similar".
Prefer [branding].tagline_app (the explicit Application-tag value);
fall back to .tagline; final fallback to the literal default.

<!-- mios-src:4c966ee1a42e from build-mios.ps1:10255-10261 -->

### MiOS Configurator launcher script in the install dir. Calls...

MiOS Configurator launcher script in the install dir. Calls the
in-VM launcher (/usr/libexec/mios/mios-configurator-launch) via
`wsl --exec` so the same code path drives both surfaces:
  - Windows Start Menu / Desktop "MiOS Configurator.lnk"
  - GNOME Dock / Activities entry on a deployed host (mios-
    configurator.desktop -> the same launcher)
On Windows this opens Epiphany flatpak via WSLg -> the configurator
window appears on the Windows desktop.

<!-- mios-src:88f5f069165f from build-mios.ps1:10279-10286 -->

### MiOS Dev Shell points at the canonical post-rename name...

MiOS Dev Shell points at the canonical post-rename name first
($DevDistro = "MiOS-DEV"); pre-rename installs still get a usable
entry via the launcher's Resolve-MiosDevDistro fallback in
mios-dev.ps1 (under $MiosBinDir). The legacy Podman Shell entry
was removed -- `podman machine ssh MiOS-DEV` fails post-rename
because podman hardcodes the `podman-` prefix in WSLDistroName(),
and "MiOS Dev Shell" already covers the same use case.
MiOS Terminal / MiOS Dev Shell route through the centering launcher
(mios-launch.ps1) so every double-click lands a borderless 80x30
acrylic window screen-centered, regardless of last-window position
WT might have remembered. -WindowStyle Hidden keeps the wrapper
pwsh invisible -- only the WT window appears.
Final native-app shortcut set (5 apps total, per operator):
  MiOS              the terminal hub (created earlier in
                    Install-MiosLauncher line ~5743)
  MiOS-DEV          dev VM dashboard (created in verbShortcuts
                    loop line ~5904)
  MiOS Config       opens mios.html in default browser
                    (created in verbShortcuts loop line ~5904)
  MiOS Help         verb reference (created in verbShortcuts
                    loop line ~5904)
  Uninstall MiOS    Add/Remove-style uninstaller (this block)

The legacy MiOS Setup / Build MiOS / MiOS Configurator / MiOS
Terminal / MiOS Dev Shell shortcuts have been retired -- those
verbs are operator-typed inside the MiOS terminal, NOT separate
native apps. ('MiOS Configurator' is the legacy long-form name
for the new 'MiOS Config' app.)
vmconnect.exe is the Hyper-V Manager's VM-connection tool. On a
MiOS Hyper-V deployment the guest's mios-hyperv-enhanced.service
patches xrdp onto the VMBus vsock transport so vmconnect lights
up Enhanced Session by default (clipboard sync, dynamic
resolution, audio, USB). The shortcut opens vmconnect with no
VM specified -- operator picks their MiOS VM from the list.

<!-- mios-src:12a04fdf0827 from build-mios.ps1:10309-10342 -->

### Stale-shortcut cleanup -- if a legacy revision dropped any...

Stale-shortcut cleanup -- if a legacy revision dropped any of
these names, remove them so the operator's Start Menu / Desktop
match the canonical 5-app set.

<!-- mios-src:dac5f36d9287 from build-mios.ps1:10356-10358 -->

### Uninstaller script. Operator-asserted contract "EVERY...

Uninstaller script. Operator-asserted contract
"EVERY failure will result in an uninstallation!! Plus make sure
MiOS uninstaller ACTUALLY removes and cleans everything up after."

Goal: every uninstall leaves Windows in EXACTLY the state it was
in before MiOS was first installed. The next install starts from
zero, no stale state to confuse the next debug iteration.

What gets removed (12 artifact categories):
  1. Podman machine ($BuilderDistro) -- stop + rm
  2. WSL distros -- $BuilderDistro + $MiosWslDistro + every
     podman-MiOS-* + MiOS-BUILDER variant (defensive, since the
     install pipeline has gone through several distro names)
  3. M:\MiOS install dir, M:\ overlay files, M:\ProgramData,
     M:\ data dir
  4. WT settings.json -- launchMode root key (only if MiOS-set),
     profiles.defaults globals (only the keys MiOS writes), MiOS
     scheme, MiOS profile, MiOS-DEV profile, podman-MiOS-* auto
     profiles
  5. PowerShell profile redirector blocks -- both pwsh 7
     ($PROFILE.CurrentUserAllHosts) AND WindowsPowerShell 5.1
     (~\Documents\WindowsPowerShell\profile.ps1) -- marker-
     delimited block removal preserves any operator-added content
     outside the markers
  6. Fonts -- Geist*.otf/.ttf + Symbols-Only Nerd Font from
     %LOCALAPPDATA%\Microsoft\Windows\Fonts + matching HKCU font
     registry entries
  7. PATH env -- M:\MiOS\bin removed from HKCU + HKLM Path
  8. HKCU uninstall reg key
  9. Start Menu folder + Desktop .lnk shortcuts (MiOS, MiOS-DEV,
     MiOS Config, MiOS Help, Uninstall MiOS, plus stale legacy
     names from prior install revisions)
 10. AppUserModelID HKCU registrations
 11. podman-machine state symlinks (the symlinks to M:\podman from
     AppData\Local, .local\share, ProgramData\containers\podman\machine)
 12. MIOS_* environment variables (HKCU + HKLM scope)

Default preserves $MiosConfigDir (per-user identity / mios.toml
operator overrides) so a re-install picks up the operator's
last config. -Purge nukes that too for true zero-state uninstall.

Non-destructive: never touches C:\MiOS, C:\mios-bootstrap (the
operator's source repos), the operator's own pwsh profile content
outside the >>> MiOS oh-my-posh init >>> markers, or any non-MiOS
WT profiles / schemes / fonts.

<!-- mios-src:69ae597e90dc from build-mios.ps1:10371-10415 -->

### Requires -Version 5.1

Requires -Version 5.1

<!-- mios-src:bc35b223480a from build-mios.ps1:10418-10418 -->

### Also nuke the MiOS\Linux Apps\ subfolder + every .lnk...

Also nuke the MiOS\Linux Apps\ subfolder + every .lnk inside it
(Files / Web / VSCodium / Flatseal / Extension Manager / Ptyxis /
System Monitor / Settings -- created by Install-WindowsBranding's
Linux Apps loop). "uninstaller STILL doesn't
uninstall everything from windows" -- previous build only removed
named .lnks, leaving Linux Apps\ orphaned in Start Menu.

<!-- mios-src:9c56e8f8b2c5 from build-mios.ps1:10645-10650 -->

### 16. FULL FORMAT M:\ partition ("FULLY format the M:\...

16. FULL FORMAT M:\ partition ("FULLY format
the M:\ partition only"). Only formats if M:\ exists AND is the
MiOS-DEV labeled partition we provisioned. NEVER touches any other
drive letter, never re-partitions, never creates/deletes drives.
Confirmation gated -- only fires when operator explicitly asked for
uninstall (not on -Quiet runs from a panicked irm|iex reap path).

<!-- mios-src:339bfb3ada4e from build-mios.ps1:10747-10752 -->

### ── Phase 9 -- Build (DEPRECATED)...

── Phase 9 -- Build (DEPRECATED) ─────────────────────────────────────────
Same self-replication enforcement applies: $BootstrapOnly is forced
to $true at line 202, so this Phase-9 invocation is unreachable from
the operator-facing flow. The build pipeline runs INSIDE MiOS-DEV
via /usr/libexec/mios/mios-build-driver; the `mios build` verb
(M:\MiOS\bin\mios-build.ps1) is the canonical operator trigger.
Kept here as dead code so git-blame still resolves legacy refs;
a follow-up commit will delete this branch outright.

<!-- mios-src:aa52bef65e72 from build-mios.ps1:10794-10801 -->

### Pass the operator-chosen model selection (Phase 6 prompt)...

Pass the operator-chosen model selection (Phase 6 prompt) through
to the build so 37-ollama-prep.sh bakes the right pair into
/usr/share/ollama/models. MIOS_AI_MODEL takes precedence over the
hardware-driven default in Get-Hardware.

<!-- mios-src:9ce01252db89 from build-mios.ps1:10803-10806 -->

### NOTE

NOTE: Rename-PodmanDevDistro now runs DURING bootstrap (after
Phase 5 + smoke test + Install-WindowsBranding) so the dev VM
is already named MiOS-DEV by the time the OCI build (Phase 9
above) completes. The build pipeline reaches the distro via
podman's API socket (SSH-forwarded) which is unaffected by
the WSL rename, OR via Invoke-DistroSh which probes both
names. No post-build rename is needed.

<!-- mios-src:ba5c29f5053b from build-mios.ps1:10814-10820 -->

### In BootstrapOnly mode, the hint banner at line ~6584...

In BootstrapOnly mode, the hint banner at line ~6584 already
printed the "Windows-side install complete" + verb hints.
Skip the second summary here -- printing it AGAIN duplicates
the operator-facing post-bootstrap UX. Per
feedback_mios_bootstrap_stops_at_dev_ready.

<!-- mios-src:d80490e92867 from build-mios.ps1:10844-10848 -->

### NO "Press Enter to close..." pause. The bootstrap finishes...

NO "Press Enter to close..." pause. The bootstrap finishes with
an automatic chain into the dev distro to run mios-build-driver
(the actual OCI build). Operator's terminal stays open in the
distro shell after the driver finishes; if they want the
bootstrap log they read $LogFile directly.

<!-- mios-src:1137b4ee955d from build-mios.ps1:10871-10875 -->

### The driver lives at M:\usr\libexec\mios\mios-build-driver...

The driver lives at M:\usr\libexec\mios\mios-build-driver
(Phase 2 cloned mios.git to M:\). WSL automounts every
Windows drive at /mnt/<letter>/, so the dev distro can
see it directly at /mnt/m/usr/libexec/mios/mios-build-driver --
no need to base64-stage the file via stdin (which had
its own dragons: PowerShell `|` corrupting binary stdin,
ProcessStartInfo.ArgumentList not existing in PS 5.1,
etc.). Just exec it from the mount.

Probe automount first so we surface a clear error if the
operator's WSL config has [automount].enabled=false. The
default machine-os config has automount on; this is a
belt-and-braces check.

<!-- mios-src:8bbb9304e5fd from build-mios.ps1:10901-10913 -->
