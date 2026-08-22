<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Primary entry point for MiOS installation; handles admin elevation, environment validation, and fresh-clone of the bootstrap repo to initiate the preflight, VM setup, and OCI build pipeline.
AI-related: /usr/share/mios/mios.toml, /etc/mios/mios.toml, /etc/mios/., /usr/share/mios/branding/mios.txt, /usr/share/mios/branding/mios, mios-dev, mios-bootstrap, mios-pull, mios-launch, mios-install
AI-functions: Disable-ConsoleQuickEdit, Resolve-MiosTomlText, Get-MiosTomlValue, Show-MiOSBanner, Show-MiOSAgreement, Invoke-MiOSAgreementGate, _Center-MiOSGateConsole, Get-MiosPalette, _hex, Test-MiOSFontInstalled, Wait-MiOSWindowsTerminalReady, Ensure-MiOSWinget

<!-- mios-src:6cb747722e65 from Get-MiOS.ps1:1-3 -->

### The canonical Windows-entry working tree per...

The canonical Windows-entry working tree per
feedback_mios_entry_m_drive_clone.md: M:\MiOS\repo\mios-bootstrap.
M:\ is provisioned to EXACTLY 256 GB by Initialize-MiosDataDisk
below. The previous %TEMP%-with-GUID approach (commit 88a0de3)
was a stopgap; M:\ is the canonical answer because the build's
downstream artifacts (OCI layers, WSL2 .tar/.vhdx, Hyper-V vhdx,
qcow2, ISO, RAW) easily exceed 50 GB and need a dedicated
data partition.

<!-- mios-src:220c3f685253 from Get-MiOS.ps1:69-76 -->

### For non-Default (build/flash/sync) actions invoked via...

For non-Default (build/flash/sync) actions invoked via `irm|iex` on a BARE Windows, the
mios-bootstrap repo isn't cloned yet -- the Default bootstrap clones it, but these actions run
FIRST (this router precedes the bootstrap). Fetch it here (git if present, else a GitHub zip)
so a factory Windows can go straight from the web one-liner to a build/flash with no manual clone.

<!-- mios-src:e1b07f8cfd55 from Get-MiOS.ps1:110-113 -->

### 4. Launch the canonical MiOS-Cat launcher. It self-elevates...

4. Launch the canonical MiOS-Cat launcher. It self-elevates via UAC, so
it ends up running as the machine Administrator -- which on a provisioned
MiOS host is the SSOT-named MiOS AI admin account (the renamed built-in
Administrator; [autounattend.service].svc_user, default 'mios-sudo').
We no longer hardcode a 'MIOS\Administrator' scheduled-task principal:
the hostname AND the admin-account name are operator-defined via SSOT, so
a fixed 'MIOS\Administrator' was wrong on every box but this dev machine.

<!-- mios-src:209802d65f28 from Get-MiOS.ps1:203-209 -->

### Self-cache-bust on entry...

-- Self-cache-bust on entry ------------------------------------------------
raw.githubusercontent.com is fronted by Fastly with `Cache-Control: max-age=300`,
so the canonical Run-dialog paste:
  powershell -ExecutionPolicy Bypass -Command "irm https://...Get-MiOS.ps1 | iex"
returns the 5-min-old cached copy after a push. Operators who test in tight
iteration cycles end up running stale code without realizing it.

Fix: every cached copy of this script self-relaunches with a `?cb=<unix-time>`
query string on first entry. Fastly treats unique URLs as distinct cache
keys, so the busted URL always pulls origin-fresh. The `MIOS_CACHE_BUSTED`
sentinel breaks the loop on the second pass (the freshly-fetched copy
doesn't re-relaunch). Once this prefix is deployed, ALL future pushes
land fresh on the next canonical-one-liner paste -- the only run that
pays the stale-cache cost is the very first one after this prefix is
itself deployed (the cached version pre-dates the prefix).
-- Resize + center the OUTER WinR pwsh window before anything paints ------
At irm|iex entry the operator's WinR-spawned pwsh defaults to 120x30
(or whatever their conhost default is). Resize to 80x40 (the
[terminal.install] default) and center on the cursor's active monitor
so the readme/acknowledgements + cache-bust banner are centered and
fit without wrap.

RESIZE ORDER MATTERS: SetWindowSize requires buffer >= window. If
current buffer < target cols, SetWindowSize fails. If current window
> target cols, SetBufferSize fails. Branch on current width.

<!-- mios-src:d7580dd3ed93 from Get-MiOS.ps1:265-289 -->

### Cleanup of stale legacy profile body BEFORE anything else...

-- Cleanup of stale legacy profile body BEFORE anything else ----------------
Earlier failed runs may have left a corrupted, mojibake'd profile.ps1 at
the legacy fallback path %USERPROFILE%\MiOS-bootstrap\powershell\. The
OUTER WinR pwsh dot-sources $PROFILE.CurrentUserAllHosts (the redirector)
at startup, BEFORE our script runs -- if the redirector's target file
has bad UTF-8 bytes, the parse error fires every time the operator pastes
the irm|iex one-liner. We can't suppress that startup load (it happened
before we got control), but we CAN delete the bad file here so it doesn't
fire AGAIN on subsequent runs. The canonical profile location is M:\MiOS\
powershell\profile.ps1 (written by Pass-1 with UTF-8 BOM); the
%USERPROFILE%\MiOS-bootstrap\ tree is purely a stale fallback artifact.

<!-- mios-src:9ade315a9d7c from Get-MiOS.ps1:331-341 -->

### Acknowledgement gate (full scrollable form -- inlined...

Acknowledgement gate (full scrollable form -- inlined because this
script runs via 'irm | iex' where $PSScriptRoot is empty so we cannot
dot-source automation/lib/agreements-banner.ps1 from a clone.

Skip paths:
  $env:MIOS_AGREEMENT_BANNER in (quiet|silent|off|0|false)  -- silent skip
  $env:MIOS_AGREEMENT_ACK   = 'accepted'                    -- declared accept (CI)
  $env:MIOS_GETMIOS_RELAUNCHED = '1'                        -- inner call inherits the outer's accept

On 'No thanks' or any non-accept reply we exit 78 (EX_CONFIG) before
any clone, fetch, or elevation -- nothing on disk is mutated.

<!-- mios-src:f87d2cc14bc4 from Get-MiOS.ps1:387-397 -->

### mios.toml reader (Get-MiOS.ps1 = ALWAYS web-only)...

-- mios.toml reader (Get-MiOS.ps1 = ALWAYS web-only) -------------------------
mios.toml is THE global dotfile (per feedback_mios_toml_html_global_dotfile
memory). EVERY tunable -- window dims, M:\ size, font, AumID, retry
delays, theming, package lists -- sources from here. The HTML
configurator edits mios.toml; every consumer reads from it.

This file (Get-MiOS.ps1) is the BOOTSTRAP entry -- invoked via
`irm | iex` for clean installs and via `mios update` for forced
refresh. Per operator architectural rule

  "ORIGIN = web entries/repos only -- no fallback to M:\ or
   anywhere else -- unless origin has been pulled and it's a
   simple 'mios build' -- that can pull from M:\ as it'd already
   exist -- then 'mios update' would ALWAYS pull from web
   regardless of clean entry, updating, etc-etc!!!"

Get-MiOS.ps1 is BOTH the clean entry AND what mios update re-runs,
so EVERY read here is web-only.  M:\ overlays / ~/.config user
overrides are honored by build-mios.ps1's `mios build` flow (which
is downstream of mios-pull and assumes M:\ is current), NOT by the
bootstrap itself.  Mixing the two would let a stale M:\ silently
override a web fetch, defeating the "clean entry forces refresh"
guarantee.

Vendor defaults are sufficient (per feedback_mios_defaults_baseline):
the stack works with no user toml present. Get-MiosTomlValue returns
its `-Default` arg if the key is missing anywhere.
Import MiOS.Install sub-modules

<!-- mios-src:4b52f4d9b404 from Get-MiOS.ps1:399-426 -->

### Return without unary-comma wrapper -- callers collect via...

Return without unary-comma wrapper -- callers collect via
@(Get-MiosTomlValue ...) which collects the pipeline-
unrolled int sequence into a fresh array. With the
unary-comma wrapper, @() got @(@(0,5,15,30)) -- a 1-
element array containing the int array -- and
$delays[0] = @(0,5,15,30) blew up Start-Sleep -Seconds.

<!-- mios-src:065f55427a08 from Get-MiOS.ps1:525-530 -->

### Default to string -- strip the SURROUNDING TOML string...

Default to string -- strip the SURROUNDING TOML string quotes (and
unescape backslash sequences for double-quoted strings). The
previous Trim('"',"'") was too aggressive: a value like
    "'MiOS' v0.2.4"
had its leading apostrophe stripped because Trim treats the char
set as a multi-set on BOTH ends. Operator-reported regression:
the installer banner rendered as `MiOS' v0.2.4` (missing leading
`'`) instead of `'MiOS' v0.2.4`.

<!-- mios-src:0112f387b3fb from Get-MiOS.ps1:537-544 -->

### Basic string

Basic string: strip and unescape \\, \", \n, \t, \r.
Sentinel uses [char]0x01 (literal SOH byte) instead of the
PS 7-only `` `u{0001} `` syntax -- PS 5.1 treats `` `u ``
as just literal "u", which leaked the placeholder
`u{0001}BS` (visible) into rendered strings.  Operator
"Initializing mios.git as the M:u{0001}BSu{0001}
working tree".  [char]0x01 works in both PS 5.1 and PS 7+.

<!-- mios-src:597bdd1cbe76 from Get-MiOS.ps1:548-554 -->

### Canonical origin URLs (SSOT: [bootstrap] mios_repo /...

-- Canonical origin URLs (SSOT: [bootstrap] mios_repo / bootstrap_repo) ------
ONE source for every web fetch below. Resolved once from mios.toml so an
operator override of the repo owner/name/ref flows to all download sites; the
vendor defaults match the [bootstrap] keys. Raw-content bases are DERIVED from
the .git clone URLs (github.com host -> raw.githubusercontent.com, drop the
trailing .git, append the ref) so the owner/name live in exactly one place.
Script-scoped + assigned AFTER Get-MiosTomlValue is defined; the fetch
functions above resolve these at call time (which is always later). The two
root chicken-egg fetches that pull mios.toml / Get-MiOS.ps1 itself keep their
inline literal -- they run before any toml exists and ARE the documented
vendor default these vars fall back to.

<!-- mios-src:3b2ebfee02b9 from Get-MiOS.ps1:574-584 -->

### Framed branded ASCII banner -- shown at the top of EVERY...

Framed branded ASCII banner -- shown at the top of EVERY MiOS
window/dashboard per operator: "EVERY WINDOW SHOULD HAVE A FRAMED
AND BRANDED BANNER OF THE MIOS ASCII BANNER ART -- EVERY WINDOW
AND/OR DASHBOARD HAS IT AT THE TOP".
Width = 80 cells (frame char to frame char). Inner width = 78.
The ASCII art block + subtitle are CENTERED within the inner
width as a single block (same approach as Show-MiosDashboard) --
not line-by-line, so the art's internal diagonal alignment is
preserved while the whole logo sits visually centered.
Box-drawing requires UTF-8 codepage (chcp 65001) -- conhost in
CP437/CP1252 mangles ++++|- to `?`. Callers must set codepage
before invoking; the agreement gate + Pass-2 inner cmd both do.

<!-- mios-src:2b0184139248 from Get-MiOS.ps1:601-612 -->

### Width

Width: cols - right_margin - 2 frame chars. SSOT from mios.toml.
Operator reported "framing too wide STILL" at the previous hard-
coded inner=78 (total=80) -- that totaled the entire 80-col
terminal width with no slack, and WT's pseudo-console
over-reports by 1 cell during the first paint, so the right
frame char wrapped. inner = cols - right_margin - 2 always
leaves right_margin cells of slack on the right edge.

<!-- mios-src:36c2e403f349 from Get-MiOS.ps1:628-634 -->

### "dashboards should be edge to edge globally!! 80x20 window...

"dashboards should be edge to edge globally!!
80x20 window is the Global benchmark!". right_margin=0 means the
frame paints col 1..N where N = WindowWidth, edge-to-edge.
Canonical launches use mios-launch.exe with --focus so WT runs in
true 80x20 cells with no chrome reservation. Non-focus launches
(operator opens WT profile directly) have chrome that eats cells
-- in those cases the operator can override right_margin via
mios.toml [terminal].right_margin.

<!-- mios-src:2927a88cbcc0 from Get-MiOS.ps1:636-643 -->

### PS 5.1 (Windows PowerShell -- the ONLY shell on a fresh...

PS 5.1 (Windows PowerShell -- the ONLY shell on a fresh Windows) does
NOT define [char] * [int]: it throws "the operation '[System.Char] *
[System.Int32]' is not defined" and kills the whole elevated bootstrap
before the agreement gate can even render. pwsh 7 silently promotes the
char to a string and repeats it; 5.1 does not. Cast to a string FIRST so
the horizontal rule repeats identically on both shells. (char + string
concatenation IS fine in 5.1 -- only the multiply was undefined.)
install-robustness.

<!-- mios-src:fa3f1731f18d from Get-MiOS.ps1:654-661 -->

### Note

Note: gate IS rendered in the elevated relaunch (Pass-2). Pass-1
(the small black box from `irm|iex`) self-elevates and exits
BEFORE this function is ever invoked -- the agreement belongs in
the properly-sized 80x40 Pass-2 conhost. The previous behaviour
short-circuited Pass-2 via $env:MIOS_GETMIOS_RELAUNCHED, which
caused the agreement to be rendered in Pass-1's tiny inherited
conhost (~80x25) where the ~104-line summary scrolled past in a
flash and the operator only saw the bottom prompt.

<!-- mios-src:3c5769a46ff8 from Get-MiOS.ps1:777-784 -->

### Ensure the conhost is 80 cells wide BEFORE rendering. Use...

Ensure the conhost is 80 cells wide BEFORE rendering. Use the same
branching SetBufferSize/SetWindowSize pattern as the WinR-entry
resize at the top of this script (lines 105-115): the order matters
because the Win32 console rule is `buffer.cols >= window.cols`.
DON'T call MoveWindow with hardcoded pixel dimensions: at 150-200%
DPI, conhost cells are ~16-25 px so a hardcoded 820 px window only
fits 33-50 cells visible while the buffer stays 80 wide -- conhost
adds a horizontal scrollbar and the operator sees what looks like a
20x40 window. Letting SetWindowSize drive the Win32 window size
auto-pixel-sizes correctly at any DPI.

<!-- mios-src:56ffc4814e0c from Get-MiOS.ps1:786-795 -->

### Don't clamp by LargestWindowSize: at 200% DPI it can return...

Don't clamp by LargestWindowSize: at 200% DPI it can return as
low as 20 rows on a 1080p monitor, which produced the operator-
reported regression "window opens but is 1/2 the size it should
be". 80x40 is the documented [terminal.install] target -- if
conhost can't fit it visibly the worst case is silent fallback
to LargestWindowSize anyway, but most setups handle it fine.

<!-- mios-src:443d4fc9b954 from Get-MiOS.ps1:799-804 -->

### Win32 helpers for re-centering on every page refresh....

Win32 helpers for re-centering on every page refresh. Operator-
reported regression: "window respawns slightly off-center every
time it refreshes the window". Conhost doesn't move the Win32
window on Clear-Host, but tiny size renegotiations (font cache /
DPI re-resolve when the active monitor changes) drift it. We
snapshot the active monitor once and re-center on every page.

<!-- mios-src:c51fce9739ae from Get-MiOS.ps1:815-820 -->

### Capture the operator's active monitor + the FROZEN target...

Capture the operator's active monitor + the FROZEN target pixel
rect ONCE at gate entry. Reading current dims via GetWindowRect on
every page lets conhost's tiny per-render renegotiations drift the
window a few pixels each time -- the operator-reported "final
agreements window still ends up off-centered". Pinning to a frozen
target X,Y,W,H on every MoveWindow is a no-op when the window is
already there, and a snap-back when conhost has drifted.

<!-- mios-src:ef1cf89c72d2 from Get-MiOS.ps1:837-843 -->

### Resolve the topmost-ancestor HWND of the conhost: WT main...

Resolve the topmost-ancestor HWND of the conhost: WT main window
when WT is the default terminal app (Windows 11 22H2+), conhost
itself otherwise. Stored once so every per-page _Center call
targets the same window. Operator-reported regression: "all
windows aren't recentering still!" was caused by GetConsoleWindow
returning the OpenConsole pseudo-host HWND (NOT WT's) -- moving
the pseudo-host had no visible effect because WT owns the actual
window.

<!-- mios-src:3e7941ddecbc from Get-MiOS.ps1:849-856 -->

### AUTO-PAGINATE so the banner ALWAYS stays visible at the top...

AUTO-PAGINATE so the banner ALWAYS stays visible at the top of
the window. Operator-reported regression: previous two-page split
had page 1 = 53 lines but the conhost only shows 40 rows, so the
banner auto-scrolled off the top before the prompt rendered. The
operator had to scroll up to see the banner -- which violated
"EVERY WINDOW HAS THE BANNER AT THE TOP".

Strategy: render the banner first, then pack as many content lines
as fit in (window_rows - banner_rows - prompt_rows - margin) before
pausing. Repeat until the agreement body is exhausted, then enter
the Acknowledged prompt loop on the final page.

<!-- mios-src:70e295c69c04 from Get-MiOS.ps1:892-902 -->

### Re-center the conhost window on the OPERATOR'S active...

Re-center the conhost window on the OPERATOR'S active monitor
captured at gate entry. Without this, conhost drifts a few
pixels per Clear-Host (font cache / DPI renegotiation).

<!-- mios-src:2940a5f389a2 from Get-MiOS.ps1:953-955 -->

### 1. ALWAYS spawn a fresh elevated pwsh window. The original...

1. ALWAYS spawn a fresh elevated pwsh window. The original `irm | iex`
host inherits whatever terminal called us (VS Code integrated, remote
session, embedded host, etc.) which often (a) isn't admin, (b) is the
wrong size for the build, and (c) breaks console cursor positioning.
A fresh top-level pwsh window guarantees a clean, properly-sized
environment regardless of where the curl was run from.

-- Auto-elevate at script entry (single UAC) -----------------------
Per operator: "irm|iex mios.bat Win + R entry should it itself auto
elevate!!! it needs admin rights to install some components without
several UAC prompts interrupting the install".

Previously this script split work into Pass-1 (user) + Pass-2 (admin
via mid-install UAC). That meant operator saw the UAC prompt halfway
through; some Pass-2 steps (M:\ partition shrink, Podman Desktop
winget install, podman machine init) need elevation, so the prompt
was unavoidable -- but firing it at the start instead means ONE
UAC interaction up-front and the entire install runs in the same
elevated session.

Sentinel: $env:MIOS_GETMIOS_RELAUNCHED prevents the elevated relaunch
from re-elevating in an infinite loop.

<!-- mios-src:094710407b2e from Get-MiOS.ps1:984-1005 -->

### Pass-1 -> Pass-2 UAC handoff prompt strings resolve through...

Pass-1 -> Pass-2 UAC handoff prompt strings resolve through
mios.toml [messages.elevation] (SSOT).  Operator rebrands via
mios.html.  Vendor defaults below are the cold-fallback set
when no toml is reachable yet (this runs BEFORE M:\ overlay
exists on first install).

<!-- mios-src:a2fb7a0a0108 from Get-MiOS.ps1:1010-1014 -->

### Capture cursor position BEFORE the UAC prompt, while the...

Capture cursor position BEFORE the UAC prompt, while the operator's
attention is still on whichever monitor they pasted from. By the
time the inner script runs (after UAC accept), Cursor.Position is
at the UAC "Yes" button location -- typically the primary monitor,
NOT necessarily where the operator was working. Embed the captured
X,Y as constants in the inner cmd so Screen.FromPoint() resolves
to the active-display before-elevation, not after.

<!-- mios-src:10b7ce9a5d41 from Get-MiOS.ps1:1021-1027 -->

### Bootstrap window dims (the elevated conhost that runs...

Bootstrap window dims (the elevated conhost that runs Pass-1 +
Pass-2 + readme/acknowledgements). Pulled from mios.toml
[terminal.install] -- vendor default 80x40 for log/output room.
The post-install MiOS APP spawn uses [terminal] (80x20, portal
feel) because the operator-facing terminal is shorter than the
install-time log window.
Compute target pixel dims HERE so they bake as literal integers
into the rendered inner cmd -- the spawned pwsh has no access
to outer-scope variables.

<!-- mios-src:27c791a6ae2d from Get-MiOS.ps1:1032-1040 -->

### Separate dims for the post-install MiOS APP spawn (80x20 --...

Separate dims for the post-install MiOS APP spawn (80x20 -- the
canonical operator-facing terminal). These bake into the inner
cmd alongside $_elevCols/$_elevRows but drive the wt.exe -p MiOS
spawn at end-of-bootstrap, NOT the bootstrap conhost itself.

<!-- mios-src:81cb2b6b22ce from Get-MiOS.ps1:1051-1054 -->

### Pass-2 exit-message strings resolved at install time from...

Pass-2 exit-message strings resolved at install time from
mios.toml [messages.pass2_exit] (SSOT). Baked as literals into
the inner-cmd heredoc below.  Single-quote the values + escape
single-quotes so the heredoc-substituted text is a valid PS
literal regardless of operator-supplied content.

<!-- mios-src:777d75b0b18a from Get-MiOS.ps1:1060-1064 -->

### AGREEMENT_ACK is intentionally NOT pre-set. Pass-2 (this...

AGREEMENT_ACK is intentionally NOT pre-set. Pass-2 (this elevated
relaunch) is where the operator reads + acks the agreement, in the
properly-sized 80x40 conhost. Pre-accepting via env would skip the
gate -- which would defeat the point of moving the gate here.
Tell the MiOS pwsh profile body to render the framed dashboard +
oh-my-posh prompt for THIS bootstrap window. The profile gates the
dashboard call on `$env:WT_SESSION OR `$env:TERM_PROGRAM='mios';
elevated pwsh in conhost has neither, so without this the install
runs in a vanilla black box. Setting it here makes the elevated
bootstrap window itself the MiOS terminal experience.

<!-- mios-src:56365e4ef5b8 from Get-MiOS.ps1:1077-1086 -->

### Force UTF-8 codepage + output encoding BEFORE any output...

Force UTF-8 codepage + output encoding BEFORE any output paints.
Without this, conhost defaults to CP437/CP1252 and the dashboard's
Unicode box-drawing glyphs (+ + + + | - + +) render as `?`. Setting
OutputEncoding alone isn't enough -- chcp 65001 changes the active
codepage for the underlying console, which is what affects glyph
substitution.

<!-- mios-src:e05b22a8a82a from Get-MiOS.ps1:1088-1093 -->

### Pass-2 transcript -- the early elevated window was...

Pass-2 transcript -- the early elevated window was historically UNLOGGED
(operator: "the incorrectly launched powershell window just dies silently
--seemingly no logs in sight!!!"). Start a transcript NOW so ANY early
failure (IRM fetch, scriptblock parse/throw, agreement gate, a preflight
'exit', or a bare error) lands in a readable file. build-mios.ps1 opens
its own mios-install-*.log later; this closes the gap BEFORE that on the
Pass-2 critical path. install-robustness.

<!-- mios-src:2625a20c5994 from Get-MiOS.ps1:1098-1104 -->

### Pre-UAC cursor location (captured by the launching pwsh...

Pre-UAC cursor location (captured by the launching pwsh BEFORE Start-
Process -Verb RunAs); use these constants instead of querying
Cursor.Position now (which would read at the UAC Yes-button click
location, defeating the active-display intent).

<!-- mios-src:d9750db7ae91 from Get-MiOS.ps1:1112-1115 -->

### DPI per-monitor v2 so Screen.WorkingArea + SetWindowPos...

DPI per-monitor v2 so Screen.WorkingArea + SetWindowPos agree on
the coordinate space (was off-by-DPI on multi-monitor setups
where the operator-reported regression "all windows aren't
recentering still" surfaced -- MoveWindow placed the window at
logical-px coords interpreted as physical-px, missing the target
monitor entirely on high-DPI secondary displays).

<!-- mios-src:0f4c7fdfe642 from Get-MiOS.ps1:1128-1133 -->

### Pixel target size -- BAKED from outer scope as literal...

Pixel target size -- BAKED from outer scope as literal integers
via @"..."@ interpolation (no backticks on $_winWPx / $_winHPx /
$_elevCols / $_elevRows / $_elevScr). The inner pwsh process
cannot see outer-scope variables (it's a fresh pwsh.exe spawn);
everything we want it to know must be substituted at template-
build time. Earlier broken edits used backticks on $_elevCols
which produced LITERAL `\$_elevCols` in the rendered script,
which evaluated to $null inner-side, multiplied by cell dims
to zero, and gave a 20x12 (basically 1x1 visible) window.
Branch on current width: SetBufferSize fails when shrinking buffer
below current window; SetWindowSize fails when growing window
beyond current buffer. Conhost rule: buffer.cols >= window.cols.

<!-- mios-src:d9d118dd2374 from Get-MiOS.ps1:1135-1146 -->

### SetWindowSize tells conhost to display N cells; conhost...

SetWindowSize tells conhost to display N cells; conhost itself
auto-pixel-sizes the Win32 window correctly for the active DPI.
DON'T MoveWindow with hardcoded pixel dims (the previous behaviour
of `MoveWindow ... 820x812`) -- at 150% DPI conhost cells render
~16 px wide so a 820 px window only fits ~50 cells, and at 200%
DPI ~33 cells. Operator-reported regression at 200% DPI:
"window opens but is 1/2 the size it should be". Reading the
ACTUAL post-resize Win32 window dims via GetWindowRect and using
those for centering keeps the window correctly cell-sized while
still putting it on the operator's active display.
Retry loop: window may not be fully realized + sized yet at first
call; SetWindowPos before that is a silent no-op. Try up to 8x
over ~2 seconds. Log every step to M:\MiOS\logs\mios-center-debug.log
(per feedback_mios_m_drive_everything; falls back to %TEMP% only
when M:\ doesn't exist yet during very-early bootstrap) so operator
can paste back what's happening when "windows aren't centering" recurs.

<!-- mios-src:6360c745a50f from Get-MiOS.ps1:1155-1170 -->

### Don't break on success. Operator-reported regression...

Don't break on success. Operator-reported regression: "spawned
install window still isn't centered/self centering STILL".
Logs showed centering succeeded on attempt 0 but the window
subsequently moved -- conhost/WT re-layouts after every output
paint + SetWindowSize call can shift the window. Keep re-
centering through all 12 ticks (~6 seconds) so the window
stays put through the inner-cmd's banner Write-Host calls,
the IRM fetch, and the child pwsh spawn.

<!-- mios-src:54c69c26bb3d from Get-MiOS.ps1:1194-1201 -->

### Build the cache-busted URL HERE inside the inner cmd, NOT...

Build the cache-busted URL HERE inside the inner cmd, NOT via outer-
scope interpolation. Operator-reported regression: when the inner cmd
was rendered with `-Uri '$_rawUrl'` and `$_rawUrl` interpolated to empty
for any reason (encoding issue / heredoc quirk / nested-template bug),
the rendered file became `Invoke-RestMethod -Uri '' -Headers ...` which
sent PowerShell into its mandatory-parameter prompt loop:
    cmdlet Invoke-RestMethod at command pipeline position 1
    Supply values for the following parameters:
    Uri:
Computing the URL inside the inner cmd removes the outer-scope dep
entirely and makes the rendered file self-sufficient.

<!-- mios-src:0918c1ef809d from Get-MiOS.ps1:1212-1222 -->

### Write to a temp .ps1 and run as a CHILD pwsh process so any...

Write to a temp .ps1 and run as a CHILD pwsh process so any
'exit N' calls inside Get-MiOS.ps1 terminate the child, NOT our
hosting elevation window. Without this, any preflight 'exit 1'
killed the elevated host before the operator could read the
error or pause for inspection -- the window appeared to "die
silently". Per operator: "the incorrectly launched powershell
window... just dies silently--seemingly no logs in sight!!!"
Log path: M:\MiOS\logs if M:\ exists (the canonical install-on-M
location), else %TEMP%. The child pwsh runs Start-Transcript
internally so the log gets every Write-Host without the parent
having to pipe through Tee-Object (which DESTROYS the child's
`$Host.UI.RawUI` console handle and makes `$RawUI.CursorPosition
= @{X=0;Y=0}` throw "The handle is invalid" -- exactly the crash
the operator hit in commit 1e3484f).
NO PRELUDE PREPEND. Get-MiOS.ps1 has a `param()` block at the
top of the file -- PowerShell requires param() to be the FIRST
statement in a script (after comments / using statements). My
prior commits prepended chcp/Start-Transcript lines which
pushed param() to line 6+, causing PowerShell to parse the
block's arguments as standalone assignments:
    "[string]\$RepoUrl = 'https://github.com/mios-dev/...'"
    -> "The assignment expression is not valid"
The codepage + Console encoding are ALREADY set in the inner
cmd (chcp 65001 etc. above); the child pwsh inherits the
conhost codepage from this elevated parent, so Unicode glyphs
render correctly without an inline prelude.
Logging during Pass-1 is sacrificed for now -- build-mios.ps1's
own logging at M:\MiOS\logs\mios-install-*.log covers Pass-2+
which is where 90% of the install time lives. Operator sees
all Pass-1 output live in the elevated host (Read-Host pause
at the end keeps it visible).
Run the freshly-fetched Get-MiOS.ps1 IN-PROCESS via scriptblock.
The previous `& pwsh.exe -File $tmpScript` spawned a new pwsh
process. On Windows 11 with WT as the default terminal, that
spawn opened a NEW WT TAB / WINDOW (operator-reported regression:
"spawns bootstrap window (correct) >> THEN opens a new window
(incorrect) >> THEN ALSO spawns the acknowledgement window").
In-process scriptblock execution eliminates the third window AND
avoids the cross-process console handle dance that previously
broke Read-Host on PS 5.1 fallback. Any `exit N` calls inside
Get-MiOS.ps1 will terminate THIS pwsh -- but that's exactly what
the operator wants for a unified "single bulk-install window"
experience. The existing try/catch wrapping is enough to keep
the elevation host visible long enough for the Read-Host pause
at the bottom of the inner cmd to fire.

<!-- mios-src:cf2adc8ee86f from Get-MiOS.ps1:1243-1287 -->

### "irm|iex invocation and install processes spawn too many...

"irm|iex invocation and install processes
spawn too many powershell windows and should be performed
in-line in one promoted Powershell window after bootstrap".
On success, transition THIS elevated conhost into the MiOS
terminal experience instead of asking the operator to press
Enter and click a shortcut.  Dot-source M:\MiOS\powershell\
profile.ps1 -- it self-renders the framed dashboard and
exposes the `mios <verb>` dispatcher (build / dash / dev /
config / pull / update / help).  Operator types verbs
directly in this same window; no new WT spawn, no shortcut
click, no third window.

<!-- mios-src:42354e7f078f from Get-MiOS.ps1:1305-1315 -->

### The MiOS profile body sources the dashboard, oh-my-posh...

The MiOS profile body sources the dashboard, oh-my-posh,
the mios.toml resolvers, AND defines `mios <verb>` plus the
per-verb function aliases.  After this dot-source the
operator is at the MiOS prompt in this same elevated
conhost.  pwsh -NoExit (set in the spawn args) keeps the
interactive prompt alive; no Read-Host below for the
success path.

<!-- mios-src:b978023f0c73 from Get-MiOS.ps1:1321-1327 -->

### SUCCESS path returns here -- the dot-sourced profile owns...

SUCCESS path returns here -- the dot-sourced profile owns
the prompt from this point.  No press-Enter close; the
operator quits the window naturally (`exit` / Ctrl-D / `q`).

<!-- mios-src:ad43c77bee53 from Get-MiOS.ps1:1337-1339 -->

### Write the inner cmd to a temp .ps1 and pass -File. Why NOT...

Write the inner cmd to a temp .ps1 and pass -File. Why NOT
-EncodedCommand: the inner cmd is ~12.5 KB of source. UTF-16
encoding doubles that to ~25 KB; Base64 expands to ~33 KB. Start-
Process -Verb RunAs goes through ShellExecute, whose lpParameters
is capped at 32,767 chars (signed 16-bit limit). The encoded
payload + surrounding -NoLogo / -NoProfile / -ExecutionPolicy /
-NoExit / -EncodedCommand args pushes us OVER 32 KB -- ShellExecute
returns ERROR_INVALID_PARAMETER (0x80070057) which surfaces to the
operator as "Self-elevation failed: The parameter is incorrect."
UAC never even fires; Pass-2 never opens. -File <shortpath> keeps
the command line tiny regardless of inner cmd size, so ShellExecute
is happy.

<!-- mios-src:64764e21e4c7 from Get-MiOS.ps1:1354-1365 -->

### SUCCESS

SUCCESS: Pass-1 has done its job. Pass-2 is alive in a new
elevated window which will fetch the latest Get-MiOS.ps1, render
the agreement gate (in 80x40), and run the install. Pass-1 must
EXIT IMMEDIATELY so the operator's focus moves cleanly to Pass-2.
The hosting `powershell -Command "irm | iex"` has no -NoExit, so
`return` here lets Pass-1's powershell.exe close on its own.
Operator perceives: small black box flashes -> UAC prompt ->
properly-sized elevated window appears with the agreement.

<!-- mios-src:d277abbb6027 from Get-MiOS.ps1:1384-1391 -->

### FAILURE PATH

FAILURE PATH: keep Pass-1 visible so the operator can read the
error detail (UAC denied, ShellExecute failure, etc.). On
success Pass-1 has already returned above.

<!-- mios-src:15a625b2e5b2 from Get-MiOS.ps1:1394-1396 -->

### AGREEMENT GATE -- runs in Pass-2 only. Pass-1 returned out...

AGREEMENT GATE -- runs in Pass-2 only. Pass-1 returned out of the
elevation block above, so reaching this line means we're already in
the properly-sized 80x40 elevated conhost. The gate function resizes
UP to 80x60 to give the ~104-line agreement breathing room, then
blocks on Read-Host until the operator types "Acknowledged" or aborts.

<!-- mios-src:77a5471db875 from Get-MiOS.ps1:1409-1413 -->

### Windows Terminal "MiOS" profile + Geist Mono Nerd Font +...

-----------------------------------------------------------------------
Windows Terminal "MiOS" profile + Geist Mono Nerd Font + oh-my-posh
wiring. Runs ONCE on the outer (pre-elevation) pass so the elevated
relaunch can pin -p MiOS and inherit the correct font, scheme,
padding, acrylic backdrop, 50% blur, 12pt Geist, and a
borderless 80x30 focus-mode window centered on the primary display.

Canonical dimensions: 80 cols × 30 rows.
  * 80×30 is the IBM "text-mode 3+" / TTY0 standard dimension
    (alongside 80×25 / 80×50). Universal grub/console fallback.
  * 4:3 pixel aspect ratio: with a 1:2 (W:H) monospace cell, 80/30
    gives 720×600 px ≈ 1.20:1 → render with lineHeight=1.0 the cells
    squash to 9×18 px → 720×540 → exactly 4:3.
  * Wide enough for the dashboard frame (80-col strict-clamp) and
    tall enough for the menu + footer + 8 phase rows + log row.

All three helpers are idempotent: safe to call on every run.
-----------------------------------------------------------------------

<!-- mios-src:3604382583c4 from Get-MiOS.ps1:1416-1433 -->

### Hokusai + operator-neutrals palette -- ALL values source...

Hokusai + operator-neutrals palette -- ALL values source from
mios.toml [colors] (vendor < host < user three-layer overlay) via
Get-MiosTomlValue. mios.toml is THE singular SSOT for the palette;
the literals below are FALLBACKS used only when the layered TOML
can't be read (early bootstrap before M:\ exists, or a corrupted
overlay). An operator edit in mios.html flows through to this
palette without touching any PS1.

<!-- mios-src:58ffff6bee92 from Get-MiOS.ps1:1435-1441 -->

### DEFENSIVE color resolution. Every WT scheme field MUST be a...

DEFENSIVE color resolution. Every WT scheme field MUST be a valid
`#rrggbb` or `#rgb` hex string -- WT rejects the entire
settings.json with "Line N column N (foreground) Have: ""
Expected: color" if ANY field is empty or malformed, falling back
to bare WT defaults (the operator-reported "no theme / no acrylic
/ no MiOS profile" symptom -- WT silently dropped the broken
MiOS scheme). The _hex helper below accepts the TOML value, then
ALWAYS returns a valid hex color: if the resolved value is empty
/ null / malformed, it returns the hardcoded fallback instead.

<!-- mios-src:502719282064 from Get-MiOS.ps1:1443-1451 -->

### Idempotent winget install for Windows Terminal Preview...

Idempotent winget install for Windows Terminal Preview ("dev line").
WT Preview tracks the active development branch, so MiOS gets the
newest acrylic/systemBackdrop/launchMode behavior the moment Microsoft
ships it. Stable WT (Microsoft.WindowsTerminal) is fine too; we only
upgrade an operator who has neither installed.

Source: winget pulls from msstore by default; Preview lives at
  id = Microsoft.WindowsTerminal.Preview
We pass --silent so no UI surfaces and --accept-{package,source}-
agreements so Server SKUs (which display the agreement EULA on first
winget call) don't hang the bootstrap.

<!-- mios-src:6f3447f325a5 from Get-MiOS.ps1:1520-1530 -->

### Per operator

Per operator: target the BASE Windows Terminal install (Stable),
NOT Preview. Polls until WT Stable's AppX package is registered
AND its LocalState dir is materialized.

<!-- mios-src:f6ff6be699e3 from Get-MiOS.ps1:1532-1534 -->

### Bootstrap winget itself on a truly bare Windows host (Win...

Bootstrap winget itself on a truly bare Windows host (Win 10 21H2,
OOBE-fresh Win 11 N edition without Store, etc.) before any other
Install-MiOS* function tries to use it. Operator-flagged
"MiOS should automatically install EVERYTHING needed to install MiOS
via irm|iex". Without this, every winget invocation on a bare host
silently warns + skips, leaving the bootstrap half-installed.

Resolution chain:
  1. winget already on PATH -> done.
  2. Microsoft.DesktopAppInstaller AppxPackage installed but PATH
     stale -> refresh PATH, re-probe.
  3. Download App Installer MSIXBUNDLE from mios.toml
     [bootstrap.prereqs].appinstaller_url (default aka.ms/getwinget)
     -> Add-AppxPackage.

<!-- mios-src:3c2f4f35da32 from Get-MiOS.ps1:1559-1572 -->

### Operator pivot

Operator pivot: MiOS targets the BASE Windows Terminal install,
NOT Preview. We do NOT pollute the operator's globals or default
profile -- we just upsert the MiOS / MiOS-DEV profiles into the
operator's existing settings.json so they appear in the WT
profile dropdown. Borderless / centered / sized launch comes
from wt.exe COMMAND-LINE flags at launch time, not globals.

<!-- mios-src:2d880d8138ff from Get-MiOS.ps1:1613-1618 -->

### Ensure PowerShell 7 (`pwsh.exe`) is on disk BEFORE the WT...

Ensure PowerShell 7 (`pwsh.exe`) is on disk BEFORE the WT MiOS
profile is generated, so the profile's `commandline` can bind
to pwsh.exe rather than silently falling back to Windows
PowerShell 5.1. PS 5.1 has the OLD PSReadLine that breaks
oh-my-posh init's modern PSReadLine integration; the resulting
MiOS terminal renders the OPERATOR'S pre-existing PS 5.1
profile (whatever broken oh-my-posh init they had — typical
symptom: "CONFIG NOT FOUND" prompt segment). Install-MiOSTerminalExtras
at Step 6/7 also installs Microsoft.PowerShell, but that's
AFTER WT profile creation — too late.

Idempotent: probes existing install before re-installing.
Refreshes $env:PATH after install so the caller's pwsh
detection (Get-AppxPackage / Get-Command pwsh) sees the new
binary in this same session.

<!-- mios-src:2f39901f8939 from Get-MiOS.ps1:1656-1670 -->

### TOML-first per AGENTS.md §3 -- winget ID from mios.toml...

TOML-first per AGENTS.md §3 -- winget ID from mios.toml
[bootstrap.prereqs].pwsh_pkg (operator can pin to PowerShell-Preview
or an MSI variant via mios.html).

<!-- mios-src:3e24aec83cba from Get-MiOS.ps1:1694-1696 -->

### ALL MiOS install artifacts land on M:\ per the operator's...

ALL MiOS install artifacts land on M:\ per the operator's
invariant. Fonts go to M:\MiOS\fonts\ -- Windows accepts any
path in HKCU\...\Fonts as long as the registry value points
at the actual .ttf file. Falls back to %LOCALAPPDATA%\...
only if M:\ isn't mounted yet (very early bootstrap).

<!-- mios-src:8f21efc6e7ad from Get-MiOS.ps1:1744-1748 -->

### Get every font file in the extracted tree (.ttf OR .otf --...

Get every font file in the extracted tree (.ttf OR .otf -- the
current Geist Nerd Fonts release ships .otf only). Nerd Fonts
release naming has changed multiple times -- the Get-ChildItem
-Filter pattern was missing valid faces because of case-sensitivity
and substring quirks on PowerShell 7.6+. Use -match instead which
is case-insensitive by default.

<!-- mios-src:ab4656f72f13 from Get-MiOS.ps1:1760-1765 -->

### Install Bibata-Modern-Classic as the Windows-wide cursor...

Install Bibata-Modern-Classic as the Windows-wide cursor scheme.
Operator-flagged "cursor is still not bibata GLOBALLY".
Linux dev VM Bibata install runs separately inside the WSL distro
(build-mios.ps1's Set-Step "Installing Bibata-Modern-Classic
cursor"). This Windows-side complement covers the desktop chrome
so the operator sees the same cursor on hover/click outside WT.

Mechanism:
  1. Fetch ful1e5/Bibata_Cursor latest "Bibata-Modern-Classic-
     Windows.tar.gz" release asset.
  2. Extract to M:\MiOS\cursors\Bibata-Modern-Classic (per the
     everything-on-M:\ invariant).
  3. Set HKCU\Control Panel\Cursors values to the extracted
     .cur / .ani paths so Windows uses Bibata in every app.
  4. Register the scheme under HKCU\Control Panel\Cursors\Schemes
     so it appears in Settings -> Mouse -> Additional pointer
     options and survives operator scheme switches.
  5. Broadcast SystemParametersInfo(SPI_SETCURSORS) so the running
     desktop picks up the new pointers without a logoff.

Idempotent: if Bibata is already installed AND the active
`(Default)` scheme is "Bibata Modern Classic", short-circuit.

<!-- mios-src:bd016a5062b6 from Get-MiOS.ps1:1813-1834 -->

### Map Bibata filenames -> Windows cursor registry value...

Map Bibata filenames -> Windows cursor registry value names.
Sourced from Bibata's shipped install.inf (clickgen-generated
Wreg section). Notable rename from older Bibata releases:
- Pointer.cur (not Default.cur) for Arrow
- Work.ani (not Working.ani) for AppStarting
- Vert.cur / Horz.cur / Dgn1.cur / Dgn2.cur (compact names)
- Alternate.cur for UpArrow (no -Select suffix)

<!-- mios-src:47ddf1beb043 from Get-MiOS.ps1:1889-1895 -->

### CursorBaseSize controls the rendered pixel size of the...

CursorBaseSize controls the rendered pixel size of the active
cursor (Windows picks the matching variant from the multi-image
.cur file). Bibata's Windows release embeds 5 sizes per .cur
(32, 48, 64, 96, 128); even the smallest 32px variant renders
visibly larger than typical Windows cursors because the
bibata glyph fills more of the 32x32 canvas. Operator-flagged
"windows bibata is too large" -- lowering the base
size to 24 forces Windows to downscale the 32px source to
match the visual weight of the default Aero cursor.
Operator-overridable via mios.toml [theme.cursor_windows].base_size.

<!-- mios-src:b5a575f427ee from Get-MiOS.ps1:1953-1962 -->

### Resolve the WT settings.json path. Per operator: target the...

Resolve the WT settings.json path. Per operator: target the BASE
(Stable) Windows Terminal install. Returns $null if WT Stable isn't
installed (caller should run Install-MiOSWindowsTerminal first).

<!-- mios-src:72fdafe5116b from Get-MiOS.ps1:1992-1994 -->

### Stable WT profile GUID for "MiOS-Bootstrap". Re-using the...

Stable WT profile GUID for "MiOS-Bootstrap". Re-using the same GUID
across runs lets us upsert idempotently instead of polluting the
profile list with a new entry every time.

<!-- mios-src:f9911bb72589 from Get-MiOS.ps1:2022-2024 -->

### Re-resolve the palette HERE (in case $Script:MiosPalette...

Re-resolve the palette HERE (in case $Script:MiosPalette was cached
before the M:\ TOML existed -- file-load-time evaluation of
Get-MiosPalette can hit the cold-fetch path which may have failed
silently). Then guard EVERY field with the same hex-fallback the
palette resolver applies, so a stale/empty cached value can't leak
into the WT scheme and trigger WT's "Line N column N (foreground)
Have: '' Expected: color" rejection -- which falls back the entire
settings.json to defaults (no MiOS profile, no acrylic, no scheme).

<!-- mios-src:7e4c8b067a5a from Get-MiOS.ps1:2027-2034 -->

### Profile commandline

Profile commandline: pwsh -NoLogo -NoExit -Command ". 'M:\...'".
Explicitly dot-sources the canonical M:\ profile script AFTER
$PROFILE has loaded -- so even if the operator has a broken
oh-my-posh init in their $PROFILE that runs after our markers,
OUR regex-patched init runs LAST and wins. This is what makes
the MiOS terminal's prompt deterministic regardless of the
operator's existing PowerShell profile state. Without this
explicit re-init, the MiOS terminal could inherit a broken
PSReadLine binding state from the operator's pre-existing init.
Resolve pwsh 7 across all install shapes:
  1. MSI install at $env:ProgramFiles\PowerShell\7\pwsh.exe
  2. Microsoft Store install at WindowsApps\Microsoft.PowerShell_*
     (operator's actual setup -- PS 7.6.1 from MS Store).
  3. App Execution Alias via Get-Command (last-ditch).
  4. Windows PS 5.1 (only if no pwsh found at all). 5.1 has the
     OLD PSReadLine that breaks oh-my-posh init -- avoid unless
     truly desperate.

<!-- mios-src:68883d89edd4 from Get-MiOS.ps1:2067-2083 -->

### NoProfile is CRITICAL

-NoProfile is CRITICAL: skip the operator's $PROFILE chain
entirely so any pre-existing oh-my-posh init / PSReadLine
configuration / aliases the operator already has DON'T run AFTER
our M:\ profile and override it. Operator-reported symptom: their
pre-existing themed PS 7 prompt rendered in MiOS terminal because
their $PROFILE re-initialized oh-my-posh AFTER our marker block.
With -NoProfile, ONLY the M:\ profile runs (via -Command dot-
source), so the MiOS terminal is operator-isolated and 100%
deterministic.
Single-quoted PS string with `''` for embedded literal quotes.
ConvertTo-Json will JSON-encode the outer double-quotes correctly.
`$env:MIOS_APP_CONTEXT='1'` is the gate signal the M:\ profile
body checks before resizing the conhost to the MiOS-app dims
(80x20). Without this signal the profile body skips the resize,
which is what we want during BOOTSTRAP/INSTALL where any child
pwsh inheriting `$PROFILE.CurrentUserAllHosts redirector should
NOT shrink the operator's 80x40 install conhost mid-install.

<!-- mios-src:ca4e79dc5a16 from Get-MiOS.ps1:2120-2136 -->

### Per-profile shared settings -- apply to BOTH "MiOS" and...

Per-profile shared settings -- apply to BOTH "MiOS" and "MiOS-DEV"
so they look/feel identical. Belt-AND-braces acrylic settings:
WT 1.16-1.17 reads `useAcrylic` (legacy bool) and `opacity`. WT
1.18+ reads `systemBackdrop` (per-profile). Setting BOTH means
acrylic 50% transparency renders correctly across every WT
version the operator might end up on. `useMica` is NOT set --
it's not a documented WT key (mica is selected via
systemBackdrop="mica"), and shipping unknown keys can cause WT's
schema validator to reject the profile and fall back to defaults.
GLOBAL MiOS terminal defaults sourced from mios.toml [theme] +
[theme.font]. Per operator (multiple reaffirmations): acrylic ON,
50% transparency, frame-less, border-less, scroll-bar-less. The
WT profile patcher reads from mios.toml so editing those keys in
the configurator HTML re-skins every MiOS terminal on the next
bootstrap run -- single edit surface, applied to BOTH WT profiles
(MiOS + MiOS-DEV) below.
-- Defensive toml-value resolution --------------------------
If ANY of these returns an empty / invalid value, WT's schema
validator rejects the entire profile and the operator gets bare
default chrome (no acrylic, no MiOS scheme, no font). The earlier
tabColor "" failure proved this is fragile -- so we validate
EVERY toml-resolved string before stamping it into the profile.

<!-- mios-src:c24366ea9a59 from Get-MiOS.ps1:2139-2160 -->

### launch_mode -- forces WT focus mode (no titlebar, no tabs)...

launch_mode -- forces WT focus mode (no titlebar, no tabs) at
window-create time so the pseudo-console reports the actual
visible cell count from first paint. Without this, WT initially
measures the viewport WITH titlebar/tabs (cell count = cols-1)
and only re-measures after `scrollbarState=hidden` takes over,
by which time the first prompt has already been rendered to the
wrong width. With launch_mode=focus, the chrome is gone before
the first paint, so cell count = cols immediately.

<!-- mios-src:48a4ba0d0642 from Get-MiOS.ps1:2182-2189 -->

### disable_animations -- defaults to FALSE (animations ON) per...

disable_animations -- defaults to FALSE (animations ON) per
operator: "enable animations and all preview features in the MiOS
Windows Terminal profile -- full aesthetics! ALSO: can it quickly
fade on open and close??". WT's built-in window open/close fade is
gated on disableAnimations=false + useAcrylic=true. The trade-off:
acrylic-recompute on first paint MAY re-trigger the off-by-N
cell-count bug; if the powerline wraps again with animations on,
bump mios.toml [terminal].right_margin to 1 as the targeted band-
aid (NOT animations off -- operator wants the aesthetics).

<!-- mios-src:06d557dd77cf from Get-MiOS.ps1:2192-2200 -->

### enable_preview_features -- gates the bundle of WT...

enable_preview_features -- gates the bundle of WT experimental.*
toggles that are aesthetics-relevant (URL detection, AtlasEngine
GPU renderer, forced-VT input, full-repaint rendering). Defaults
to TRUE per operator. Set to false only if a specific WT version
ships a regression in one of the preview keys.

<!-- mios-src:8ca5c82f8612 from Get-MiOS.ps1:2203-2207 -->

### MINIMAL chrome only -- per operator's trace, the WT MiOS...

MINIMAL chrome only -- per operator's trace, the WT MiOS app
rendered the oh-my-posh prompt (so commandline + profile body
work) but DID NOT apply chrome (no acrylic, no MiOS scheme).
That means WT silently rejected one of the chrome keys and
fell back to defaults for the rest. Stripping back to the
bare minimum proven-working set; will re-add carefully once
this verifies rendering with full theming.
Terminal dims sourced from mios.toml [terminal].cols / .rows so
opening the WT profile DIRECTLY (without the launcher's --size
arg, e.g. from the WT dropdown) still produces an 80x20 window.
Without these, WT inherits the operator's global default
(typically 120x30) and the dashboard's framing breaks.

<!-- mios-src:4a90f1eb749c from Get-MiOS.ps1:2214-2225 -->

### Disable WT's end-of-line auto-wrap on the MiOS profile....

Disable WT's end-of-line auto-wrap on the MiOS profile.
Default WT behavior: writing to the LAST column emits a
soft-wrap newline, so content that fills exactly cols-wide
(e.g. our edge-to-edge dashboard frame at width=80 in an
80-col window) wraps every full-width row to a new visual
row -- pushing the dashboard's TOP frame above the viewport.
Operator screenshot image #12: top `+-MiOS-+`
corner clipped, fastfetch info at row 0, right `|` border
missing. Setting this to true tells WT to leave col cols-1
written without firing the soft-wrap, so width=80 content
in an 80-col window stays on one row. Combined with
mios.toml [terminal].right_margin=0 + frame_width=80 this
produces the truly edge-to-edge framed dashboard the
operator wants on BOTH bash + pwsh sides.

<!-- mios-src:513a1884c076 from Get-MiOS.ps1:2255-2268 -->

### initialCols / initialRows lock the dims when WT spawns this...

initialCols / initialRows lock the dims when WT spawns this
profile from a non-launcher entry point (dropdown, "MiOS
Terminal" Start Menu shortcut). Operator-edited via mios.toml
[terminal].cols / .rows.

<!-- mios-src:05274fe1c9b3 from Get-MiOS.ps1:2270-2273 -->

### MiOS-DEV profile

MiOS-DEV profile: drops the operator straight into the MiOS-DEV WSL2
distro as the mios user, cwd /. Same look as MiOS (acrylic, font,
Resolve the actual on-disk WSL distro name. podman machine init
registers the distro as 'podman-MiOS-DEV' (podman hardcodes the
'podman-' prefix), even though the operator-facing name is
MiOS-DEV. Operator-reported regression: clicking the MiOS-DEV
shortcut threw 'WSL_E_DISTRO_NOT_FOUND' because the profile
commandline targeted bare 'MiOS-DEV' which doesn't exist on disk.
Walk the registered distro list at install time and pick the
first match in priority order: prefer 'podman-MiOS-DEV' (post
init) -> 'MiOS-DEV' (post Restore-PodmanPrefix) -> 'podman-MiOS-
BUILDER' (legacy) -> 'MiOS-BUILDER' (legacy).

<!-- mios-src:5cdd952d723b from Get-MiOS.ps1:2289-2300 -->

### GLOBAL WRITES (edge-to-edge pivot): the prior "no globals"...

GLOBAL WRITES (edge-to-edge pivot): the prior "no
globals" stance left WT's pseudo-console reporting +1-2 cells
over the actual visible cell count during first paint, before
`profiles.defaults.scrollbarState='hidden'` could take effect.
That made oh-my-posh's right-aligned powerline block wrap the
trailing time char to col 0 of the next line ("powerline seconds
rolling over to the left under the second-line ❯"). Operator:
"MiOS app/windows terminal windows should be completely
frameless/borderless with no margin (edge-to-edge printing)."

Setting `launchMode = "focus"` at the ROOT level strips the title
bar AND the tab row from the very first paint, so WT measures the
viewport at the actual cell count cols × rows. Pairing it with
per-profile `suppressApplicationTitle = true` keeps WT from
re-measuring whenever the shell tries to set the window title
(every `cd`, every prompt repaint), and `disableAnimations = true`
skips the acrylic-recompute pass that re-measures the cell grid.
All three are required: drop any one and the off-by-N comes back.

<!-- mios-src:fc8f88065644 from Get-MiOS.ps1:2345-2362 -->

### Root-level launchMode -- forces focus mode (no titlebar, no...

Root-level launchMode -- forces focus mode (no titlebar, no tabs)
globally. This affects EVERY WT window the operator opens, not
just MiOS profiles. Operator-approved ("go fix
mios-bootstrap edge-to-edge now") because `--focus` on the wt.exe
CLI alone hides tabs but leaves the titlebar, so the off-by-N
cell-count bug persisted on launches that didn't go through the
MiOS launcher. Sourced from mios.toml [theme].launch_mode (SSOT)
so an operator who needs tabs back can flip it via mios.html
without editing this script. Use `wt.exe -w 0 nt` for a transient
tabs-and-titlebar window if needed.

<!-- mios-src:a8ac96e1d228 from Get-MiOS.ps1:2368-2377 -->

### GLOBAL no-scrollbars + zero-padding + no-titlebar-rewriting...

GLOBAL no-scrollbars + zero-padding + no-titlebar-rewriting via
profiles.defaults. Per operator: "MiOS app window/terminal
window(s) should all have NO scrollbars inhibiting any windows
globally!!". Per-profile scrollbarState only affects that profile;
profiles.defaults applies to EVERY profile including auto-
generated ones (cmd, PowerShell, WSL distros), so when an operator
switches profiles they keep the borderless+scrollbar-less feel.
suppressApplicationTitle=true and disableAnimations=true are the
second + third legs of the edge-to-edge tripod (see comment
above) -- without them, WT re-measures the viewport after the
first prompt has already been rendered using the wrong width.

<!-- mios-src:f5f35a64a1af from Get-MiOS.ps1:2380-2390 -->

### Preview / experimental features bundle. All gated on...

Preview / experimental features bundle. All gated on
mios.toml [theme].enable_preview_features. Operator: "enable
animations and all preview features in the MiOS Windows Terminal
profile -- full aesthetics!" Each key here MUST be a documented
WT experimental knob (no random invented keys -- WT silently
rejects unknown keys, and a single rejected key can cascade into
the entire profile being skipped, which manifests as "MiOS scheme
never applied" / "powerline glyphs render as boxes").

<!-- mios-src:468522cf4252 from Get-MiOS.ps1:2402-2409 -->

### ForceVT input -- routes ALL input through the VT pathway...

ForceVT input -- routes ALL input through the VT pathway, so
modifier keys (Ctrl/Alt/Shift combos) hit the shell as
documented escape sequences instead of being intercepted by
WT's native key handler.

<!-- mios-src:b522cb00d7fd from Get-MiOS.ps1:2417-2420 -->

### Filter out any prior MiOS / MiOS-DEV entries by GUID *or*...

Filter out any prior MiOS / MiOS-DEV entries by GUID *or* by the
names we've used in earlier revisions, so the upsert is exactly two.
Also strip podman/WSL auto-generated profiles for our distros
(podman-MiOS-DEV, podman-MiOS-BUILDER, etc.) -- WT auto-creates one
per `podman machine init` call and they accumulate without dedup.
Our branded MiOS-DEV profile already covers that distro.
Strip prior MiOS-related entries.  "MiOS" name kept in the strip
list so re-runs after the rename ("MiOS app itself
should be defined as MiOS-WIN") clean up the old "MiOS" profile
left behind.  Also strips current "MiOS-WIN" by name in case the
GUID changed.

<!-- mios-src:e59937c77af1 from Get-MiOS.ps1:2446-2456 -->

### NOTE

NOTE: globalSummon keybinding (Win+Space) NOT written. Adding
it appears to trip WT's settings-file validator silently --
the prompt rendered (so commandline + scheme reference were
fine) but acrylic / scheme resolution didn't apply, suggesting
WT bailed mid-load. Will re-add via a separate post-MVP commit
after minimum chrome is verified rendering. Operator can still
add it manually via mios-config.html or by editing settings.json.

<!-- mios-src:dd6ab125b9e2 from Get-MiOS.ps1:2473-2479 -->

### Verify against the ACTUAL renamed profile names from...

Verify against the ACTUAL renamed profile names from
mios.toml [theme.terminal] ("MiOS app
itself should be defined as MiOS-WIN").  Was hardcoded to
'MiOS' which always failed post-rename and dropped through
to the raw-JSON-injection fallback that wrote a degraded
settings.json (schemes/profiles arrays partly-stripped),
leaving WT without the proper MiOS chrome -> Nerd Font
PUA glyphs (U+E0B4 / U+E0B6) rendered as `?` placeholders.

<!-- mios-src:92d95ef966ad from Get-MiOS.ps1:2502-2509 -->

### Make MiOS a first-class Windows app the moment irm|iex...

Make MiOS a first-class Windows app the moment irm|iex finishes:
  * Start Menu MiOS.lnk  (so Win-search "MiOS" returns it)
  * Desktop MiOS.lnk     (one-click launch)
  * HKCU Uninstall key   (Settings > Apps > Installed apps lists it)
  * AppUserModelID stamp (taskbar grouping + Pin to Start identity)
  * Best-effort programmatic Pin to Start (Win10 only -- Win11 hint)

Target dir for the launcher script: M:\MiOS\bin\mios-launch.ps1
(operator's M:\-everywhere invariant -- "irm|iex sets up M:\
disk/partition installs EVERYTHING to M:\ EVERYTHING").  M:\
is a HARD REQUIREMENT -- the bootstrap creates it in
Initialize-DataDisk before this function runs.  No fallback
to LOCALAPPDATA; if M:\ isn't there, something has wiped it
mid-install and we should fail loudly rather than silently
split the install across C:\ and M:\.

<!-- mios-src:1842db5d85f4 from Get-MiOS.ps1:2537-2551 -->

### mios-launch.ps1 -- native MiOS app launcher. Spawns wt.exe...

mios-launch.ps1 -- native MiOS app launcher.
Spawns wt.exe with the MiOS profile in focus mode (frameless,
borderless, no titlebar/tab-row), 80 cols x 30 rows, screen-centered
on whichever monitor the cursor is currently on, always-on-top.
Runs invisibly (parent shortcut uses -WindowStyle Hidden).

-Profile <name>  WT profile to launch.  Canonical names:
                 'MiOS-DEV' (= dev VM via wsl.exe -d podman-MiOS-DEV)
                 'MiOS-WIN' (= Windows pwsh + MiOS profile body)
-Verb <name>     Optional. Runs `mios <verb>` inside the launched
                 Windows-side window after the profile body loads.
                 Ignored for MiOS-DEV (the dev VM is a bash login).

"UNIFY all MiOS app windows/themed windows
terminal windows to use the same profile and launch params GLOBALLY!!!"

<!-- mios-src:ef600b96fa8c from Get-MiOS.ps1:2576-2590 -->

### Window name

Window name: MiOS for the bare hub launch, MiOS-<verb> for verb
launches. Per-verb unique names prevent verb tabs piling into the
main MiOS hub window -- each click opens its OWN centered focus
window. The hub stays single-instance (clicking MiOS again reuses
the existing window). Win+Space summon still targets `MiOS` (the hub)
per mios.toml [theme.terminal].summon_window_name.

<!-- mios-src:6a821546868c from Get-MiOS.ps1:2611-2616 -->

### `-w <winName>` names the window so click-to-focus finds it...

`-w <winName>` names the window so click-to-focus finds it and the
post-launch SetWindowPos retry can target it. The hub uses
`-w MiOS` (single-instance, summon-targetable). Per-verb launches
use `-w MiOS-<verb>` (own window per verb -- no tab-pile).

Empty subcommand on hub launches uses the profile's bound commandline
(Windows pwsh + MiOS PS profile body via Install-MiOSTerminalProfile).
On verb launches, override commandline with a pwsh that loads the
profile body explicitly THEN runs `mios <verb>` -- otherwise wt.exe's
subcommand replaces the profile commandline and we lose the dashboard
render + the `mios` function definition.

<!-- mios-src:211242bb3393 from Get-MiOS.ps1:2639-2649 -->

### Pick the WindowsTerminal process whose StartTime is AFTER...

Pick the WindowsTerminal process whose StartTime is AFTER our
spawnedAt timestamp. Picking "newest WT" without the timestamp
filter accidentally targets the operator's pre-existing WT
window (whose StartTime is later only because StartTime sort
picks the most-recently-active one). Filter by spawn time + 1s
leeway so we always land on OUR newly-spawned WT.

<!-- mios-src:79c0635b523c from Get-MiOS.ps1:2681-2686 -->

### ENFORCE the target pixel size ($winW / $winH computed from...

ENFORCE the target pixel size ($winW / $winH computed from
mios.toml [terminal].cols/.rows + [theme.font] cell metrics).
The previous version of this code used $rw/$rh from GetWindowRect
-- which is the CURRENT window size -- and only re-centered.
When `wt.exe -w MiOS` added a tab to an existing wider window
(operator already had a MiOS-named WT window from a prior run),
the launcher kept the old wide dims and the operator saw a
~167-col terminal instead of the canonical 80x20. SetWindowPos
with the COMPUTED target dims ($winW / $winH) forces the resize
every launch so the MiOS terminal is deterministic.

<!-- mios-src:51a818bf8e15 from Get-MiOS.ps1:2696-2705 -->

### 0x40 = SWP_SHOWWINDOW | SWP_NOOWNERZORDER (apply size +...

0x40 = SWP_SHOWWINDOW | SWP_NOOWNERZORDER (apply size + topmost).
0x04 = SWP_NOZORDER                       (re-apply to release topmost
                                           after the window is the
                                           front-most; without this
                                           second pass the operator
                                           can't focus other windows).

<!-- mios-src:fe473714f205 from Get-MiOS.ps1:2710-2715 -->

### Bake mios.toml [terminal] / [theme.font] values into the...

Bake mios.toml [terminal] / [theme.font] values into the launcher
body. Single-quoted here-string above means $vars don't interpolate
at definition time; we substitute placeholders here at install time
so the launcher's geometry tracks the operator's mios.toml edits.

<!-- mios-src:343242e79d3a from Get-MiOS.ps1:2722-2725 -->

### Resolve a pwsh.exe for the .lnk target. IMPORTANT: probe...

Resolve a pwsh.exe for the .lnk target.
IMPORTANT: probe canonical install locations FIRST. Get-Command
pwsh.exe on Windows 11 returns the WindowsApps reparse-point stub
(%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe) which ShellExecute
rejects with 0x80070002 (operator 17:57 install: clicking MiOS
Help.lnk produced "[error 2147942402 (0x80070002) when launching
`mios help`] The system cannot find the file specified.")

<!-- mios-src:0e925fa1e32d from Get-MiOS.ps1:2742-2748 -->

### Hub .lnk targets the MiOS-DEV WT profile (mios.toml...

Hub .lnk targets the MiOS-DEV WT profile (mios.toml
[theme.terminal].hub_target_profile, default "MiOS-DEV") --
"MiOS app opens direct to... podman-MiOS-DEV".
The launcher receives -Profile <name>; mios-launch.ps1 spawns
`wt.exe ... -p <name>` which lands the operator straight in the
dev VM shell.  No Verb -- the dev VM commandline is a bash
login, not a `mios <verb>` dispatcher.

<!-- mios-src:a88c33b9a320 from Get-MiOS.ps1:2761-2767 -->

### Canonical 4-shortcut set ------------------ SSOT: each...

- Canonical 4-shortcut set ------------------
SSOT: each shortcut's metadata (name, profile, verb, description)
resolves through mios.toml [apps.shortcut.<key>]. PS-code defaults
below are vendor fallbacks per feedback_mios_defaults_baseline.
Operator can rename/relabel via mios.html -> mios.toml without
touching code. Per feedback_mios_toml_is_ssot_for_code: no
hardcoded user-facing strings.

Operator directive: "MiOS app opens MiOS-DEV machine to the GLOBAL
unified dash, MiOS-WIN does the windows side ... MiOS Help and
Uninstall MiOS are the ONLY installed shortcuts/links system wide!!!"

<!-- mios-src:5cbe00b61264 from Get-MiOS.ps1:2800-2810 -->

### Per-verb shortcuts (MiOS-DEV / MiOS Build / MiOS Dashboard...

-- Per-verb shortcuts (MiOS-DEV / MiOS Build / MiOS Dashboard / etc.) --
Per the canonical e2e contract: native-app surface is the MiOS hub +
per-verb shortcuts. Each verb opens a fresh MiOS WT app window (via
mios-launch.ps1) and runs `mios <verb>` inside it. Both Start Menu
AND Desktop get the shortcuts so the operator can pick whichever
surface they prefer (and pin manually -- Win11 disabled programmatic
pinning to Start, so we drop the .lnk and the operator right-clicks
→ "Pin to Start" / "Pin to Taskbar").
Operator-curated 4-app surface: MiOS (the terminal hub, created
separately above as MiOS.lnk), MiOS-DEV (dev VM dashboard),
MiOS Help (verb reference), Uninstall MiOS (Add/Remove). The
build / dash / config / update / pull verbs are operator-typed
commands INSIDE the MiOS terminal, NOT separate native apps.
Per-verb shortcuts.  Each entry maps to:
  * Profile  -- WT profile name to launch ('MiOS' = hub,
                'MiOS-DEV' = wsl.exe -d podman-MiOS-DEV --user mios)
  * Verb     -- mios verb to run inside the launched window
                (empty = just open the profile, no dispatch)
  * Icon     -- per-verb .ico under M:\MiOS\icons (fallback: mios.ico)
"launching MiOS-DEV doesn't launch in to
the podman-MiOS-DEV machine still" -- root cause was that the
MiOS-DEV.lnk was passing `-Verb dev` to mios-launch.ps1 which
only accepted -Profile, so the dev launcher silently fell back
to Profile='MiOS' (the hub) and the dev verb was never used.
The Profile field below routes to the right WT profile so
MiOS-DEV.lnk now lands in the actual dev VM.
consolidation: "TOO MANY APPS!! I SAID
UNIFY MiOS APPS in a way that makes sense and is minimal --
MiOS app opens direct to ... podman-MiOS-DEV!!!".  The hub
MiOS.lnk written above is the ONE user-facing app.  Per-verb
shortcuts (MiOS Help / MiOS Config / MiOS-DEV / MiOS-WIN)
are NOT created -- those are typed verbs in the terminal
(`mios help`, `mios config`, `mios dev`, etc.), not separate
native apps.  Only the Uninstall MiOS shortcut sibling lives
alongside the hub.  $miosVerbs is left as an empty array so
downstream loops (AumID stamping, .lnk reaping) iterate
zero entries instead of crashing on $null.

<!-- mios-src:c82d38238c60 from Get-MiOS.ps1:2901-2937 -->

### Uninstall MiOS shortcut (Start Menu + Desktop)...

-- Uninstall MiOS shortcut (Start Menu + Desktop) --------------
Per "MiOS should... Install as a Native
Windows Application with a bundled uninstaller being a
shortcut/link as well".  The hub already registers in
Add/Remove Programs (line 2294+); this gives the operator a
direct desktop / Start-Menu shortcut to the uninstaller without
opening Settings -> Apps.  The .lnk targets M:\MiOS\bin\uninstall.ps1
which build-mios.ps1's Install-WindowsBranding stages -- it does
the full reap (WSL distros, podman machines, registry keys, M:\
overlay, .lnk cleanup).  Falls back to the inline UninstallString
registered above if the full uninstall.ps1 isn't on disk yet
(e.g. on a half-bootstrapped host).

<!-- mios-src:cda6204b9040 from Get-MiOS.ps1:2940-2951 -->

### Stale-shortcut cleanup -- canonical 4-shortcut set is MiOS...

Stale-shortcut cleanup -- canonical 4-shortcut set is
MiOS / MiOS-WIN / MiOS Help / Uninstall MiOS (created above).
Every OTHER variant a prior revision shipped gets reaped so
re-running Get-MiOS.ps1 normalizes the menu. NOTE: MiOS-DEV.lnk
is reaped because the canonical "MiOS.lnk" already targets the
dev VM (no second shortcut for the same target). MiOS Config.lnk
is reaped because `mios config` is a typed verb inside the terminal.

<!-- mios-src:02d664fc05f1 from Get-MiOS.ps1:2979-2985 -->

### DisplayName resolves through mios.toml...

DisplayName resolves through mios.toml [branding].tagline_app
(per 'the Applications tag/description
when installed "MiOS - Immutable Fedora AI Workstation"
should be defined as My Personal Operating System or similar').
The technical descriptor "Immutable Fedora AI Workstation"
remains in the dashboard subtitle for in-terminal context;
the OS-wide app face (this DisplayName, .lnk descriptions,
AppX manifest) uses the operator-friendly tagline.

<!-- mios-src:66da70192690 from Get-MiOS.ps1:3069-3076 -->

### Explicit Windows Start Menu shortcuts for MiOS web...

Explicit Windows Start Menu shortcuts for MiOS web services. WSLg's
auto-publish heuristic filters out the 10 mios-svc-*.desktop files
MiOS ships in /usr/share/applications/ (Categories=System;Network;
Settings; + Exec=xdg-open URL doesn't fit WSLg's app model).
Operator-confirmed 0 of 10 mios-svc-* entries surfaced
as Windows shortcuts despite clean Type=Application + NoDisplay=false.

TOML-first per AGENTS.md §3 -- iterates mios.toml [desktop.start_menu]
`publish` list and reads <key>_label, <key>_scheme, <key>_port_key
for each entry. Resolves the port from [ports].<port_key>. Writes
one .url Internet shortcut per entry into
  %APPDATA%\Microsoft\Windows\Start Menu\Programs\podman-MiOS-DEV\
so they land in the same Start Menu folder WSLg uses for the
2 apps it does auto-publish (gnome-software, winemine).

Idempotent: rewrites the .url body each pass; safe to re-run.
Operator removes by dropping a key from `publish` (existing .url
persists until Pass-0 reap or manual delete).

<!-- mios-src:6d77937736f2 from Get-MiOS.ps1:3124-3141 -->

### Vendor content blobs (branding ASCII / fastfetch config /...

========================================================================
Vendor content blobs (branding ASCII / fastfetch config / oh-my-posh
theme) USED to be embedded as heredocs in this script.  They drifted
from upstream mios.git on every iteration and produced stale
powerline glyphs / ASCII art / fastfetch logos at install time --
"you are hardcoding mios build to build a
smaller version of itself that you've embedded in the actual codebase
and THAT's where it's sourcing from!! MiOS is completely self
developing, self building, self hosted... ALL values source from the
toml".

Get-MiosVendorContent resolves vendor content from mios.git origin
(raw.githubusercontent.com).  WEB ONLY -- no local fallback.

Per operator architectural rule

  "ORIGIN = web entries/repos only -- no fallback to M:\ or
   anywhere else -- unless origin has been pulled and it's a
   simple 'mios build' -- that can pull from M:\ as it'd already
   exist -- then 'mios update' would ALWAYS pull from web
   regardless of clean entry, updating, etc-etc!!!"

Get-MiOS.ps1 is BOTH the clean `irm | iex` entry AND what `mios
update` re-fetches.  Both must hit the web -- never M:\, never
C:\MiOS, never %USERPROFILE%.  M:\ overlays exist for build-mios.ps1
/ `mios build` to read AFTER mios-pull has populated them; the
bootstrap itself ALWAYS forces a fresh fetch.  Mixing the two
would let a stale M:\ silently override the web pull, defeating
the "clean entry forces refresh" guarantee.

Hard-fail with a clear error rather than falling back to a stale
snapshot.  No embedded heredocs, no M:\ cache, no on-disk dev
tree -- nothing but origin.
========================================================================

<!-- mios-src:36c8751f33bd from Get-MiOS.ps1:3180-3213 -->

### Use Invoke-WebRequest, NOT Invoke-RestMethod. IRM...

Use Invoke-WebRequest, NOT Invoke-RestMethod.  IRM
auto-deserializes any JSON response into a PSCustomObject; for
vendor content like mios.omp.json we need RAW TEXT.  IRM
produced an 867-byte stringified-PSCustomObject (instead of
the 10.9 kb omp.json source) and broke the downstream
GetBytes() call with "Cannot find an overload" because the
argument was an object, not a string.  IWR returns the raw
response body as a string (or byte[] for binary), which we
then UTF-8-decode if it came back as bytes -- so PUA glyphs
(U+E0B4 / U+E0B6) in mios.omp.json survive end-to-end.

<!-- mios-src:6e1f6e541e97 from Get-MiOS.ps1:3232-3241 -->

### Open-source terminal-completion + UX enhancers. PowerShell...

Open-source terminal-completion + UX enhancers. PowerShell
modules come from PSGallery (Install-Module); CLI tools come
from winget. Net effect: every MiOS shell session gets:

  * Terminal-Icons          -- file/folder icons in `ls` output
  * posh-git                -- git tab-completion + branch info
  * CompletionPredictor     -- AI-style predictive completion
  * WinGet.CommandNotFound  -- "did you mean: winget install X?"
                               when an unknown command is typed
  * sharkdp.bat             -- syntax-highlighted `cat` replacement
  * junegunn.fzf            -- fuzzy finder (Ctrl-T, Ctrl-R)
  * GitHub.cli              -- `gh` CLI for github operations

All idempotent: probes existing install before re-installing.

MUST run under PowerShell 7+, not Windows PowerShell 5.1:
  * PS 5.1 ships PowerShellGet 1.0.0.1, which can resolve Install-Module
    as a *command* but fails to load the *module* dependency graph
    (NuGet PackageProvider) -- the operator-visible error is
    "Install-Module was found in PowerShellGet, but the module could
    not be loaded". Force-Import + bootstrapping NuGet doesn't fully
    fix this on a fresh 5.1 install.
  * CompletionPredictor + Microsoft.WinGet.CommandNotFound require
    PS 7+ at *runtime* anyway (they use the PSReadLine 2.2 predictor
    API only available in pwsh 7).
  * PS 5.1 and PS 7 have SEPARATE per-user module paths
    (~/Documents/WindowsPowerShell/Modules vs ~/Documents/PowerShell/Modules)
    -- installing from 5.1 wouldn't help pwsh 7 see them at runtime.

If launched via `powershell` (5.1), trampoline this step through
pwsh.exe so installs land in pwsh 7's user-module path.

<!-- mios-src:12cb66ed71e3 from Get-MiOS.ps1:3261-3291 -->

### NOTE

NOTE: when invoked via the trampoline below, this script's stdout is
captured by the parent (Windows PowerShell 5.1) and CLIXML-serialized
because pwsh 7 sends Write-Host through the PSHost information stream.
Use [Console]::WriteLine instead -- raw stdout bypasses the PSHost
serializer entirely, so the parent sees plain text. Cost: no color in
the trampolined branch (acceptable -- the in-process branch still
uses Write-Host with color).

<!-- mios-src:3187455241fb from Get-MiOS.ps1:3305-3311 -->

### SSOT

SSOT: package list comes from the layered mios.toml chain.
Per operator "ALL Global packages SOURCE FROM THE TOML/HTML
FILE!!!" + "now how does changing the html change the toml
thats read by multiple scripts and components".

Layered resolution order (highest → lowest precedence):
  1. M:\etc\mios\mios.toml          -- HOST overlay (where the
                                       Epiphany configurator
                                       saves; visible to BOTH
                                       Windows AND MiOS-DEV via
                                       /mnt/m/etc/mios/mios.toml)
  2. M:\usr\share\mios\mios.toml    -- VENDOR copy on M:\ if
                                       Phase 2 already cloned it
  3. raw.githubusercontent.com mios.git origin/main  -- COLD
                                       first-run path (no M:\
                                       yet)

Each layer is checked; the first that yields a non-empty
[packages.windows] pkgs = [...] wins. This makes Pass 1 see
user edits made via the HTML configurator the moment they're
saved, the same way the Linux side sees them via /etc/mios/.

<!-- mios-src:85c9055ad033 from Get-MiOS.ps1:3355-3375 -->

### winget install/upgrade oh-my-posh to latest....

winget install/upgrade oh-my-posh to latest. Operator-reported
"Get-PSReadLineKeyHandler Spacebar / Enter / Ctrl+c" positional
parameter errors come from oh-my-posh's init script emitting the
legacy positional syntax that no PSReadLine version accepts.
Latest oh-my-posh emits -Chord <key> -- the correct named-parameter
syntax. So bumping oh-my-posh fixes the init errors at the source.

<!-- mios-src:e7e1713aa48f from Get-MiOS.ps1:3456-3461 -->

### oh-my-posh's init pwsh emits Get-PSReadLineKeyHandler calls...

oh-my-posh's init pwsh emits Get-PSReadLineKeyHandler calls that
use named parameters (Get-PSReadLineKeyHandler -Chord Spacebar).
The version of PSReadLine that ships in PowerShell 7.6's box is
too old to accept those args -- it expects positional, and emits
"A positional parameter cannot be found that accepts argument
'Spacebar'/'Enter'/'Ctrl+c'". This breaks oh-my-posh init, which
then leaves the prompt in a fallback state.

Fix: install/update PSReadLine via PowerShellGet to >= 2.3.5.
Per-user (-Scope CurrentUser) so we don't need elevation.

<!-- mios-src:fa9deff73bf0 from Get-MiOS.ps1:3487-3496 -->

### winget install fastfetch + stage MiOS-themed config and...

winget install fastfetch + stage MiOS-themed config and ASCII
logo at M:\MiOS\fastfetch\ (or LOCALAPPDATA fallback). The PS
profile invokes `fastfetch -c <staged>` on every MiOS shell
session start so the operator sees a MiOS-branded MOTD.

<!-- mios-src:bb34a542ebc2 from Get-MiOS.ps1:3520-3523 -->

### Stage the config + logo on M:\ (M:\-everywhere invariant --...

Stage the config + logo on M:\ (M:\-everywhere invariant -- no
LOCALAPPDATA fallback; Initialize-DataDisk creates M:\ before
any MiOS staging runs).

<!-- mios-src:bd4b101f8f80 from Get-MiOS.ps1:3557-3559 -->

### MUST write the JSONC config without a UTF-8 BOM....

MUST write the JSONC config without a UTF-8 BOM. fastfetch's
JSON parser is strict and rejects files starting with EF BB BF
("Error: failed to parse JSON config file"). Set-Content
-Encoding UTF8 prepends a BOM on Windows PowerShell 5.1 and
pwsh's "UTF8" alias too. Use System.IO.File.WriteAllText with
an explicit no-BOM encoding to match what fastfetch expects.

<!-- mios-src:a2823b2e7635 from Get-MiOS.ps1:3569-3574 -->

### Color substitution from mios.toml [theme.fastfetch] (SSOT)...

-- Color substitution from mios.toml [theme.fastfetch] (SSOT) --
Per "oh my posh and other settings should
source from the same toml sections for all platform for theme/
branding to be truly unified in code".  fastfetch's per-module
color overrides (logo / keys / title / output) ship with vendor-
default ANSI tags that match [theme.fastfetch] vendor defaults;
operator overrides via mios.html flow into every MiOS terminal
without touching this script.  Only fires when the resolved
value differs from vendor and is one of fastfetch's accepted
ANSI color names.

<!-- mios-src:51f7e92b0d9a from Get-MiOS.ps1:3588-3597 -->

### Per the M:\-everywhere invariant: the actual oh-my-posh...

Per the M:\-everywhere invariant: the actual oh-my-posh init
script lives at M:\MiOS\powershell\profile.ps1. The C:\ user
profile ($PROFILE.CurrentUserAllHosts) gets a tiny redirector
block that dot-sources the M:\ script -- so the operator can
edit the M:\ copy and every PS shell picks up changes on next
launch, without bouncing through C:\.

<!-- mios-src:3a58f5281b1f from Get-MiOS.ps1:3649-3654 -->

### Write the FULL oh-my-posh init script to...

Write the FULL oh-my-posh init script to M:\MiOS\powershell\profile.ps1.
The C:\ user profile only gets a thin redirector that dot-sources
this file -- so future edits to the M:\ copy take effect on next
shell launch with no C:\ round-trip.
Build the M:\ profile script. Self-heals every embedded artifact
(oh-my-posh config + fastfetch config + MiOS ASCII logo) on
dot-source if the file isn't already staged on disk -- so even
an operator who irm|iex'd an older Get-MiOS.ps1 without these
stages gets a fully-themed MiOS terminal on the next pwsh launch.

<!-- mios-src:e869e467289e from Get-MiOS.ps1:3674-3682 -->

### Lift terminal dims from mios.toml [terminal] (per...

Lift terminal dims from mios.toml [terminal] (per
feedback_mios_toml_html_global_dotfile -- mios.toml is THE
global dotfile). Vendor defaults: 80x30 (operator-defined MiOS
default) with frame at cols-1 / rows-1 so the dashboard fits
inside the borderless + scrollbar-less terminal without the
right border colliding with the line-wrap boundary.

<!-- mios-src:0cbe9379632f from Get-MiOS.ps1:3686-3691 -->

### frame_width default is COLS - 1 per operator "everything...

frame_width default is COLS - 1 per operator "everything should be
-1 width" -- 1-cell gutter on the right edge prevents the frame
from line-wrapping when WT reports WindowWidth one cell over
visible. mios.toml [terminal].frame_width is the SSOT; the
configurator HTML exposes this for operator override.
frame_height stays rows-1 so one row is reserved for the prompt.

<!-- mios-src:4f2ccf770c05 from Get-MiOS.ps1:3695-3700 -->

### right_margin

right_margin: cells of slack between the rightmost paintable cell
and the rightmost cell the dashboard frame / right-aligned prompt
block writes to. Default 2 because the operator reported "framing
too wide STILL" with the previous cols-1 (1 cell) margin -- WT's
pseudo-console reports WindowWidth 1 cell over the visible/
paintable cell count during the first paint (before the
scrollbarState='hidden' setting and its scrollbar-reservation
release have taken effect). cols-2 always avoids wrap.

<!-- mios-src:0bb2493b0c57 from Get-MiOS.ps1:3703-3710 -->

### EULA pre-print lines (mios.toml [messages.eula])...

-- EULA pre-print lines (mios.toml [messages.eula]) -------------
Read the toml once at install time and bake the resolved lines
as a literal PS array into the heredoc.  Operator edits via
mios.html flow on the next `mios update` re-run.  Get-MiosTomlValue
can't parse multi-line array values (its key regex doesn't span
lines), so use an inline DOTALL match here.

<!-- mios-src:71b1918c52a6 from Get-MiOS.ps1:3721-3726 -->

### MiOS PowerShell profile -- PSReadLine reload + fastfetch...

MiOS PowerShell profile -- PSReadLine reload + fastfetch MOTD +
oh-my-posh init.
Source of truth: this file lives on M:\ and is dot-sourced from
`$PROFILE.CurrentUserAllHosts AND from the WT MiOS profile's
explicit -Command preamble (so it ALWAYS runs in MiOS terminals,
even when the operator's $PROFILE has its own broken oh-my-posh
init that would otherwise override ours).
Self-heals every artifact (mios.omp.json, fastfetch config.jsonc,
mios.txt ASCII logo) from embedded base64 blobs if the canonical
disk copy is missing.

<!-- mios-src:bb11ccac7329 from Get-MiOS.ps1:3782-3791 -->

### ONCE-PER-SESSION GUARD. This script is dot-sourced from...

ONCE-PER-SESSION GUARD. This script is dot-sourced from BOTH
(a) the redirector in `$PROFILE.CurrentUserAllHosts AND
(b) the WT MiOS profile's -Command preamble.
Without this guard, both pathways fire Show-MiosDashboard +
oh-my-posh init -- the operator sees TWO stacked framed
dashboards. Session-scoped flag short-circuits subsequent calls.

<!-- mios-src:1c6ff969906d from Get-MiOS.ps1:3793-3798 -->

### UTF-8 codepage + Console encoding...

-- UTF-8 codepage + Console encoding ------------------------------
Operator-reported regression: powerline glyphs (U+E0B4 etc.) rendered
as 'î' mojibake -- WT was decoding the UTF-8 bytes as cp1252 because
this profile body wasn't setting chcp 65001 / Console.OutputEncoding.
Setting both ensures every glyph oh-my-posh emits to stdout renders
as the correct PUA cap, not the cp1252-mangled multi-char sequence.

<!-- mios-src:de3b7e90f5cf from Get-MiOS.ps1:3802-3807 -->

### Window resize + center (every MiOS pwsh)...

-- Window resize + center (every MiOS pwsh) --------------------
Dimensions sourced from mios.toml [terminal] (cols/rows/
scrollback_rows). Per feedback_mios_terminal_dimensions every
MiOS-spawned window opens at the configured size centered on
the active monitor. Apply BEFORE any output paints so the
operator never sees a default-sized window briefly before the
resize. Idempotent -- a second pass via the inner script
(Pass-2 elevation) is a no-op.

IMPORTANT GATE: only resize when we're actually in the MiOS APP
context (i.e. the WT MiOS profile launched us). Otherwise -- if a
child pwsh during BOOTSTRAP/INSTALL accidentally loads this profile
via `$PROFILE.CurrentUserAllHosts redirector -- the resize shrinks
the operator's 80x40 install conhost down to the 80x20 MiOS-app
size mid-install. Operator-reported regression: "window changes to
the MiOS Global sizes of 80x20 somewhere in the middle of the
installations". `$env:MIOS_APP_CONTEXT is set ONLY by the WT MiOS
profile commandline (see Install-MiOSTerminalProfile in Get-MiOS.ps1).

<!-- mios-src:a58a80b19583 from Get-MiOS.ps1:3813-3830 -->

### Center on the ACTIVE display (where the cursor currently...

Center on the ACTIVE display (where the cursor currently is),
NOT PrimaryScreen. On multi-monitor hosts the operator launches
mios.bat from whichever monitor they're working on; the window
should land THERE.

<!-- mios-src:c51cf90c00bc from Get-MiOS.ps1:3856-3859 -->

### NO TERMINAL-TYPE GATE. Always run the PSReadLine reload +...

NO TERMINAL-TYPE GATE. Always run the PSReadLine reload + oh-my-
posh init. The WT_SESSION gate on the previous version was
silently skipping the init when WT didn't set the env var early
enough -- producing the "theme works in normal terminal but not
MiOS Terminal" symptom. fastfetch is gated separately below
since its ASCII rendering only makes sense in a real terminal.

<!-- mios-src:f75af3f01364 from Get-MiOS.ps1:3868-3873 -->

### Import terminal completion modules ------------------------...

-- Import terminal completion modules ------------------------
Silent best-effort: each module is imported if installed,
skipped if not. Operator gets icon-aware ls (Terminal-Icons),
git tab-completion (posh-git), AI-style prediction
(CompletionPredictor), and command-not-found suggestions
(Microsoft.WinGet.CommandNotFound).

<!-- mios-src:043085015bd9 from Get-MiOS.ps1:3876-3881 -->

### PSReadLine reload -----------------------------------------...

-- PSReadLine reload -----------------------------------------
PowerShell 7.x ships with an in-box PSReadLine that's too old
for oh-my-posh init's Get-PSReadLineKeyHandler -Chord syntax.
Updating PSReadLine on disk (Install-Module) doesn't help the
CURRENT session because PSReadLine is autoloaded BEFORE the
profile runs. Force-import the newest installed version here
so oh-my-posh init's PSReadLine integration doesn't throw
"A positional parameter cannot be found that accepts argument
'Spacebar'/'Enter'/'Ctrl+c'".

<!-- mios-src:627f8a3882c9 from Get-MiOS.ps1:3888-3896 -->

### Resolve / self-heal MiOS artifact paths -------------------...

-- Resolve / self-heal MiOS artifact paths -------------------
M:\-everywhere invariant (operator: "irm|iex sets up M:\
disk/partition installs EVERYTHING to M:\ EVERYTHING").
M:\ is created at install time and never removed at runtime;
if it's missing, the install never completed and the operator
needs to re-run irm|iex.  The profile body falls back to a
warn rather than silently splitting state across drives.

<!-- mios-src:0a628376c8eb from Get-MiOS.ps1:3905-3911 -->

### Width adapts to LIVE terminal width every render so the...

Width adapts to LIVE terminal width every render so the dashboard
always renders edge-to-edge. "dashboards
should be edge to edge globally!! 80x20 window is the Global
benchmark!" + "opening MiOS app and using things like fastfetch
and btop--things that clear the screen; ends up fitting the
dashboards in the same original window and tab--eventually".

First-render timing: at session start, WT hasn't settled the
cell count yet. Solution: poll WindowWidth up to 5x with a
50ms gap until it stabilizes (two consecutive reads agree),
then use the stable value. After fastfetch/btop run, WT has
fully settled and subsequent renders read correctly.

<!-- mios-src:59fe70446c90 from Get-MiOS.ps1:3950-3961 -->

### Cap to mios.toml [terminal].frame_width (SSOT). WT's...

Cap to mios.toml [terminal].frame_width (SSOT). WT's
WindowWidth poll is unreliable during the first ~200ms after
spawn -- it can return a value 4-8 cells wider than the
final viewport (focus-mode + acrylic backdrop allocation
haven't settled). Without this cap, host_os/CPU/font lines
render at the inflated WIDTH, then WT re-sizes the buffer
narrower, and every overflowing line wraps -- pushing the
top frame off-viewport. Capping to the toml value (the
operator-declared "this is what 80x20 means") guarantees
the dashboard never renders wider than the declared frame.
Operator-flagged "ie..." / "on..." wraps in
MiOS-WIN dashboard with top frame clipped off-screen.

<!-- mios-src:ba428f47444e from Get-MiOS.ps1:3976-3987 -->

### Uniform frame color -- per "make the entire frame 1 uniform...

Uniform frame color -- per "make the
entire frame 1 uniform colour--make it a complimenting colour
to the windows colour that's sourced from the toml fields that
are relevant to MiOS's color palette colours". MiOS canonical
accent (mios.toml [colors].accent + [branding.dashboard].frame_color)
is operator-blue (#1A407F = ANSI 34 = [ConsoleColor]::Blue).
Embed ANSI 34 around every `$V` border so the per-content rows
render their borders in the SAME color as the standalone
top/divider/bottom Write-Host calls (which use
-ForegroundColor Blue). Without this, _Frame/_Center returned
a plain string that Write-Host emitted in the inherited
foreground (often cream from the MiOS scheme), making per-row
borders visually different from top/divider/bottom borders.

<!-- mios-src:ba1dda753b39 from Get-MiOS.ps1:3995-4007 -->

### Total budget

Total budget: frame_height rows total. Layout:
  1 top frame
  logo block       (compact: 0-1 row -- title only;
                    full:    N-row ASCII when budget allows)
  1 divider
  fastfetch block  (paired -- two modules per row)
  1 divider
  hints block      (compact: 1 line; full: 1-line-per-verb)
  1 bottom frame
Per operator: dashboard MUST fit in 80x20 (= frame_height 19).
Compact mode kicks in when frame_height < 25.

<!-- mios-src:81af7065bbf6 from Get-MiOS.ps1:4033-4043 -->

### 1-line title band -- resolves through mios.toml...

1-line title band -- resolves through mios.toml [dashboard].title
at runtime so the configurator HTML edits flow through to the
next render.  Vendor default is the technical descriptor
("MiOS  --  Immutable Fedora AI Workstation"); operators who
want the friendly "My Personal Operating System" face on the
dashboard subtitle override [dashboard].title via mios.html.

<!-- mios-src:ef6ccf97690d from Get-MiOS.ps1:4071-4076 -->

### Centered ASCII logo (operator-blue). Center the BLOCK (not...

Centered ASCII logo (operator-blue). Center the BLOCK (not
each line individually) -- the logo's internal alignment
depends on each line's leading whitespace.

<!-- mios-src:c746e415640d from Get-MiOS.ps1:4085-4087 -->

### Compact metric rows ---------------------------------...

-- Compact metric rows ---------------------------------
Driven by mios.toml [dashboard].rows -- side-by-side fields
per row keep the dashboard at ~5 metric rows so 80x20 leaves
ample room for the prompt and command output.  Per operator
"the dash is set GLOBALLY to Windows and Linux
dashboards!! same settings!!! ... smaller metric can be
side-by-side in the dash; freeing up more room for the
prompt field."  The Linux-side mios-dashboard.sh reads the
same [dashboard] section.

Field renderers fetch values via Get-CimInstance (single-
cached) / Get-Volume / `$PSVersionTable.  They each return a
short labeled string ("CPU AMD Ryzen 9 9950X3D 5.75GHz (32c)").
Unknown field-keys are silently skipped so the dashboard
is forward-compatible with future mios.toml additions.

<!-- mios-src:3a5f4b913efc from Get-MiOS.ps1:4108-4122 -->

### Compact OS caption

Compact OS caption: strip Microsoft prefix, the
"for Workstations" SKU suffix, "Insider Preview"
marketing, "(64-bit)" arch (it's redundant -- the
arch line covers it), and trailing whitespace.
Operator-flagged "Windows 11 Pro for
Workstations Insider Preview" overflowed the 80x20
frame and wrapped, pushing the top frame off-screen.

<!-- mios-src:9836fb8614e9 from Get-MiOS.ps1:4132-4138 -->

### PowerShell switch with regex condition matches but does NOT...

PowerShell switch with regex condition matches but
does NOT reliably populate `$Matches in the action
block scope -- saw `disk_c : err`
in the dashboard because `$Matches[1]` was \$null and
`$_dl` came back empty.  Parse the letter from `$_
directly via Substring instead.

<!-- mios-src:49255ef7ec38 from Get-MiOS.ps1:4195-4200 -->

### Try/catch per-field so a single broken renderer (e.g....

Try/catch per-field so a single broken renderer
(e.g. Get-Volume not available, lspci missing) doesn't
kill the whole loop -- saw the
dashboard render only the first 3 rows and bail because
the disk_c renderer's Get-Volume call raised in a
context where the Storage module wasn't loaded.

<!-- mios-src:a61fe3580b59 from Get-MiOS.ps1:4276-4281 -->

### MiOS services block ----------------------------------...

-- MiOS services block ----------------------------------
refresh: parity with the Linux-side
mios-dashboard.sh services grid. Each cell is a
<dot> <name> :<port> probe row. Endpoints reachable from
the Windows host go through localhost (WSL2's
localhostForwarding mirrors the dev VM's listening sockets
to the Windows loopback automatically). When a probe
fails -- service is down OR forwarding misses (a known
WSL2 networking flake) -- we show the dot as off and
carry the row anyway so the layout stays stable.

<!-- mios-src:0b7a39fc6c7a from Get-MiOS.ps1:4303-4312 -->

### Command hints rows ----------------------------------- Verb...

-- Command hints rows -----------------------------------
Verb list resolves through mios.toml [verbs] at RUNTIME (SSOT).
The dashboard re-reads on every render so an operator edit via
mios.html flows mios.toml -> dashboard immediately. No hard-
coding here. Vendor fallback only if every TOML candidate is
missing (cold first-run before M:\ overlay is staged).

<!-- mios-src:b7ac6bb2026b from Get-MiOS.ps1:4365-4370 -->

### NO inline-render here. The profile body is a thin function-...

NO inline-render here. The profile body is a thin function-
definition layer; the "what shows up on terminal spawn" is
whatever verb mios.toml [terminal.startup].windows points at.
The dispatch fires AT THE END of this profile (after the `mios`
verb function is defined). See the [terminal.startup] block
below the function definitions.
"have the bash and pwsh/WT environment/
dotfile(s) automatically run mios dash on open/launch--NOT
PRINT ON LAUNCH!!! THE ACTUAL ENV/DOTFILE(S) SHOULD DICTATE THE
COMMANDS/VERBS AND WHATS RUN ON CONSOLE SPAWN(ALL PLATFORMS
GLOBALLY)--ALL SOURCED FROM THE MIOS.TOML"

<!-- mios-src:a979639481c5 from Get-MiOS.ps1:4418-4428 -->

### oh-my-posh init -------------------------------------------...

-- oh-my-posh init -------------------------------------------
Capture the init script output, then regex-patch the broken
positional Get-PSReadLineKeyHandler calls. Older oh-my-posh
versions emit `Get-PSReadLineKeyHandler Spacebar` etc. -- which
NO PSReadLine version accepts (the cmdlet's parameter binder
has no positional [string]). Latest oh-my-posh emits -Chord
<key>. We inject -Chord even when running latest, since it's
idempotent (latest already has it). This makes oh-my-posh's
PSReadLine integration work regardless of installed version.

<!-- mios-src:b9e9a2dab119 from Get-MiOS.ps1:4430-4438 -->

### Shell-aware

Shell-aware: oh-my-posh init pwsh emits PS 7+ syntax that
FAILS silently in Windows PowerShell 5.1, leaving the
operator's pre-existing broken init showing "CONFIG NOT
FOUND". Detect PS edition and use the matching arg
(`powershell` for 5.1 / Desktop, `pwsh` for 7+ / Core).

<!-- mios-src:50d02e92b4a1 from Get-MiOS.ps1:4440-4444 -->

### MiOS commands...

-- MiOS commands ---------------------------------------------------
Defined in EVERY pwsh session (not gated on WT_SESSION) so the
operator can run mios-build / mios-update / mios-help from any shell.
Each command fetches its target script fresh from
raw.githubusercontent.com so the operator doesn't have to manually
pull the mios-bootstrap repo. Cache-busting via ?cb=<unix-time>
defeats Fastly's 5-minute max-age.

<!-- mios-src:abd471681485 from Get-MiOS.ps1:4458-4464 -->

### New flow (per operator: "mios build should queue the build...

New flow (per operator: "mios build should queue the build, launch
the html file in the local windows browser window, fetch the newly
minted html/toml files to the overlay >> start the build with new
key steps implemented"):

  1. Open mios-config.html in the default Windows browser so the
     operator can edit theming / functionality / package lists.
  2. Wait for the operator to save + close the configurator (or
     hit Enter to skip the edit pass).
  3. mios-pull to sync M:\ overlay to origin/main + apply user edits.
  4. Run build-mios.ps1 -BuildOnly so it skips the bootstrap phase
     and goes straight into the OCI build inside MiOS-DEV.

Bypass the configurator pass with: mios build -SkipConfig
Bypass the pull pass        with: mios build -SkipPull

<!-- mios-src:3d9f11995dde from Get-MiOS.ps1:4471-4485 -->

### Capture mtime BEFORE opening so we can tell if the operator...

Capture mtime BEFORE opening so we can tell if the operator
actually saved a new copy (the browser saves to Downloads
because file:// URLs can't write back to source). Used by
the promote step below.

<!-- mios-src:9747fca8084a from Get-MiOS.ps1:4498-4501 -->

### Step 2

-- Step 2: promote downloaded mios.toml from Downloads ----
The browser saves to %USERPROFILE%\Downloads (file:// URLs
can't write back to source). Scan for any mios*.toml /
*mios*.html newer than the in-place overlay copies and
PROMOTE them to M:\etc\mios\ + M:\usr\share\mios\configurator\.
Also archive the imported source so we don't double-promote
on the next mios-build run.

<!-- mios-src:233519a7a866 from Get-MiOS.ps1:4517-4523 -->

### Archive the source so a re-run of mios build doesn't...

Archive the source so a re-run of mios build doesn't
re-promote the same file. Keep it (don't delete) so
the operator can recover if something went wrong.

<!-- mios-src:70c617394dd5 from Get-MiOS.ps1:4548-4550 -->

### Step 3

-- Step 3: sync overlay so the build sees the latest mios.toml -
Note: this runs AFTER the Downloads-promote step so mios-pull
sees the just-promoted files in M:\etc\mios. mios-pull's git
reset --hard would otherwise blow away the operator's changes
if they lived in the tracked tree.

<!-- mios-src:db73e315cd01 from Get-MiOS.ps1:4578-4582 -->

### MINI dashboard -- the compact 80x20 framed banner +...

MINI dashboard -- the compact 80x20 framed banner + fastfetch
info. This is what fires on every shell spawn (vendor default
of [terminal.startup].verb). "have launch
be the mini-dashboard ... NOT PRINT ON LAUNCH" -- the dotfile
dispatches THIS verb so the render comes from a verb command,
not inline-print in the profile body.

<!-- mios-src:5f7256caea1f from Get-MiOS.ps1:4663-4668 -->

### FULL MiOS dashboard -- ASCII banner + fastfetch (full...

FULL MiOS dashboard -- ASCII banner + fastfetch (full width,
no compact frame trim) + MiOS-DEV service status + extended
sys specs. "the invoked 'mios dash'
command(s) runs the FULL MiOS dashboard; showing all service's
and relevant MiOS system specs too--include the MIOS ASCII
banner in the full dash!"

<!-- mios-src:d037c96248d1 from Get-MiOS.ps1:4679-4684 -->

### Unified `mios <verb>` dispatcher. Operator types `mios...

Unified `mios <verb>` dispatcher. Operator types `mios build` or
`mios b<TAB>` (PSReadLine + the ArgumentCompleter below complete to
`mios build`). Falls through to `mios-<verb>` so the same wrappers
back both call shapes.
Known verbs dispatch to mios-<verb>.ps1 wrappers in `$Global:MiosBin.
Anything that isn't a known verb is routed to Hermes-Agent at
MIOS_AI_ENDPOINT as a chat completion, so `mios how do I bootc switch`
works from any PowerShell terminal without a separate `ask` verb.

<!-- mios-src:d17615a3692f from Get-MiOS.ps1:4772-4779 -->

### Interactive-shell startup verb (SSOT: mios.toml...

-- Interactive-shell startup verb (SSOT: mios.toml [terminal.startup]) --
The profile body above is JUST function definitions. What runs on
terminal spawn is the verb declared in mios.toml -- read fresh
every shell launch so HTML configurator edits flow through with
zero re-bake. Vendor default is "dash" but the operator can flip
to any other verb (or "" for a silent shell).

Per-platform key precedence: [terminal.startup].windows wins over
[terminal.startup].verb (the cross-platform default). The Linux
bash side reads the same TOML keys (.linux > .verb).

Guards:
  - `$env:MIOS_SKIP_MOTD = "1"      -> no startup verb fires.
  - non-interactive host           -> no fire (background scripts,
                                      VS Code's PowerShell extension
                                      integrated terminal, etc.).
  - `$Global:MiosStartupVerbFired   -> idempotent across re-sources
                                      (mios.ps1 dot-sources this
                                      profile to load functions, we
                                      don't want a recursive verb
                                      call inside an already-running
                                      verb).

<!-- mios-src:a6a0339ccc0a from Get-MiOS.ps1:4817-4838 -->

### Vendor fallback

Vendor fallback: mini (the compact 80x20 framed banner).
`dash` is the FULL render -- ASCII banner + service status +
extended sys specs -- explicitly invoked by the operator,
not auto-fired on every shell spawn.

<!-- mios-src:c0226c9181ad from Get-MiOS.ps1:4860-4863 -->

### Write the profile body with explicit UTF-8 BOM. The body...

Write the profile body with explicit UTF-8 BOM. The body contains
Unicode box-drawing chars (+ + + + | - + +) for the dashboard
frame; without a BOM, PowerShell falls back to system codepage
(CP1252 on US Windows) when reading no-BOM files in some
contexts, parsing each UTF-8 byte as a separate Latin-1 char
and exploding with "Unexpected token 'â”€'" at parse time.
[IO.File]::WriteAllText with UTF8Encoding($true) writes the
3-byte 0xEF 0xBB 0xBF BOM up front so EVERY PS host (5.1, 7.x,
ISE, VS Code) decodes the file as UTF-8 deterministically.

<!-- mios-src:f4cea0117e2a from Get-MiOS.ps1:4875-4883 -->

### Append a diagnostic block to M:\MiOS\powershell\profile.ps1...

Append a diagnostic block to M:\MiOS\powershell\profile.ps1 that
writes [Console]::WindowWidth + BufferWidth + LASTEXITCODE-style
context to M:\MiOS\diagnostics\window-width.txt at every profile
load. Operators (and the AI agent debugging wrap issues) can read
this file to know the EXACT cell count WT is reporting on the
operator's hardware -- no more guessing right_margin values from
screenshots. Re-runs append (with timestamp) so we get a history
across MiOS WT launches. Per operator's 5-hour iteration spiral
STOP guessing margin values, measure the actual width.

<!-- mios-src:c7a4de39bb54 from Get-MiOS.ps1:4911-4919 -->

### MiOS WindowWidth diagnostic (auto-appended by...

-- MiOS WindowWidth diagnostic (auto-appended by Install-MiOSPowerShellProfile) --
Every MiOS pwsh launch appends one line to M:\MiOS\diagnostics\window-width.txt
capturing [Console]::WindowWidth + BufferWidth + WT_SESSION + timestamp.
This is the SOURCE OF TRUTH for the actual visible cell count on the
operator's hardware -- if WindowWidth != mios.toml [terminal].cols, the
delta is the WT chrome budget that right_margin must absorb.

<!-- mios-src:b38ecb3d63ba from Get-MiOS.ps1:4922-4927 -->

### DPI-aware centered position for an 80x30 acrylic focus-mode...

DPI-aware centered position for an 80x30 acrylic focus-mode window.

Cell metrics (Geist Mono 12pt @ 100% DPI, lineHeight=1.0): ~10 × 20 px
→ grid 800 × 600 px → 4:3 exactly.

Window-level slack (DWM frame + scrollbar + acrylic edge in focus mode):
+20 px width, +12 px height. So the wt.exe outer rect is ~820 × 612 px
at 100% DPI on a typical Win11 build.

Robustness layers:
  1. SetProcessDPIAware() -- without this, on 125%/150% scaled displays
     Screen.WorkingArea returns LOGICAL pixels and our --pos math is
     off by the scale factor (window lands top-left).
  2. Cursor-monitor detection -- PrimaryScreen always sends the window
     to display #1 even when the operator is on display #2. Use
     Screen.FromPoint(Cursor.Position) so the window opens on whichever
     monitor the operator is actively using.
  3. Post-launch correction -- wt.exe sometimes ignores --pos in focus
     mode (1.18+ regression). Move-MiOSWindowToCenter (called from the
     relaunch path after Start-Process) finds the WT hwnd and moves it
     to the true center. This is the belt-AND-braces guarantee that
     'exit' is type-able because the window is on-screen.

<!-- mios-src:73c77a41c134 from Get-MiOS.ps1:4947-4968 -->

### Post-launch re-center

Post-launch re-center: WT in focus mode sometimes lands at (0,0) or at
the previous WT window's last position because it ignores --pos. We
wait up to ~3s for a WindowsTerminal.exe process to surface a top-level
hwnd, GetWindowRect to read its real outer-rect size, then SetWindowPos
to (screenCenter - rect/2). This guarantees the window is exactly
screen-center regardless of what WT did with --pos.

<!-- mios-src:f71d462c5bcf from Get-MiOS.ps1:5000-5005 -->

### IMPORTANT

IMPORTANT: do NOT strip WS_THICKFRAME / WS_CAPTION via
SetWindowLongPtr -- DWM's acrylic compositor REQUIRES those style
bits to allocate the per-window swap chain that backs the blur
surface. Earlier revisions stripped them for "completely
borderless" -- and the cost was no acrylic at all (the window
rendered as a flat black popup). The WT-side `--focus` flag +
padding=0 + suppressApplicationTitle gives the closest-to-
borderless WT can deliver while keeping acrylic alive: a 1px
DWM resize frame remains, but the titlebar / tab row / min-max
buttons are all gone.

<!-- mios-src:02ad7ce8863e from Get-MiOS.ps1:5036-5045 -->

### Re-center 3 times with 350ms gaps. WT in focus mode often...

Re-center 3 times with 350ms gaps. WT in focus mode often animates
the window to its last-known position AFTER the first SetWindowPos
registers, then settles. A single move loses the race; three
spaced-out moves stick. Each iteration re-reads the outer rect
(size can shift slightly during animation) so center math is
always against the current dimensions.

<!-- mios-src:1cabe03bd558 from Get-MiOS.ps1:5047-5052 -->

### By the time we reach this point we're GUARANTEED admin --...

By the time we reach this point we're GUARANTEED admin -- the
auto-elevation block at the top of the script (right after the
agreement-gate function definition) returned out of Pass-1 if the
operator pasted from a non-admin shell, and only Pass-2 (the elevated
relaunch) ever falls through to here. Code below runs in Pass-2 only.

<!-- mios-src:d5f31b3c7265 from Get-MiOS.ps1:5072-5076 -->

### Bootstrap winget (Microsoft.DesktopAppInstaller) on a...

Bootstrap winget (Microsoft.DesktopAppInstaller) on a Windows host
that doesn't ship it. Win11 has it preinstalled; Win10 22H2 also
ships it; but Windows Server, Sandbox, debloated images, and very
fresh OOBE machines sometimes don't. winget is the prerequisite
for every package install downstream (WSL, Podman, Windows Terminal,
PowerShell 7, oh-my-posh, fastfetch, etc.) so failing here means
NOTHING else installs.

Operator directive "Make sure the irm|iex installer
can STILL install on a fresh Windows System with NOTHING installed".

<!-- mios-src:b5ffbad1c394 from Get-MiOS.ps1:5093-5102 -->

### Detect + enable the OS-level features MiOS needs...

Detect + enable the OS-level features MiOS needs:
  Microsoft-Windows-Subsystem-Linux   -- WSL substrate
  VirtualMachinePlatform              -- WSL2 (HCS) + Hyper-V hypervisor
  Microsoft-Hyper-V                   -- Hyper-V Manager + VMs (Pro/Ent)

All require admin (DISM-level feature toggles). Caller is responsible
for admin context -- Get-MiOS.ps1 self-elevates via UAC before any
call site reaches this function, so we hard-fail with a clear message
rather than silently skipping if we somehow land here as a normal user.

"pwsh7+, podman, wsl, hyper-v, etc-etc are all
fecthed and installed during irm|iex installations -- THE FIRST
STEPS AFTER DISK CREATION". This function is Step 0.6 in Pass-2,
immediately after Initialize-DataDisk + Set-PodmanMachineStorageOnM
+ Set-WingetStorageOnM + mios.toml promotion to M:\.

Reboot policy: enables with -NoRestart and aggregates which features
required a reboot. Surfaces a clear warning at the end if any
reboot is pending; doesn't reboot automatically (operator-flagged:
NO automatic mid-install reboots).

<!-- mios-src:0ed8f61076f9 from Get-MiOS.ps1:5159-5178 -->

### TOML-first per AGENTS.md §3 -- feature DISM names resolve...

TOML-first per AGENTS.md §3 -- feature DISM names resolve from
mios.toml [bootstrap.prereqs.features].* so operators can swap
Hyper-V for Hyper-V-Core, add Containers/SMBDirect, etc., via
mios.html. Order matters (WSL substrate before VMP before Hyper-V);
use [ordered] to preserve insertion order. Build via .Add() (void
return) instead of $features[k]=v to avoid any indexer-emit leak
into the function's pipeline output (operator-confirmed
the indexer-assignment form leaked the assigned value into the
function's return stream, making `$_featResult -eq 'reboot-required'`
filter-match a multi-element array even when rebootPending stayed
$false -- spurious Pass-2 halt despite all 3 features already
Enabled).

<!-- mios-src:1dcf45df54a8 from Get-MiOS.ps1:5185-5196 -->

### Get-WindowsOptionalFeature threw. Either the feature...

Get-WindowsOptionalFeature threw. Either the feature genuinely
isn't on this edition (e.g. Hyper-V on Home), OR the legacy
optional-feature name no longer exists because WSL is now
Store-distributed (WSL 2.x MSIX needs only VirtualMachinePlatform,
not the deprecated 'Microsoft-Windows-Subsystem-Linux' feature).
If wsl.exe already works, the substrate is satisfied regardless
of optional-feature state -- don't emit a scary "not available".

<!-- mios-src:8ed7ac7e23de from Get-MiOS.ps1:5208-5214 -->

### WSL bootstrap on fresh Windows...

--- WSL bootstrap on fresh Windows ----------------------------------
Fresh Windows 11 doesn't ship wsl.exe -- it's a separate Store-distributed
MSIX app since 2022. On a clean machine, DISM enables the Windows feature
("Microsoft-Windows-Subsystem-Linux") but the actual wsl.exe binary +
the WSL kernel are downloaded from the Store. `wsl --install` (DISM-era
path) auto-pulls them on first run; we drive it explicitly so the
operator sees a known transcript instead of waiting on opaque downloads.

Operator-flagged "MiOS should be running preview builds
of WSL. Make sure the irm|iex installer can STILL install on a fresh
Windows System with NOTHING installed".

<!-- mios-src:078b1c92c75c from Get-MiOS.ps1:5238-5248 -->

### TOML-first -- WSL Store MSIX winget ID from mios.toml...

TOML-first -- WSL Store MSIX winget ID from mios.toml
[bootstrap.prereqs].wsl_pkg (operator can pin to Microsoft.WSL
preview channel via mios.html).

<!-- mios-src:233b3297318f from Get-MiOS.ps1:5250-5252 -->

### WSL kernel update + opt into PRE-RELEASE channel (preview...

WSL kernel update + opt into PRE-RELEASE channel (preview builds).
`wsl --update` pulls the latest MSIX kernel from Microsoft Store;
`--pre-release` flag (added in WSL 2.0.0, available on every modern
Windows + WSL combo) opts into the preview build channel which has
the newer compositor + gnome-shell --nested fixes operator needs
for the Enhanced Session full-desktop path.
`--set-default-version 2` ensures wsl --install / `wsl --import`
use WSL2 (HCS via VirtualMachinePlatform) by default.

<!-- mios-src:200a56ee7396 from Get-MiOS.ps1:5280-5287 -->

### TOML-first -- mios.toml...

TOML-first -- mios.toml [bootstrap.prereqs.features].require_reboot_to_continue
decides whether Pass-2 halts here (so downstream WSL-dependent
steps don't cascade-fail) or surfaces a warning and continues.
Operator default: halt (true), since on a truly fresh Windows
the dev VM, podman machine init, and OCI build all REQUIRE the
reboot; trying to run them just produces noise + half-broken
state. Operator opts to "continue anyway and watch what
survives" by setting it to false in mios.html.

<!-- mios-src:14737ddc2c17 from Get-MiOS.ps1:5313-5320 -->

### ALWAYS install RedHat.Podman (the CLI MSI) -- this is what...

ALWAYS install RedHat.Podman (the CLI MSI) -- this is what actually
lays down podman.exe with PATH integration. Podman Desktop alone
bundles the CLI internally but doesn't expose it on PATH; the
standalone CLI package does. Idempotent: winget no-ops if already
present.
TOML-first -- Podman CLI MSI ID from mios.toml [bootstrap.prereqs].podman_cli_pkg

<!-- mios-src:cdb3a5b550f6 from Get-MiOS.ps1:5430-5435 -->

### NOTE

NOTE: do NOT exit 1 here. build-mios.ps1's Phase 2 (machine init)
talks to Podman Desktop's API directly via the WSL distro -- it
doesn't need podman.exe on the Windows-side PATH to function.
Per operator: "no 'restart this shell' or 're-run' anything!!!!
automated!!!!!"

<!-- mios-src:ff619ec48c7f from Get-MiOS.ps1:5539-5543 -->

### Invoke-MiOSFullReap -- Phase 0 reap of every prior MiOS...

-----------------------------------------------------------------------------
Invoke-MiOSFullReap -- Phase 0 reap of every prior MiOS artifact
-----------------------------------------------------------------------------
Per feedback_mios_entry_full_reset memory:
  "every irm|iex must reap ALL prior MiOS state: temp clones, persistent
  clones, WSL distros (MiOS / MiOS-DEV / podman-MiOS-DEV / MiOS-BUILDER),
  podman machines, Hyper-V VMs (MiOS-*), install dirs (M:\ contents +
  %PROGRAMDATA%\MiOS / %LOCALAPPDATA%\MiOS / %APPDATA%\MiOS), Start Menu
  shortcuts, registry uninstall key. No partial state; no carry-over."
C:\MiOS + C:\mios-bootstrap are PROTECTED -- operator dev working trees
of mios.git + mios-bootstrap.git per feedback_mios_no_c_drive_fallback.

AND per "If the uninstaller actually uninstalled
things automatically every time; I wouldn't have to Manually uninstall
anything EVERY TIME it fails!!!!"

Two callers:
  1. Phase 0 of the irm|iex main flow -- runs BEFORE Initialize-DataDisk
     so every install starts from zero state regardless of prior runs.
  2. The top-level failure trap -- runs on any unhandled exception so a
     half-broken install never leaves stale state behind.

Idempotent: every block is wrapped in EAP=SilentlyContinue + try/catch so
missing artifacts are no-ops. Logs each category's outcome to stdout in
DarkGray so the operator sees what's being reaped without noise.

Scope (matches uninstall.ps1's 12-category contract + Hyper-V + persistent
clones):
  1. Podman machines (MiOS-DEV, MiOS-BUILDER, plus any podman-MiOS-* WSL distro)
  2. WSL distros (MiOS, MiOS-DEV, podman-MiOS-DEV, MiOS-BUILDER, podman-MiOS-BUILDER)
  3. Hyper-V VMs matching MiOS-*
  4. Install dirs: M:\ contents (everything except drive root metadata),
     %PROGRAMDATA%\MiOS, %LOCALAPPDATA%\MiOS, %APPDATA%\MiOS.
     NEVER C:\MiOS (operator dev tree of mios.git -- protected).
  5. WT settings.json -- launchMode, profiles.defaults MiOS keys, MiOS scheme,
     MiOS / MiOS-WIN / MiOS-DEV / podman-MiOS-* profiles
  6. PowerShell profile redirector blocks (10 candidate paths, marker-delimited)
  7. Fonts: Geist + symbols-only Nerd Font + matching HKCU font reg entries
  8. PATH env entries pointing into M:\MiOS\bin (HKCU + HKLM)
  9. HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\MiOS
 10. Start Menu folder + Desktop .lnk shortcuts (every legacy variant)
 11. AppUserModelID HKCU/HKLM\Software\Classes\AppUserModelId\MiOS.Workstation
 12. podman-machine state symlinks (3 candidate paths)
 13. MIOS_*/MiOS_* environment variables (HKCU + HKLM)

Non-destructive: NEVER touches C:\mios-bootstrap OR C:\MiOS (both are
operator dev clones -- may have uncommitted work), the operator's
pwsh profile body outside the >>> MiOS ... >>> markers, or any
non-MiOS WT profiles / schemes / fonts.

<!-- mios-src:6bf7bc3bddc5 from Get-MiOS.ps1:5547-5595 -->

### SSOT

SSOT: every operator-visible reap string resolves through
mios.toml [messages.reap].* with the hardcoded fallback as Default.
Per feedback_mios_messages_section_ssot: no Write-Host literals.

<!-- mios-src:0281334da27d from Get-MiOS.ps1:5601-5603 -->

### 4. Install dirs. PROTECTED FROM REAP -- operator-owned dev...

4. Install dirs. PROTECTED FROM REAP -- operator-owned dev trees:
  * C:\MiOS            -- dev working tree of mios.git (memory:
                           feedback_mios_no_c_drive_fallback;
                           ".git IS /" working tree). End consumers
                           never have this dir, so deleting it
                           only ever destroys operator dev work.
Operator-flagged after this
                           trap fired on a Phase-3 reap-on-failure
                           and wiped their checkout (uncommitted
                           edits unrecoverable -- no shadow copies).
  * C:\mios-bootstrap  -- dev working tree of mios-bootstrap.git
                           (same protected category).

MiOS owns M:\ exclusively (see block below) + a few %ProgramData% /
%LOCALAPPDATA% / %APPDATA% caches that ARE install-managed.

<!-- mios-src:73734c1a87ce from Get-MiOS.ps1:5649-5663 -->

### Desktop folders also collect Windows scratch artifacts like...

Desktop folders also collect Windows scratch artifacts like
`.tmp.driveu...` from disk-shrink/format operations. These aren't
MiOS-managed but they appear during the Initialize-DataDisk shrink
and confuse the operator (they look like leftover MiOS junk).
Reap any .tmp.* item from desktop dirs only (NOT Start Menu --
those are the actual install targets for MiOS shortcuts).

<!-- mios-src:aeaae63bb2eb from Get-MiOS.ps1:5825-5830 -->

### Recursively remove MiOS\Linux Apps\ subfolder (Files / Web...

Recursively remove MiOS\Linux Apps\ subfolder (Files / Web / VSCodium /
Flatseal / Extension Manager / Ptyxis / System Monitor / Settings)
created by Install-WindowsBranding's Linux Apps loop. Operator
"uninstaller STILL doesn't uninstall everything from
windows" -- the named-.lnk loop above left Linux Apps\ orphaned.

<!-- mios-src:76e62210ff3d from Get-MiOS.ps1:5847-5851 -->

### 16a. Windows Firewall inbound rules with the "MiOS -"...

16a. Windows Firewall inbound rules with the "MiOS -" prefix.
Paired with build-mios.ps1 :: Set-MiosLanFirewallRules. Sweep by
DisplayName prefix so we never touch operator-authored rules.

<!-- mios-src:f8f94ed3cf96 from Get-MiOS.ps1:5943-5945 -->

### 17. Prepare M:\ for a fresh MiOS tree. HISTORICALLY this...

17. Prepare M:\ for a fresh MiOS tree. HISTORICALLY this FULL-formatted
M:\ on the premise "MiOS owns this entire volume" -- true on a clean
provision. But a MiOS-Xbox-provisioned host (this machine was the first
MiOS-Xbox deployment) can later carry the ACTIVE Windows pagefile and
Windows UUP staging on M:\ because C:\ is too small to hold them.
Formatting there would strip the live pagefile with nowhere to recreate
it (C:\ full) and destroy unrelated data. So: full-format ONLY when M:\
is a DEDICATED MiOS volume (no pagefile, nothing but MiOS artifacts);
otherwise surgically remove just the MiOS dirs and preserve the rest.

<!-- mios-src:7927e37a8242 from Get-MiOS.ps1:5963-5971 -->

### Install-robustness do NOT hard-exit on a box that cannot...

Install-robustness do NOT hard-exit on a box that cannot
free the full 256 GB (256/512 GB laptop SSDs, or a heavily-used C:).
CLAMP the data partition to the largest fittable size, down to a floor
([bootstrap.host_storage].min_shrink_mb, default 64 GB); only abort if
even the floor won't fit -- and then `throw` (TRAPPABLE by the caller's
try/catch) instead of a bare `exit 1` (which terminated the whole
runspace, so the caller's catch + remediation never ran).

<!-- mios-src:befa23a3aeff from Get-MiOS.ps1:6040-6046 -->

### Functions-only dot-source gate...

-- Functions-only dot-source gate -------------------------------------------
Per "irm|iex is the main entry point for ALL things
MiOS... FIX all in code!". The canonical entry is:
  irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex
which falls through to the Pass-1 main flow below (M:\ provisioning + Step
1-8 chain + bootstrap.ps1 handoff). EVERY install path -- whether triggered
by the irm|iex one-liner, the MiOS launcher, mios-update, or build-mios.ps1
-- routes through these same Install-MiOS* functions so the deployed state
is deterministic regardless of entry path.

build-mios.ps1's Install-MiosLauncher dot-sources THIS script with
$env:MIOS_GETMIOS_FUNCTIONS_ONLY=1 set so it can reuse the function
definitions (Install-MiOSPowerShellProfile, Install-MiOSTerminalProfile,
etc.) without re-entering the main flow. Without this gate, dot-sourcing
would re-trigger Initialize-DataDisk + Step 1-8 + the bootstrap.ps1
handoff, which would recurse infinitely (build-mios.ps1 was called BY
bootstrap.ps1 in the first place).

<!-- mios-src:724f4770e7cc from Get-MiOS.ps1:6186-6202 -->

### Step 0

-- Step 0: M:\ provisioning BEFORE Pass-1 stages anything -------------------
Per operator: "EVERYTHING MIOS RELATED--EVEN WINDOWS COMPONENTS INSTALLED--
ARE ALL INSTALLED ON THE CREATED M:\ Drive/Partition!!!"

Pass-1 below stages the WT MiOS profile, MiOS PS profile body, native-app
launcher, fastfetch config, oh-my-posh theme. ALL of those have a "M:\ if
exists else %USERPROFILE%\..." fallback -- without M:\ provisioned FIRST,
files land on C:\ and Pass-2's later Initialize-DataDisk creates an empty
M:\ partition while the staged content is stuck in C:\ (split state).

This block creates M:\, junctions podman-machine + winget storage paths
onto M:\, so Pass-1's WT install + winget tools install + profile staging
all land on M:\ from the very first write. The Pass-2 calls to the same
functions are idempotent no-ops.
-- Defender exclusions BEFORE anything else --------------------------------
16:48 install: Microsoft Defender AMSI blocked
build-mios.ps1 with "This script contains malicious content and has
been blocked by your antivirus software". The C# Add-Type blocks for
IPropertyStore + PROPVARIANT + StringToCoTaskMemUni (AppUserModelID
stamping) match heuristic patterns that malware uses for shortcut-
persistence -- false positive that kills the install.

Pre-add Defender exclusions for the MiOS-owned paths so AMSI skips
scanning them. Requires admin (Pass-2 elevated context). Wrapped in
try/catch -- if the operator's Group Policy forbids Set-MpPreference,
we continue silently and let AMSI do its thing (the bait-reduction
refactor in build-mios.ps1 should keep most installs unblocked).

<!-- mios-src:946d7cb6a9f1 from Get-MiOS.ps1:6211-6237 -->

### SSOT

SSOT: exclusion paths + processes resolve through mios.toml
[security.defender_exclusions].* with vendor defaults baked here.
Operator can add their own paths via mios.html -> mios.toml.

<!-- mios-src:e83120b987e8 from Get-MiOS.ps1:6240-6242 -->

### Pre-Phase-0

-- Pre-Phase-0: write .wslconfig BEFORE the very first wsl.exe call ---------
Mirrored networking + firewall=false are read by WSL2 when the
UTILITY VM starts. The utility VM starts on the FIRST wsl.exe
invocation anywhere in this run -- and Invoke-MiOSFullReap below
calls `wsl --unregister` + `wsl --shutdown` before anything else.
If .wslconfig isn't on disk by then, the utility VM that those reap
calls implicitly boot lands in legacy NAT mode and STAYS there until
the next time someone explicitly stops it. Symptom the operator hit
every container port (cockpit 8090, forge_http 8300,
open_webui 8033, hermes 8642, searxng 8899, llm-light 8450) timed out from
Windows even though `ss -tlnp` inside MiOS-DEV showed the binds, and
the host showed `vEthernet (WSL (Hyper-V firewall))` (NAT-only
adapter) instead of the IP-mirrored topology.
build-mios.ps1 Phase 3 still writes .wslconfig before podman-machine
init (belt-and-suspenders); this earlier write is what makes that
work even after the reap's wsl.exe calls.
Pre-Phase-0 .wslconfig writer -- TOML-first per AGENTS.md §3 / mios.toml
is THE singular SSOT for every operator-visible value. Resolve from the
layered overlay (~/.config > /etc > /usr/share); falls back to the
safe default (NAT + localhostForwarding) on a fresh host where mios.toml
isn't deployed yet. Mirrored mode opt-in: edit [wsl2].networking_mode
in mios.html, save, re-run irm|iex (read the [wsl2] comment block in
the vendor mios.toml for the prerequisites).

<!-- mios-src:5db16057c514 from Get-MiOS.ps1:6269-6291 -->

### Phase 0

-- Phase 0: Reap ALL prior MiOS state BEFORE anything else -----------------
Per feedback_mios_entry_full_reset memory: "every irm|iex must reap ALL
prior MiOS state... No partial state; no carry-over." AND operator
"If the uninstaller actually uninstalled things automatically
every time; I wouldn't have to Manually uninstall anything EVERY TIME it
fails!!!!". Runs UNCONDITIONALLY on every irm|iex invocation -- even if
nothing prior is installed (idempotent no-op).

<!-- mios-src:6ccfe0f2a5c4 from Get-MiOS.ps1:6351-6357 -->

### Failure-trap auto-reap...

-- Failure-trap auto-reap --------------------------------------------------
Operator contract "If the uninstaller actually uninstalled
things automatically every time; I wouldn't have to Manually uninstall
anything EVERY TIME it fails!!!!". Phase 0 reap above already handled the
"next irm|iex starts clean" case. This trap handles the "current install
fails mid-way" case -- terminating errors here trigger a final reap so
Windows is left in zero-state immediately on failure (operator never sees
half-broken state). Runs in addition to (not replacing) Phase 0.

SSOT: every operator-visible string resolves through mios.toml
[messages.failure_trap].* with the hardcoded fallback as Default.

<!-- mios-src:d46ddd39a0a8 from Get-MiOS.ps1:6360-6370 -->

### Factory-fresh guard

Factory-fresh guard: everything below (podman/winget storage, the mios.toml
promotion, the repo clone) targets M:\. Initialize-DataDisk already clamps the
carve down to what C: can spare (64 GB floor), so if we STILL have no M: volume
the disk genuinely cannot provide it -- STOP with an actionable reason instead
of silently cascading a broken install onto a drive that does not exist.

<!-- mios-src:42e066e33d9e from Get-MiOS.ps1:6415-6419 -->

### Step 0.5

Step 0.5: Promote the fetched vendor mios.toml to BOTH M:\usr\share\mios
and M:\etc\mios so the Windows-side dashboard / wrappers / Show-MiosDashboard
read the same [dashboard].rows / [colors] / [ports] / [packages.windows]
as the Linux side. Without this step Show-MiosDashboard falls back to its
vendor row-layout when M:\etc\mios\mios.toml is missing or stale, and
operator sees a different dashboard layout in pwsh vs in MiOS-DEV bash
(operator-flagged "MIOS.TOML ISN'T USED GLOBALLY"). Idempotent:
overwrites the M:\ overlay on every install with the live origin/main
fetch so a re-run always picks up the latest configurator edits.

<!-- mios-src:aafce3e07fd0 from Get-MiOS.ps1:6448-6456 -->

### Step 0.6

Step 0.6: Enable Windows OS-level features MiOS depends on (WSL +
VirtualMachinePlatform + Hyper-V). "pwsh7+,
podman, wsl, hyper-v, etc-etc are all fecthed and installed during
irm|iex installations -- THE FIRST STEPS AFTER DISK CREATION". This
runs as Step 0.6 -- after Initialize-DataDisk + the storage redirects
+ mios.toml M:\ promotion, before Pass-1 Windows-user-scope setup.
Requires admin; function self-checks and defers cleanly otherwise.

<!-- mios-src:6bd5ae1c50f6 from Get-MiOS.ps1:6475-6481 -->

### Hyper-V Firewall must allow inbound to the WSL VM. By...

Hyper-V Firewall must allow inbound to the WSL VM. By default the WSL
VM Creator GUID {40E0AC32-46A5-438A-A0B2-2B479E8F2E90} is
NotConfigured, which inherits a deny-all-inbound policy and silently
drops every Windows-host -> WSL service request -- even when WSL2
native localhostForwarding, the in-distro firewalld, AND the netsh
portproxy are all open. Operator-confirmed with this
setting NotConfigured, every browser hit on http://localhost:PORT/
returned 000 across the entire MiOS stack. Setting it to Allow +
Enabled is what unblocks the inbound path.

<!-- mios-src:25b081428e8d from Get-MiOS.ps1:6487-6495 -->

### WSL/VirtualMachinePlatform were just enabled and need a...

WSL/VirtualMachinePlatform were just enabled and need a reboot. Rather
than making the operator re-paste the one-liner (the factory-fresh
friction point), arm a run-once ELEVATED scheduled task that re-runs
the one-liner AUTOMATICALLY at the next logon, then halt cleanly so the
WSL/podman/build steps don't cascade-fail on a not-yet-rebooted host.

<!-- mios-src:7e991cdd7416 from Get-MiOS.ps1:6521-6525 -->

### Strict install order. Each step gates the next: 1. WT...

Strict install order. Each step gates the next:
  1. WT Preview install + AppX-ready wait. Until this completes
     LocalState\settings.json doesn't exist and the patcher
     silently no-ops -- which is exactly what the operator
     caught us doing in earlier revisions.
  2. settings.json patch IMMEDIATELY after install, while the
     LocalState dir is freshly materialized. This is what makes
     MiOS the default theme on the very first WT launch.
  3. Geist Mono NF font install. Settings.json already references
     this face name; if the font isn't on disk yet WT will
     silently fall back to Cascadia, but the ANSI scheme + acrylic
     still apply -- so font order doesn't break anything else.
  4. PowerShell profile (oh-my-posh init line). Lowest priority;
     cosmetic, only matters once the operator hits a prompt.
Apply the MiOS palette + transparency settings to the Windows OS
registry so the OPERATOR'S WHOLE DESKTOP is MiOS-themed -- not
just the WT window. EnableTransparency is the precondition for
acrylic to render at all (Server / freshly-imaged Windows ships
with it OFF, which is why "no acrylic, nothing" was happening).
Dark mode + ColorPrevalence + DWM accent paint MiOS's operator-
blue (#1A407F) onto title bars, taskbar, and Start chrome too.

MiOS canonical accent (mios.toml [colors].accent): #1A407F.
DWM stores AccentColor in 0xAABBGGRR layout (alpha + reverse-byte
BGR), so #1A407F encodes as 0xFF7F401A.

<!-- mios-src:d86c0f947151 from Get-MiOS.ps1:6554-6578 -->

### Use reg.exe directly. Both Set-ItemProperty -Type DWord AND...

Use reg.exe directly. Both Set-ItemProperty -Type DWord AND
.NET Microsoft.Win32.RegistryKey.SetValue('DWord') reject
0xFF7F401A in PS 7 / .NET 8 because their validators want
UInt32 inputs but PS represents the value as Int64
4286529562, which overflows when downcast to Int32 (->
-8437734) and then fails UInt32's range check. reg.exe
accepts hex literals natively for REG_DWORD and writes the
raw 32-bit pattern -- DWM reads back the unsigned 0xFF7F401A.

<!-- mios-src:6e954bd5820d from Get-MiOS.ps1:6593-6600 -->

### SSOT

SSOT: Step 1/7..7/7 banners resolve through mios.toml [messages.steps].
"applications and icons should be installed AFTER
everything--at the end!!!! LAST STEPS". Step 8 (Install-MiOSNativeApp)
was relocated to the very end of Get-MiOS.ps1, AFTER bootstrap.ps1 +
build-mios.ps1's full phase loop succeeds. If the dev VM build fails
part-way, the failure-trap reap fires and NO shortcuts are ever
created -- operator never sees broken icons pointing at a half-built
dev VM. Steps 1-7 below stage the Windows-side basics ONLY.

<!-- mios-src:a5fd32edefe2 from Get-MiOS.ps1:6615-6622 -->

### Bibata cursor rides alongside the font install -- both are...

Bibata cursor rides alongside the font install -- both are
operator-visible "global desktop chrome" touches that don't fit
neatly into a separate numbered step.
"cursor is still not bibata GLOBALLY".

<!-- mios-src:21bbbb34e8b9 from Get-MiOS.ps1:6645-6648 -->

### Start Menu shortcuts for every Linux .desktop entry in the...

Start Menu shortcuts for every Linux .desktop entry in the dev
VM (flatpak apps + native rpm apps + MiOS service launchers).
Uses Microsoft WSL's native shortcut pattern (wslg.exe target,
no console flash, .ico icons in %LOCALAPPDATA%\Temp\WSLDVCPlugin\
<distro>\) so apps appear in Windows search / Start with their
proper icons. Operator-flagged "opening WSL apps in
windows is NOT native WSL behaviour ... icons should be visible
for each application NATIVELY".

<!-- mios-src:db0993389aae from Get-MiOS.ps1:6650-6657 -->

### NOTE

NOTE: Install-MiOSNativeApp (canonical 4-shortcut creation) used to
run here as Step 8/8. Moved to the end-of-script "FINAL STEP"
block (post-bootstrap.ps1 success) per operator directive.

<!-- mios-src:89aef87392b3 from Get-MiOS.ps1:6673-6675 -->

### Refresh $env:PATH from registry BEFORE dot-sourcing the...

Refresh $env:PATH from registry BEFORE dot-sourcing the profile.
winget just installed oh-my-posh / fastfetch / etc. and updated the
USER + MACHINE PATH, but the current pwsh session inherited the
PATH from the launching (non-admin) pwsh -- it does NOT see those
newly installed binaries. Without this refresh the profile body's
`oh-my-posh init pwsh | iex` silently no-ops and the prompt stays
vanilla; Show-MiosDashboard's `Get-Command fastfetch` returns null
and the dashboard never renders.

<!-- mios-src:98053fa1cb89 from Get-MiOS.ps1:6677-6684 -->

### Reload the user profile in the CURRENT irm|iex pwsh session...

Reload the user profile in the CURRENT irm|iex pwsh session so
the regex-patch + PSReadLine reload + MiOS prompt take effect
immediately, without the operator having to close + re-open
pwsh. The redirector was just written -- dot-source it now.

<!-- mios-src:7d355ae35cdb from Get-MiOS.ps1:6696-6699 -->

### Steps 1-7 done -- WT, fonts, oh-my-posh, fastfetch, native...

Steps 1-7 done -- WT, fonts, oh-my-posh, fastfetch, native app
all live under the OPERATOR's user profile (HKCU, OneDrive,
%LOCALAPPDATA%, per-user Start Menu). Bootstrap below
(Initialize-DataDisk + bootstrap.ps1) needs ADMIN to shrink C:\
and machine-scope-winget-install Podman Desktop. UAC-spawn an
elevated pwsh that re-fetches Get-MiOS.ps1 with
MIOS_GETMIOS_RELAUNCHED=1, which causes the inner call to
SKIP this Pass-1 block entirely (no font reinstall) and
fall through to the Pass-2 path (lines below this if-block --
M:\ provisioning + bootstrap.ps1 hand-off).

<!-- mios-src:8ec18d2c5169 from Get-MiOS.ps1:6709-6718 -->

### Pass-2 inner script

Pass-2 inner script: first action is to size the console to 80x30
and center it on the primary monitor, BEFORE any output runs (so the
operator never sees a default 120x30 window briefly before resize).
`[Console]::SetWindowSize` covers conhost; the Win32 SetWindowPos
call covers conhost AND WT's pseudo-console (WT honors the absolute
client-area sizing on its parent HWND).

<!-- mios-src:36fa0fb0f50d from Get-MiOS.ps1:6740-6745 -->

### NB: -NoProfile is INTENTIONALLY OMITTED. Per operator...

NB: -NoProfile is INTENTIONALLY OMITTED. Per operator
("launch with the same themes and settings as Global MiOS
Dashboards with oh my posh piping--etc--everything!!"), the
Pass-2 elevated window must load the MiOS PowerShell profile
body (M:\MiOS\powershell\profile.ps1) so it gets:
  * the resize+center preamble (every MiOS pwsh dashboard sized)
  * Show-MiosDashboard (framed banner + fastfetch info)
  * oh-my-posh init with the MiOS theme
  * mios-* command shims (mios-build, mios-pull, etc.)
The once-per-session guard ($Global:MiosProfileLoaded) keeps
the profile from rendering twice when WT also fires it.

<!-- mios-src:ca3a10cec336 from Get-MiOS.ps1:6808-6818 -->

### NB: previous attempt to launch via `wt.exe new-window...

NB: previous attempt to launch via `wt.exe new-window
--profile MiOS pwsh ...` with `-Verb RunAs` returned
0x80070002 ERROR_FILE_NOT_FOUND on Windows 11 -- appx-packaged
WT + UAC + complex argv combine badly under ShellExecuteEx.
Fall back to bare pwsh elevation. The user's default terminal
host (conhost or WT) decides where the elevated process
lands. Either way, the MiOS PS profile body still loads
in-process via $PROFILE.CurrentUserAllHosts redirector, so
oh-my-posh + Show-MiosDashboard render automatically -- the
operator gets the MiOS terminal experience regardless of
which host paints the chrome.
If WT is the operator's default-terminal-host (Windows 11
22H2+ default), the elevated pwsh lands in WT with the
operator's default profile (PowerShell). To get the MiOS WT
profile inside an already-elevated pwsh, the operator can
run `wt -p MiOS` from that elevated session -- no second UAC.

<!-- mios-src:90f83e93b6f2 from Get-MiOS.ps1:6821-6836 -->

### 2. Resize host window to 80x30 -- the canonical TTY0 /...

2. Resize host window to 80x30 -- the canonical TTY0 / text-mode-3+
dimension and the MiOS dashboard's global size. 80 cols × 30 rows
yields a 4:3 pixel aspect with standard 1:2 monospace cells, fits
the dashboard frame's 80-col strict-clamp, and matches the post-
install hub menu's row budget. wt.exe --size 80,30 already requested
this for the WT window; this RawUI set is the conhost-fallback path
AND a belt-and-braces resize in case WT honored --pos but ignored
--size on an older build.

<!-- mios-src:1715886c6bf3 from Get-MiOS.ps1:6852-6859 -->

### 3. Helpers (Write-Info / Write-Good / Write-Err /...

3. Helpers (Write-Info / Write-Good / Write-Err / Require-Cmd /
Ensure-PodmanDesktop) and the M:\ provisioning functions
(Initialize-DataDisk / Set-PodmanMachineStorageOnM /
Set-WingetStorageOnM) are defined ABOVE Pass-1 now (so Step 0 can
create M:\ before Pass-1 stages files). Their original definitions
moved up; this section header retained for orientation.

<!-- mios-src:f4b2747b9f1d from Get-MiOS.ps1:6869-6874 -->

### 4. Prerequisites Podman Desktop is no longer a "Require-Cmd...

4. Prerequisites

Podman Desktop is no longer a "Require-Cmd or die" gate -- mios.bat
self-elevates so we have admin here, which means winget can install
RedHat.Podman-Desktop unattended without bouncing the operator out
to a browser. Latest stable (per memory: target latest) -- no
version pin, winget picks whatever the manifest currently advertises.

<!-- mios-src:9a85dbd5877e from Get-MiOS.ps1:6880-6886 -->

### Junction every candidate podman-machine storage path onto...

Junction every candidate podman-machine storage path onto M:\ so the
eventual `podman machine init` lands the WSL distro VHDX (multi-GB) on
the dedicated 256 GB partition rather than on C:\. Per
feedback_mios_dev_on_m_drive.md, this MUST happen before any podman
command runs -- if podman creates files at the source path first, the
junction can't be applied to a non-empty dir without a move-then-junction
dance.

Podman v4.x and v5.x use different default storage paths on Windows
depending on machine provider, user vs. system scope, and version
upgrades that didn't migrate the data. We junction ALL candidates so
whichever one the installed podman picks resolves to M:\.
Junction every winget package storage path onto M:\ so winget-installed
CLIs (oh-my-posh, fastfetch, fd, ripgrep, jq, btop4win, etc.) land on
the dedicated MIOS-DEV partition rather than scattering across
%LOCALAPPDATA% and %PROGRAMFILES%. Per operator: "winget should be
installing EVERYTHING to the M:\ partition for ease of uninstallations".

Carve-outs (NOT relocatable):
  - Windows Terminal (appx-packaged UWP, lives in WindowsApps)
  - Podman Desktop (machine-scope MSI, lives in Program Files)
These two stay where Microsoft / RedHat installed them; everything
else (per-user winget package cache + per-user manifest cache + the
winget portable-app stash) gets symlinked to M:\winget\*.

Same symlink-not-junction discipline as podman storage paths above:
mklink /D, not /J. winget's link resolver follows symlinks; some
uninstallers fail on junction targets.

Runs BEFORE any winget install so the very first install's package
directory creation lands on M:\ from the start. If we redirect
AFTER winget has already created the dirs, we'd need to move the
contents over -- doable but racy. Idempotent: re-runs are no-ops if
the symlinks already point at M:\.
NOTE: Phase 0 above (Invoke-MiOSFullReap, called BEFORE Initialize-
DataDisk on every irm|iex run) has already nuked every prior MiOS
artifact on this machine: WSL distros, podman machines, Hyper-V VMs,
install dirs (%PROGRAMDATA%\MiOS / %LOCALAPPDATA%\MiOS / %APPDATA%\MiOS),
M:\ contents, WT MiOS scheme + profiles, Start Menu folder + Desktop
.lnks, HKCU uninstall reg key, AppUserModelID regs, podman-machine
state symlinks, MIOS_* env vars, fonts, PATH entries, MiOS Firewall
rules.

C:\MiOS + C:\mios-bootstrap are NEVER touched: both are operator-
owned dev working trees of mios.git / mios-bootstrap.git (per the
feedback_mios_no_c_drive_fallback memory). End consumers never have
these dirs; reaping them only ever destroys operator dev work.
Operator-flagged after C:\MiOS got nuked.

Per feedback_mios_entry_full_reset memory +
"every irm|iex must reap ALL prior MiOS state... No partial state;
no carry-over." M:\ is the MiOS-owned 256 GB partition; the reap
clears that + the AppData caches but never the dev-tree C:\ paths.

<!-- mios-src:2735d8eb6029 from Get-MiOS.ps1:6897-6949 -->

### Step 0 above (before Pass-1) ALREADY provisioned M:\ +...

Step 0 above (before Pass-1) ALREADY provisioned M:\ + symlinked
podman-machine + winget package storage onto M:\. Pass-1's winget
tools install + WT install + profile staging all landed on M:\
from the very first write. The Initialize-DataDisk + storage-junction
functions are idempotent, so this comment block stands as a marker
of where the late-bound calls USED to live -- they're no longer needed.

<!-- mios-src:83d094ec251a from Get-MiOS.ps1:6951-6956 -->

### 5. Fresh-clone the mios-bootstrap repo to...

5. Fresh-clone the mios-bootstrap repo to M:\MiOS\repo\mios-bootstrap.

CONTRACT (per feedback_mios_irm_iex_always_temp_clone.md +
feedback_mios_entry_m_drive_clone.md): irm|iex ALWAYS clones a
fresh copy. There is NO update / fetch / pull branch. The clone
target is M:\MiOS\repo\mios-bootstrap (the canonical Windows-entry
working tree), NOT %TEMP% or %USERPROFILE%.

Since the full reset above already wiped M:\MiOS, $RepoDir won't
exist when we get here -- no Remove-Item dance needed. (Operator
overrides with -RepoDir <other-path> still get the safety check.)

<!-- mios-src:a866f97854fd from Get-MiOS.ps1:6964-6974 -->

### If $RepoDir already exists with a .git subdir from a prior...

If $RepoDir already exists with a .git subdir from a prior run, do an
in-place fetch + reset --hard to bring it to origin/main. NEVER delete
operator-side files (per feedback_mios_entry_full_reset.md). If it
exists but isn't a git repo, fail with an actionable message rather
than silently nuking it.

<!-- mios-src:d8385dce8937 from Get-MiOS.ps1:7017-7021 -->

### FINAL STEP

-- FINAL STEP: applications + icons (operator directive) ------------------
"applications and icons should be installed AFTER
everything--at the end!!!! LAST STEPS". Only fires on bootstrap.ps1 +
build-mios.ps1 success ($_bootstrapExit==0). On failure the trap-on-
failure auto-reap above already wiped Windows clean -- no shortcuts
pointing at a half-broken dev VM.

<!-- mios-src:c9f7c21176ca from Get-MiOS.ps1:7117-7122 -->

### Bootstrap stops at DEV-ready...

-- Bootstrap stops at DEV-ready --------------------------------------------
(feedback_mios_dev_vm_is_builder_only.md):
  "we aren't bootc switching podman-MiOS-DEV!!! WE NEED TO FIRST BOOT IN
   TO podman-MiOS-DEV and have it working!!!! 'mios build' command is
   for building OCI images from any MiOS app window"

The dev VM is the BUILDER substrate -- podman-machine-os Fedora 44 with
the MiOS overlay (Quadlets / RPM layer / flatpaks / branding) applied
during Phase 3. It is NOT bootc-switched to localhost/mios:latest; that
would conflate the builder with the deployment target. `mios build` is
the operator-triggered verb that produces OCI + bootc-image-builder
artifacts (vhdx / qcow2 / iso / raw / wsl tarball) for deploying to
OTHER substrates. Output flows outward from the dev VM, never inward.

Earlier commits (a307e4b ... 90aa799) auto-chained `mios build` here on
the assumption that post-bootstrap = bootc-switched dev VM. Operator
corrected: that's wrong. Bootstrap returns at DEV-ready; the staged
MiOS hub shortcut + verb-hint banner above tell the operator what
verbs to type next.

<!-- mios-src:970a8d119634 from Get-MiOS.ps1:7139-7157 -->

### WSLg host-side bridge reset (clears [WARN: COPY MODE])...

-- WSLg host-side bridge reset (clears [WARN: COPY MODE]) ------------------
"STILL no visible windows" -- weston / msrdc
accumulate state during the multi-minute install (mid-install
wsl.exe -- probes, daemon-reloads, container starts) that often
leaves the host-side RDP-RAIL bridge stuck in COPY MODE even after
our /mnt/wslg/runtime-dir chmod fix lands. A fresh `wsl --shutdown`
+ `Restart-Service LxssManager` on the Windows host gives WSLg a
clean slate to negotiate VAIL (shared-memory) mode on first re-entry.

Safe to run unconditionally at the END of irm|iex: bootstrap has
already completed all its work, no in-flight operations to lose.
The next time the operator launches MiOS, WSLg starts fresh.

<!-- mios-src:b8a3c342f35d from Get-MiOS.ps1:7159-7170 -->

### Restart-Service requires admin; the irm|iex caller already...

Restart-Service requires admin; the irm|iex caller already
elevated, so this works. Failure is non-fatal -- shutdown
alone is usually enough.
WSL service name differs by Windows build: 'WslService' on Win11
Store/inbox WSL, 'LxssManager' on legacy Win10. Try both; skip
gracefully if neither exists ('Cannot find any service
with service name LxssManager' on Win11).

<!-- mios-src:ce13c4686408 from Get-MiOS.ps1:7177-7183 -->

### MiOS-Cat handoff

-- MiOS-Cat handoff: offer to flash a bootable MiOS-Cat USB -----------------
The bare `irm|iex` one-liner runs the Default action and (until now) never
routed to MiOS-Cat -- the -Action FlashUSB path is unreachable from a pipe (no
params). Offer it here as a param-less prompt so a factory-fresh install can go
straight from provisioning to building a deploy USB. Skipped under -Unattended
(never surprise-format a drive) or if bootstrap did not succeed.

<!-- mios-src:aee6d4b2bbe2 from Get-MiOS.ps1:7197-7202 -->
