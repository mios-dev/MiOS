<!-- AI-hint: Manual pages distilled from the source comments of mios, sanitized, each passage anchored to the comment it came from. -->

# mios

### Examples for other local OpenAI-API-compatible runtimes...

Examples for other local OpenAI-API-compatible runtimes:
  LLM-Light:          base_url = "http://localhost:11450/v1"
  vLLM:               base_url = "http://localhost:8000/v1"
  LM Studio:          base_url = "http://localhost:1234/v1"
  mios-gateway-agent: base_url = "http://localhost:8642/v1"
  LiteLLM proxy:      base_url = "http://localhost:4000/v1"

<!-- mios-src:7036a2325287 from etc/mios/kb.conf.toml:11-16 -->

### Comment lexer + classifier for the generative documentation...

Comment lexer + classifier for the generative documentation system.

Spec: docs/agy/doc-generative-documentation.md sections 1.2 and 2.

Two jobs, kept apart on purpose:

  lex(path)      -> the comment blocks in a file, with enough context
                    (attachment, anchor code, hashes) to place and track them.
  classify(b, ..) -> exactly one verdict per block, from an ordered first-match
                    rule set, so every decision is explainable by one rule id.

The classifier holds NO thresholds of its own. Every number arrives in a
`Policy` built from mios.toml `[docs]`, because a rule change must be an
operator edit to SSOT rather than a code edit (Law 7 NO-HARDCODE, Law 8
SSOT-PROJECTION).

Taggability and comment syntax are NOT redefined here. They are loaded from
usr/libexec/mios/mios-ai-tag through the same SourceFileLoader shim
mios-ai-hint-coverage uses, so "which files carry documentation" has exactly one
definition across all consumers.

<!-- mios-src:f6c3310f2a36 from usr/lib/mios/mios_comments.py:5-25 -->

### The files the census covers

The files the census covers: GIT-TRACKED only, sorted.

    Walking the filesystem instead made the count depend on whatever untracked
    or ignored files a particular machine happened to have -- vendored trees,
    scratch dirs, staging dumps. The number then differed between a contributor
    box and CI, which silently loosened the ratchet ceiling in CI to the point
    that its negative test could not breach it. Tracked files are the same set
    everywhere.

<!-- mios-src:4f4415e5d651 from usr/lib/mios/mios_comments.py:49-57 -->

### Import usr/libexec/mios/mios-ai-tag (no .py suffix) as a...

Import usr/libexec/mios/mios-ai-tag (no .py suffix) as a module.

    Same SourceFileLoader approach mios-ai-hint-coverage already uses. Returns
    None when it cannot be found, so callers can degrade rather than crash.

<!-- mios-src:28a9e30776f6 from usr/lib/mios/mios_comments.py:85-89 -->

### Every name a comment could legitimately reference. A...

Every name a comment could legitimately reference.

    A reference counts as dangling only when it is absent from here AND absent
    from the tree AND not allowlisted. Without this filter the staleness rule
    drowns in false positives -- the survey needed it to get from 353 raw hits
    down to ~70 real ones.

<!-- mios-src:6fc7fcbe217c from usr/lib/mios/mios_comments.py:212-218 -->

### Python uses tokenize + ast, never regex. Regex miscounts...

Python uses tokenize + ast, never regex.

    Regex miscounts multi-line data strings as prose -- the survey proved it on
    the AI-plane files, where a system-prompt literal reads exactly like a
    narrative comment block.

<!-- mios-src:1fe018524038 from usr/lib/mios/mios_comments.py:331-336 -->

### R4 BANNER DELIBERATE NARROWING of the spec's second clause....

R4 BANNER

DELIBERATE NARROWING of the spec's second clause. As written it is
"<= 8 words AND no sentence-final punctuation AND not WHY -> DROP", which
also swallows ordinary short comments ("bump the retry count",
"guard against zero") -- and DROP is a class that `prune` may delete.
Information safety is absolute here, so a short block must additionally
LOOK like a label -- ALL-CAPS, Title Case, or a trailing colon -- before it
can be treated as a divider. Pure divider runs are unaffected.

<!-- mios-src:f3e774fcaabb from usr/lib/mios/mios_comments.py:532-540 -->

### (vendor, vendor_d, host, host_d, user, user_d) resolved...

(vendor, vendor_d, host, host_d, user, user_d) resolved from the env at
    CALL time. Vendor FRAGMENTS live in /usr/lib/mios/mios.d (Law 1 USR-OVER-ETC
    + systemd's /usr/lib vendor convention), NOT beside the /usr/share monolith;
    admin/user fragments sit in a mios.d/ beside their monolith.

<!-- mios-src:69fb3387c633 from usr/lib/mios/mios_toml.py:52-55 -->

### The overlay layer paths, lowest precedence first, EXPANDED...

The overlay layer paths, lowest precedence first, EXPANDED to include
    drop-in fragments. Resolved from the environment at CALL time (not import
    time) so a caller / test / CI on a non-FHS host can retarget a layer via
    MIOS_VENDOR_TOML / MIOS_HOST_TOML / MIOS_USER_TOML / MIOS_TOML_ROOT (and the
    *_TOML_D fragment-dir overrides) AFTER this module is imported.

    Ordering is TIER-MAJOR (vendor < host < user); within each tier the monolith
    seeds LOWEST, then that tier's mios.d/*.toml fragments (lexical basename)
    deep-merge over it. Tier is the primary precedence key -- a vendor fragment
    can NEVER outrank a higher tier (the XDG/git-config scope model, not
    systemd's global flat sort). NO-OP when no mios.d/ exists: every _frags()
    glob is empty and this returns exactly [vendor, host, user] as before.

<!-- mios-src:982133a0fda5 from usr/lib/mios/mios_toml.py:69-80 -->

### Allocate every [ports] value from the [ports.categories]...

Allocate every [ports] value from the [ports.categories] schema, IN PLACE.

    This runs AFTER layer merging, so it is the live runtime allocator: a
    factory/OEM default in the vendor mios.toml, an operator override in
    /etc/mios/mios.toml, or a user override in ~/.config/mios/mios.toml all feed
    the same derivation and the result is what every consumer sees -- userenv.sh
    exports, /etc/mios/install.env, the Quadlet render, the firewall phases and
    the Containerfile build args.

    A member's port is  base + index_in_members * stride.  Because `members` is
    ordered, adding or removing a service reallocates the category with no hand
    edit and no chance of a collision. `pinned` entries are protocol contracts
    (DNS/53) and are emitted verbatim.

    The flat [ports] table in the vendor file is a rendered projection kept for
    readability and drift-gating; the derivation OVERRIDES it, so an operator who
    retargets a category base is never silently beaten by a stale vendor literal.

<!-- mios-src:d55cbc3df935 from usr/lib/mios/mios_toml.py:136-153 -->

### Allocate ports from [ports.categories] AFTER every layer...

Allocate ports from [ports.categories] AFTER every layer (and the DB
overlay) has merged, so operator/user overrides of a category base or
member list re-derive live instead of losing to the vendor flat table.

<!-- mios-src:4179b26ee527 from usr/lib/mios/mios_toml.py:209-211 -->

### Fixtures for mios_comments. Every classifier rule gets at...

Fixtures for mios_comments.

Every classifier rule gets at least one fixture that asserts the exact
(cls, reason) pair. A rule with no fixture is a rule nobody has proven fires --
this repo has a documented history of checks that could not fail, so the bar
here is that each rule is demonstrated, not merely written.

Runs standalone (python3 test_mios_comments.py) so it needs no pytest in the
bake image.

<!-- mios-src:54f42dee754a from usr/lib/mios/test_mios_comments.py:5-14 -->

### Folder default = "MiOS" -- NOT the distro name. Earlier...

Folder default = "MiOS" -- NOT the distro name. Earlier versions
wrote to %APPDATA%\...\Programs\<distro>\ to match Microsoft's
native WSL2 Start Menu sync, but Microsoft's wslservice TREATS
that folder AS ITS OWN: every WSL distro restart it re-enumerates
apps from the distro side using a much more restrictive filter
(NoDisplay + Terminal filtering plus its own ad-hoc rules), then
DELETES every .lnk in the folder that doesn't match. Result:
operator goes from 46 properly-iconed apps to 3 after `wsl
-shutdown`. Operator-flagged "no apps on windows
again!!!" -- the second time the WSL stomp wiped the shortcuts.

Writing to a distinct folder lets MS manage its 3-app distro
folder and lets MiOS own its 46-app folder side-by-side. They
appear next to each other in Start Menu.

<!-- mios-src:614c5fa292af from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:37-50 -->

### Unknown -- still copy; .lnk IconLocation tolerates PNG even...

Unknown -- still copy; .lnk IconLocation tolerates PNG even
at non-canonical extension. .NET's PNG->ICO converter
below will reject if truly garbage; we degrade gracefully.

<!-- mios-src:fd095c7a4419 from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:187-189 -->

### PNG -> ICO converter that EMBEDS the PNG bytes inside an...

PNG -> ICO converter that EMBEDS the PNG bytes inside an ICO
container. This is the Vista+ "PNG-encoded ICO" format Windows
Start Menu renders cleanly at every size from 16x16 to 256x256.

Why NOT .NET's Icon.Save() / Bitmap.GetHicon: those produce
single-image .ico files in 32-bit BMP format with a 32x32 source,
which Windows upscales badly at 256x256. The resulting Start Menu
tile shows either a generic icon or a blurry mess. Operator-flagged
twice: "no icons match", "NEVER saw native icons -- NOT
even ONCE". A PNG-embedded ICO matches what flatpak / Microsoft
Store / WSL's own sync produce.

Format (Vista+ PNG ICO):
  ICONDIR     (6 bytes): 00 00 | 01 00 | 01 00
  ICONDIRENTRY (16 bytes per image):
    bWidth(1)   bHeight(1)  bColorCount(1)  bReserved(1)
    wPlanes(2)  wBitCount(2)  dwBytesInRes(4)  dwImageOffset(4)
  Image data: raw PNG bytes (NOT XOR/AND masks like classic ICO)

<!-- mios-src:ddea11fea6f3 from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:224-241 -->

### Force the Shell to re-read .lnk IconLocation values WITHOUT...

Force the Shell to re-read .lnk IconLocation values WITHOUT
nuking the icon cache database -- previous version called
`ie4uinit.exe -ClearIconCache` which dropped every Start Menu
icon to blank until Explorer was manually restarted. Operator-
flagged "the icons disappeared now!!!".

Lighter approach: touch every .lnk mtime + the SHChangeNotify
broadcast. The Shell watches .lnk mtimes for change; touching
invalidates the per-shortcut icon cache entry without affecting
other Start Menu items.

<!-- mios-src:957c6391295e from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:288-297 -->

### Sweep ALL .lnk files in our managed folder so renamed /...

Sweep ALL .lnk files in our managed folder so renamed / removed apps
don't leave orphan shortcuts. Also clear the legacy `<distro>` folder
(where shortcuts USED to land before Microsoft's wslservice started
stomping it on every distro restart) -- if it still has our
leftover .lnks, they'll appear in Start Menu as duplicates next to
the new MiOS Apps folder.

<!-- mios-src:3de75bb63b2a from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:314-319 -->

### NATIVE WSL filename pattern

NATIVE WSL filename pattern: "<App Display Name> (<distro>).lnk".
Matches the exact convention WSL's built-in sync uses, so the
operator sees one consistent set of shortcuts (ours + WSL's
native sync share the same filenames -> de-dup at write).

<!-- mios-src:bde7cfdb0d72 from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:368-371 -->

### NATIVE Microsoft WSL pattern (reverse-engineered from a...

NATIVE Microsoft WSL pattern (reverse-engineered from a WSL-
generated shortcut on Win11 26H1):
  TargetPath       = C:\Program Files\WSL\wslg.exe  (GUI, no console)
  Arguments        = -d <distro> --cd "~" -- <exec line>
  WorkingDirectory = C:\WINDOWS\system32
  WindowStyle      = 7   (Minimized -- no flash; wslg handles UI)
  IconLocation     = <path-to-ico>,0

<!-- mios-src:82739bd24264 from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:376-382 -->

### ─── "MiOS Full Desktop" Enhanced Session shortcut...

─── "MiOS Full Desktop" Enhanced Session shortcut ───────────────────
Alternate launch path that opens the full GNOME desktop via mstsc.exe
connecting to the xrdp service in the dev VM. Set up by automation/
35-xrdp-enhanced-session.sh at install time. Lives alongside the
per-window app shortcuts in the same MiOS Apps folder so the operator
can pick per session (per-window for native-Windows-window feel,
Full Desktop for libadwaita-uniform rendering + Bibata cursor).
Operator directive "Full Enhanced Session is an alternate
launch option installed at irm|iex invoke and installation".

<!-- mios-src:ef9ce2ef6f33 from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:395-403 -->

### Nested GNOME approach

Nested GNOME approach: WSLg launches /usr/bin/mios-full-desktop in
the distro, which exec's gnome-session inside `gnome-shell --nested`.
Mutter runs as a Wayland CLIENT of WSLg's Weston, hosting the entire
GNOME desktop in one window. All cursor + theme + decoration rendering
happens INSIDE that nested compositor -- bypasses every WSLg-per-window
rendering limit at once (Bibata + rounded corners + libadwaita-uniform
everything just work because Mutter draws final pixels itself).

<!-- mios-src:9a6c3ef60a2c from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:419-425 -->

### mios_tools -- the in-sandbox Code Mode tool API (WS-2)....

mios_tools -- the in-sandbox Code Mode tool API (WS-2).

This module is the LOCAL Python API the model's generated code imports INSIDE the
coderun-sandbox. It is the whole point of Code Mode: instead of loading ~71
OpenAI function schemas into the model's context every turn, the model writes
ordinary Python that calls e.g.

    import mios_tools
    hits = mios_tools.web_search("local FOSS LLM serving 2026")
    print(mios_tools.json({"top": hits[:3]}))      # final line = filtered result

and only the FILTERED result returns to the model -- the big token win.

How a tool call leaves the jail
-------------------------------
The sandbox is Network=none + DropCapability=ALL, so the ONLY egress is the unix
socket the Quadlet already bind-mounts at /run/coderun.sock (see
mios-coderun-sandbox@.container). This shim sends a single newline-delimited JSON
request -- {"verb": "<name>", "args": {...}} -- over that socket and reads one
JSON response line back. The HOST side (the agent-pipe's Code Mode broker proxy)
listens on that socket, runs the verb through dispatch_mios_verb (so the broker's
permission / taint-firewall / dedup / HITL gates STILL apply per verb), and
writes the result back. There is NO direct verb execution inside the jail --
every call is mediated + policy-checked on the host.

Deploy: this file is mounted into the sandbox (read-only) as
/usr/local/lib/mios/mios_tools.py and put on PYTHONPATH so `import mios_tools`
resolves. Pure stdlib (socket + json) so it has no in-sandbox deps.

<!-- mios-src:c6e5226f446e from usr/libexec/mios/mios-codemode-api.py:4-32 -->

### Named window-snap region geometry (pure, no side effects)....

Named window-snap region geometry (pure, no side effects).

The rectangle math is intentionally free of hardcoded pixel constants: half /
quarter fills are computed from the LIVE work-area width and height, and the
right/bottom halves take the exact remainder so a pair of halves tiles the work
area with no gap or overlap on odd dimensions.

<!-- mios-src:b4e108c80621 from usr/libexec/mios/mios_window_region.py:5-11 -->

### Compute the ABSOLUTE (x, y, w, h) for ``region`` from a...

Compute the ABSOLUTE (x, y, w, h) for ``region`` from a screen-layout dict.

    ``layout`` matches the OS-control executor's /screen-layout contract:
    ``{"screens": [{"work": {"x", "y", "width", "height"}}, ...]}``. The chosen
    monitor's work-area origin is added to the relative rectangle. Returns None
    on an unknown region or an out-of-range / malformed monitor entry.

<!-- mios-src:476acf14a8a6 from usr/libexec/mios/mios_window_region.py:64-70 -->

### Standalone unit test for mios-docgen (WS-4 P0 doc-gen)....

Standalone unit test for mios-docgen (WS-4 P0 doc-gen).

Pure stdlib; imports the CLI module by path (it has no .py extension, matching
the libexec convention) and exercises the DB/binary-free logic: format
resolution, the master gate, degrade-open emission, and the routing decision
table. The two backend converters (Pandoc / LibreOffice) are NOT invoked --
that needs the binaries + a graphical-free office runtime and is covered by the
operator's live check; here we prove the pure decision layer.

Mirrors the test_mios_sched.py / test_mios_evict.py pattern: explicit asserts,
PASS/FAIL summary, non-zero exit on any failure.

Run:  python test_mios_docgen.py

<!-- mios-src:891a56504503 from usr/libexec/mios/test_mios_docgen.py:4-17 -->

### Tests for the mios-find ranker SSOT (mios.toml...

Tests for the mios-find ranker SSOT (mios.toml [mios-find.ranker] +
[mios-find.category_priority]).

The ranker lives in an embedded python heredoc inside the bash script
``mios-find``. We extract that block, stub the ``mios-apps --json`` inventory
call, point ``MIOS_TOML`` at a temp config, exec it in-process, and assert the
chosen launch command. Defaults must reproduce the historical in-code ranking;
a non-default config must change it -- proving the weights are read from SSOT,
not baked.

<!-- mios-src:9a3a61c4416a from usr/libexec/mios/test_mios_find_ranker.py:4-13 -->

### Quadlet sidecar enablement. Defaults policy (project-wide...

Quadlet sidecar enablement.

Defaults policy (project-wide invariant): every flag here defaults to
true. The system never disables a service via static config -- when a
service is incompatible with the host (wrong virtualization layer,
missing required path, missing hardware), systemd `Condition*`
directives in the Quadlet itself short-circuit it at boot/pre-boot
and the service silently no-ops. Operators can still override any
flag in /etc/mios/profile.toml or ~/.config/mios/profile.toml to
force-disable a service even when it would otherwise run.

<!-- mios-src:81a26ecb9a9f from usr/share/mios/profile.toml:81-90 -->

### FORCE-DISABLED (explicit exception to the defaults-true...

FORCE-DISABLED (explicit exception to the defaults-true policy):
this sidecar's docker_start.sh corrupts the SHARED host /var/lib/crowdsec
(dangling /staging symlinks + `localhost` machine re-register) and needs the
online hub at boot (incompatible with offline MiOS) -- it crash-looped the
host crowdsec agent for ~6 days. Retired; the host agent provides the IPS.
Full rationale in mios.toml [quadlets.enable] + memory mios_crowdsec_recovery.

<!-- mios-src:31fd4e869038 from usr/share/mios/profile.toml:98-103 -->
