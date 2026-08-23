<!-- AI-hint: Manual pages distilled from the source comments of tools, sanitized, each passage anchored to the comment it came from. -->

# tools

### tools/audit-version-literals.py -- Audit & inventory...

tools/audit-version-literals.py -- Audit & inventory version tokens across MiOS repo.
Classifies version literals as:
  (a) SSOT-definition
  (b) SSOT-derived/placeholder
  (c) HARDCODED-literal

Emits usr/share/mios/reference/version-literals-audit.tsv

<!-- mios-src:61f303f40e6f from tools/audit-version-literals.py:5-13 -->

### Strip INHERITED MIOS_* before running the bash twin. The...

Strip INHERITED MIOS_* before running the bash twin. The comparison asks
"what does userenv.sh resolve from SSOT?", but bash reports every MIOS_*
in its environment -- so any ambient var the TOML side has no key for
shows up as a mismatch. CI sets MIOS_DRIFT_REQUIRE_TOOLS=1 as a workflow
knob, which failed the check with:
  Var MIOS_DRIFT_REQUIRE_TOOLS: Toml resolved '', Bash resolved '1'
Keep only the tier pointers the resolver needs to find the SSOT layers.

<!-- mios-src:568191b44c9c from tools/check-resolver-twin.py:40-46 -->

### Repo-relative paths git tracks, or None when git is...

Repo-relative paths git tracks, or None when git is unavailable.

    The manifests embed a walk of the tree. Walking the FILESYSTEM makes the
    output a function of the developer's working directory -- local scratch
    files, .bak files and untracked notes all land in root-manifest.json -- so
    a manifest generated on a dev box can never match one regenerated on a
    clean CI checkout, and check_ai_manifests_fresh fails forever. Restricting
    the walk to tracked files makes the artifact reproducible anywhere.

<!-- mios-src:28caf1dca73d from tools/generate-ai-manifest.py:33-41 -->

### Generate the MiOS agent egress firewall (#54). Zero-trust...

Generate the MiOS agent egress firewall (#54).

Zero-trust federation calls for an OUTBOUND firewall: a compromised or misled
agent must not be able to exfiltrate to arbitrary internet hosts. The correct
layer for that is the OS (nftables), scoped to the agent's uid -- an app-level
hook would be incomplete (httpx clients are constructed ad-hoc throughout the
orchestrator). This emits that ruleset from SSOT; the operator applies it.

It is uid-scoped, so it does not disturb other users: `web_search` keeps working
because the agent reaches searxng over loopback, and searxng (a different uid)
reaches the internet.

<!-- mios-src:15b902cf01e4 from tools/generate-egress-firewall.py:5-16 -->

### This used to rmtree repo_root/usr/share/doc/mios/manual...

This used to rmtree repo_root/usr/share/doc/mios/manual unconditionally,
derived from repo_root and ignoring --output entirely: pointing --output at
a scratch file still deleted the in-repo directory. That directory is where
AUTHORED manual prose is meant to live, so the tool could destroy
hand-written content that no generator can reproduce. Clean only a stale
split-page directory that sits beside the file we are actually writing, and
never one holding git-tracked files.

<!-- mios-src:448a427d36d9 from tools/generate-manual.py:28-34 -->

### tools/generate-pipeline-index.py Generates...

tools/generate-pipeline-index.py
Generates usr/share/mios/reference/pipeline-index.tsv from automation/[0-9][0-9]-*.sh scripts.
Enforces 1:1 mapping for stage identity coordinates (ADR-0012, WS-NUMBER AGY-644).

<!-- mios-src:f43995ec2b39 from tools/generate-pipeline-index.py:2-6 -->

### Generate MiOS .pod Quadlets from the [pods.*] SSOT (WS-7)....

Generate MiOS .pod Quadlets from the [pods.*] SSOT (WS-7).

A co-resident group -- a set of containers that must share a podman pod (one
network namespace + lifecycle) -- was previously a hand-authored .pod Quadlet
(only mios-webtools). That is drift-prone: the pod's [Unit]/[Pod]/[Install] and
its member list lived only in the file. This projects each [pods.<name>] in
mios.toml to a deterministic <name>.pod under usr/share/containers/systemd/, so:

  * the co-resident group is declared ONCE (SSOT), and
  * tools/generate-k3s-manifests.sh -- which reads the LIVE pods -- projects the
    same workloads to k3s, so the cluster path is one faithful bridge from SSOT.

Each member .container still declares `Pod=<name>.pod` (Quadlet wires the
Wants/After on the pod service); the member list here is the documented SSOT +
fuels a drift check that every declared member exists as a .container.

Pure renderer (render_pod_quadlet) so it unit-tests offline (--selftest), in the
sibling style of the other tools/ generators. Same SSOT -> byte-identical output.

<!-- mios-src:11f8e1c5b95e from tools/generate-pod-quadlets.py:5-23 -->

### [image.sidecars] -- the digest-pinned image SSOT. Consulted...

[image.sidecars] -- the digest-pinned image SSOT. Consulted by
    _sidecar_image() so bare (no-userenv) regeneration renders the committed
    @sha256 instead of the digestless inline fallback (Quadlet digest drift).

<!-- mios-src:a9bc76e9406e from tools/generate-pod-quadlets.py:212-214 -->

### Provision the MiOS agent mTLS keypair + CA (#54)....

Provision the MiOS agent mTLS keypair + CA (#54).

Zero-trust federation needs peers to mutually authenticate. The ed25519 *message*
principal (#60) signs delegations; mTLS authenticates the *transport*. This mints
the PKI for that: a self-signed local CA + an agent leaf certificate (clientAuth +
serverAuth) signed by it. Peers trust each other by exchanging CA certs.

Trust model: self-signed local CA per node is the standard self-hosted default
(point [security.mtls] at an existing org CA to override). The enforcing half --
making the A2A endpoint REQUIRE client certs -- is reverse-proxy deployment
(MiOS terminates TLS at the proxy), documented in security/README.md; this tool
only provisions the credentials.

Idempotent: an existing CA is reused (so peer trust survives re-runs); the agent
leaf is re-issued. Requires `cryptography`. Run where the certs should live.

<!-- mios-src:1655be81ab25 from tools/provision-agent-mtls.py:5-20 -->

### render-globals.py -- generate BOTH globals resolvers from...

render-globals.py -- generate BOTH globals resolvers from the SSOT.

automation/lib/globals.sh and globals.ps1 used to be two divergent hand-typed
registries (~200 literals each) kept in step with mios.toml only by drift
checks. They are now generated in full, directly, under their original names --
every consumer that sources/dot-sources them is untouched, and there is no
`.generated` sidecar and no shim layer.

Only ONE thing cannot be a constant: the version, which is read from a file at
run time. That logic is emitted as a preamble from this generator, so it still
lives in exactly one place.

Usage:
    tools/render-globals.py           # write both resolvers
    tools/render-globals.py --check   # exit 1 if either has drifted

<!-- mios-src:a14177eaae8b from tools/render-globals.py:5-20 -->

### Assign-if-unset. Prefer the idiomatic `: "${VAR:=value}"`...

Assign-if-unset.

    Prefer the idiomatic `: "${VAR:=value}"` -- several drift checks parse that
    exact shape out of this file. It is unusable when the value contains `}`
    (message templates carry `{placeholder}`), which would close the expansion
    early and make the file a syntax error; those fall back to
    `[ -n "${VAR+x}" ] ||`, which has identical already-set-wins semantics.

<!-- mios-src:e7e3421e3913 from tools/render-globals.py:234-241 -->

### The word in `"${VAR:=word}"` is still quote-processed, so a...

The word in `"${VAR:=word}"` is still quote-processed, so a lone ' or "
inside it (e.g. "the operator's phone") starts an unterminated quote.
Only take the idiomatic form when the value is free of every metacharacter.

<!-- mios-src:ea6d3604444b from tools/render-globals.py:243-245 -->

### render-ports.py -- project [ports.categories] onto the flat...

render-ports.py -- project [ports.categories] onto the flat [ports] table.

The categories table is the numbering SSOT: each category owns a `base`, a
`stride` and an ORDERED `members` list, and a member's port is

    base + index_in_members * stride

`pinned` entries (DNS/53) are protocol contracts and are emitted verbatim.

Usage:
    tools/render-ports.py            # rewrite the flat [ports] table in place
    tools/render-ports.py --check    # exit 1 if the flat table has drifted
    tools/render-ports.py --print    # print the derived name=port map

<!-- mios-src:11affdf550ad from tools/render-ports.py:5-18 -->

### Return {port_name: value} derived from [ports.categories]....

Return {port_name: value} derived from [ports.categories].

    Pinned ports are emitted at their literal value; derived ports are
    base + index*stride. stack_id is applied later by the resolver's
    process_val(), not here, so this stays the pre-offset SSOT.

<!-- mios-src:8f8b661954a5 from tools/render-ports.py:40-45 -->

### `${MIOS_PORT_X:-1234}` literals are degrade-open defaults...

`${MIOS_PORT_X:-1234}` literals are degrade-open defaults, but a
    hand-typed one silently goes stale the moment a category base moves. Treat
    them as GENERATED: rewrite every one to its SSOT value.

<!-- mios-src:8d84ef72541b from tools/render-ports.py:192-194 -->

### Resolve the python MiOS itself provisions. Python is a...

Resolve the python MiOS itself provisions.

Python is a DECLARED MiOS dependency, not something to hope for: mios.toml
[apps.winget].pkgs lists "Python.Python.3.14" under "Critical runtime /
toolchain", so every MiOS host has it globally (dnf python3 on Linux, winget
on Windows), and installation/mios-install.ps1 + Reinstall-MiOSDEV.ps1 already
resolve it at %LOCALAPPDATA%\Programs\Python\Python314\python.exe.

The trap: `command -v python` SUCCEEDS on Windows even when it resolves to the
Microsoft Store alias stub, which prints "Python was not found" and exits. The
old probe (`command -v python3 || PY=python`) therefore set PY to the stub, and
every generator below silently did nothing while sync reported success -- the
tree looked synced while the manifests went stale. So probe by EXECUTING, and
try the MiOS-installed interpreter before bare names.

<!-- mios-src:4cf964f45b77 from tools/sync-generated.sh:24-37 -->

### EVERY renderer resolves through the layered resolver, which...

EVERY renderer resolves through the layered resolver, which honours
MIOS_ROOT / MIOS_TOML* from the environment. On a MiOS host (or the MiOS-DEV
container) those are already exported and point at the INSTALLED system, so
an unpinned run silently renders the installed SSOT into this repo's
artefacts -- which is how globals.ps1 ended up carrying 'MiOS User' and
the installed host's `agent_pipe` port. Pin every tier to the tree being synced.

<!-- mios-src:7173c25c3b4b from tools/sync-generated.sh:59-64 -->

### title

title: MiOS Computer Use
author: MiOS
version: 0.1.0
description: |
  ONE Open WebUI Native tool surfacing the MiOS computer-use capability
  (WS-4 P0) as typed tool_calls: the EXISTING desktop control + vision
  grounding verbs (mios-computer-use / mios-pc-control / mios-pc-vision)
  PLUS the new FOSS offline document generation tool (mios-docgen ->
  Pandoc + LibreOffice). The chat model invokes these directly instead of
  indirecting through the generic `terminal:` shell tool.

  This is the LiteCUA Perceptor/Reasoner/Worker pattern assembled from
  MiOS parts (NO Wide-Moat / BSL vendor stack -- see
  concepts/aios-implementation-plan.md section 0-B):
    * Perceive : cu_screenshot  (one-shot capture)
    * Ground   : cu_ground / cu_atspi_query  (AT-SPI first, vision fallback)
    * Act      : cu_click / cu_type / cu_key / cu_key_combo / cu_window_list
    * Produce  : docgen_build / docgen_convert  (author/convert artifacts)

  Dispatch goes through the OPERATOR-side launcher broker (unix socket at
  /run/mios-launcher/launcher.sock), exactly like the sibling mios_verbs
  tool -- so the verbs inherit the operator's WSLg / Wayland session
  (WAYLAND_DISPLAY, DBUS, WSL_INTEROP) that an in-container subprocess
  could never see.

  GATING + SAFETY (binding rule -- default-off / degrade-open):
    * Master valve ENABLED (default True) toggles the whole tool.
    * WRITE_ACTIONS_ENABLED (default FALSE) gates the side-effecting input
      verbs (click/type/key/key_combo). Read-class verbs (screenshot,
      ground, atspi_query, window_list, docgen) work with writes off.
    * mios-docgen itself is independently gated by [computer_use].docgen_enable
      server-side; when off it returns ok=false (this tool surfaces that).
  Every method returns structured JSON the model can reason over, so a
  failure is unambiguous (no "I clicked the button" hallucination over a
  silently-failed call).

requirements:
  pydantic

<!-- mios-src:9cde6af7c1f5 from usr/share/mios/openwebui/tools/mios_computer_use.py:4-43 -->

### Capture the desktop to a PNG (one-shot, read-only)....

Capture the desktop to a PNG (one-shot, read-only). Env-adaptive:
        local Wayland (portal/grim), WSLg via mios-pc-control, or a federated
        remote executor -- the same verb works everywhere.

        :param path: Output PNG path (e.g. /tmp/screen.png). Feed this to
            cu_ground to locate a UI element before clicking.
        :return: JSON {success, stdout, stderr}.

<!-- mios-src:e9d3dc92b109 from usr/share/mios/openwebui/tools/mios_computer_use.py:166-173 -->

### Locate a UI element by natural-language description ->...

Locate a UI element by natural-language description -> click
        coordinates. Read-only. AT-SPI accessibility tree FIRST (deterministic,
        no pixels), local vision model (qwen3-vl / UI-TARS) only as fallback.
        Returns {x, y, confidence}; pass x/y to cu_click.

        :param query: Description of the target (e.g. "the OK button",
            "the search field", "Save toolbar icon").
        :return: JSON {x, y, confidence, reasoning, source}.

<!-- mios-src:9116ea149f9b from usr/share/mios/openwebui/tools/mios_computer_use.py:186-194 -->

### Semantic accessibility-tree lookup (role/name match) ->...

Semantic accessibility-tree lookup (role/name match) -> screen
        coordinates, NO pixels/vision. Read-only. Faster + more reliable than
        cu_ground for standard widgets (buttons, menus, fields).

        :param query: Element role or name substring (e.g. "Cancel", "menu",
            "text").
        :return: JSON {query, matches:[{name, role, x, y, w, h}]}.

<!-- mios-src:1ca2bcdb0f17 from usr/share/mios/openwebui/tools/mios_computer_use.py:202-209 -->

### Click at pixel (x,y) on the desktop. WRITE action -- gated....

Click at pixel (x,y) on the desktop. WRITE action -- gated.
        Usually preceded by cu_ground / cu_atspi_query to find the coords.

        :param x: X pixel offset from top-left.
        :param y: Y pixel offset from top-left.
        :param button: left (default) | right | middle.
        :return: JSON {ok, action, backend} or {success:false,...}.

<!-- mios-src:512d9df90b58 from usr/share/mios/openwebui/tools/mios_computer_use.py:235-242 -->

### Type literal text into the focused surface. WRITE action --...

Type literal text into the focused surface. WRITE action -- gated.
        For editing FILES prefer the text-editor verbs; this is for live UI.

        :param text: The literal text to type.
        :return: JSON {ok, action, backend} or {success:false,...}.

<!-- mios-src:90b462569757 from usr/share/mios/openwebui/tools/mios_computer_use.py:252-257 -->

### Author a NEW document from text content you write, emitting...

Author a NEW document from text content you write, emitting a real
        office artifact (.docx / .pptx / .xlsx / .pdf / .html). The OUTPUT
        FORMAT is inferred from out_path's extension. You write markdown (or
        CSV for spreadsheets); MiOS renders the binary via Pandoc / LibreOffice
        -- fully local, no cloud. For .pptx, separate slides with a line of
        `---`. For .xlsx, set from_fmt="csv" and put CSV rows in content.

        :param out_path: Destination path with the target extension
            (e.g. /tmp/report.docx, /tmp/deck.pptx, /tmp/data.xlsx, /tmp/x.pdf).
        :param content: The source content to render. Markdown for docx/pptx/
            pdf/html; raw CSV rows for xlsx (with from_fmt="csv").
        :param from_fmt: Source format of `content`: markdown (default) |
            plain | html | csv.
        :return: JSON {ok, output, source, target, bytes} or {ok:false, error}.

<!-- mios-src:d768f6ac6470 from usr/share/mios/openwebui/tools/mios_computer_use.py:301-315 -->

### Convert an EXISTING file to another format (e.g. .docx ->...

Convert an EXISTING file to another format (e.g. .docx -> .pdf,
        .md -> .docx, .csv -> .xlsx, .pptx -> .pdf). Fully local via Pandoc /
        LibreOffice headless. Target format inferred from out_path's extension.

        :param in_path: Source file path (must exist on the host).
        :param out_path: Destination path; its extension picks the format.
        :return: JSON {ok, input, output, source, target, bytes} or
            {ok:false, error}.

<!-- mios-src:c6b5be3acfdb from usr/share/mios/openwebui/tools/mios_computer_use.py:336-344 -->
### A ratchet ceiling, or a hard failure if the SSOT has...

A ratchet ceiling, or a hard failure if the SSOT has stopped carrying it.

        Defaulting an absent ceiling to 999999 makes the check unfailable the
        moment a key is renamed, and it keeps reporting PASS while doing so --
        the worst outcome, because it also stops anyone looking. An absent
        ceiling is a broken gate, not an unlimited one.

<!-- mios-src:6052f6ace2c5 from tools/check-comment-ratchet.py:31-37 -->

### Gate

Gate: a hazard that only bites above one node is counted, not discovered.

A MiOS-Mini fleet is 2-6 boxes, so a config that only works standalone is a
defect waiting for the operator to add a peer. Each hazard is detected from the
tree rather than from a hand-list -- multiple archetypes able to stand up a k3s
control plane with no join path, and Pacemaker with fencing disabled -- and
every one must sit in the shrink-only [blades.hazards].accepted register under a
max_accepted ratchet. A NEW hazard fails; an entry that no longer reproduces
fails too, so the register cannot be padded.

<!-- mios-src:601cb0c605d3 from tools/check-fleet-safety.py:5-14 -->

### Keep mios-bootstrap.git in step with mios.git (Law 15)....

Keep mios-bootstrap.git in step with mios.git (Law 15).

Contract and rationale: installation/UNIFY.md.

<!-- mios-src:2d659e36d796 from tools/sync-bootstrap.py:4-7 -->

### A checker whose exit code never varies is not a check....

A checker whose exit code never varies is not a check.

These fixtures assert the tool runs against the real tree and returns an exit
code, then assert the specific invariant it exists to defend.

<!-- mios-src:385add9fd404 from tools/test_check-comment-lex-equivalence.py:5-9 -->

### Only assert the env-ceiling path for tools that actually...

Only assert the env-ceiling path for tools that actually READ those vars.

    Asserting it generically made the fixture fail on tools that never consume
    them -- a test failing for a reason unrelated to the behaviour it names is
    worse than no test, because it trains people to ignore it.

<!-- mios-src:2a391675b742 from tools/test_check-comment-lex-equivalence.py:46-51 -->

### A checker whose exit code never varies is not a check....

A checker whose exit code never varies is not a check.

These fixtures assert the tool runs against the real tree and returns an exit
code, then assert the specific invariant it exists to defend.

<!-- mios-src:385add9fd404 from tools/test_check-comment-ratchet.py:5-9 -->

### Only assert the env-ceiling path for tools that actually...

Only assert the env-ceiling path for tools that actually READ those vars.

    Asserting it generically made the fixture fail on tools that never consume
    them -- a test failing for a reason unrelated to the behaviour it names is
    worse than no test, because it trains people to ignore it.

<!-- mios-src:2a391675b742 from tools/test_check-comment-ratchet.py:46-51 -->

### A checker whose exit code never varies is not a check....

A checker whose exit code never varies is not a check.

These fixtures assert the tool runs against the real tree and returns an exit
code, then assert the specific invariant it exists to defend.

<!-- mios-src:385add9fd404 from tools/test_check-doc-ratchet-monotone.py:5-9 -->

### Only assert the env-ceiling path for tools that actually...

Only assert the env-ceiling path for tools that actually READ those vars.

    Asserting it generically made the fixture fail on tools that never consume
    them -- a test failing for a reason unrelated to the behaviour it names is
    worse than no test, because it trains people to ignore it.

<!-- mios-src:2a391675b742 from tools/test_check-doc-ratchet-monotone.py:46-51 -->

### Tests for the above-one-node hazard gate. Both detectors...

Tests for the above-one-node hazard gate.

Both detectors are covered independently: k3s multi-server needs BOTH two
grantors and a join-less `k3s server`, so a K3S_URL or a single grantor must
clear it, and pacemaker fencing must be read from code and not from comments.
Then every way the register stops measuring -- unsorted, duplicated, an unknown
id that can never retire, an entry that no longer reproduces, a missing ceiling,
a raised ceiling, a ceiling left high. Declaring max_nodes = 1 disarms the
hazards, because standalone is a real deployment and not a loophole.

<!-- mios-src:fc98532d7a4d from tools/test_check-fleet-safety.py:4-13 -->

### The three behaviours the drift gate depends on. An empty...

The three behaviours the drift gate depends on.

An empty launcher table used to render nothing, compare nothing, and report
success while 9 launchers shipped ungoverned -- so "refuses an empty table" is
the fixture that matters most here.

<!-- mios-src:a44982b23533 from tools/test_render-desktop.py:5-10 -->

### What the mirror must not get wrong. Two failure modes are...

What the mirror must not get wrong.

Two failure modes are specific and expensive: silently WRITING when only asked
to report, and appending a duplicate table instead of rewriting one -- the
duplicate-table bug that has made mios.toml unparseable twice in this repo.

<!-- mios-src:54cdb331075a from tools/test_sync-bootstrap.py:5-10 -->

### ADR-0016 D14

ADR-0016 D14: CephFS is a NATIVE service of the Mini platform, on
bare metal. Declaring it `either` would let a scheduler put the
storage plane on a transient OCI image.

<!-- mios-src:60a4a1ba90ee from tools/test_generate-mini-vs-hosted.py:345-347 -->

