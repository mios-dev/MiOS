<!-- AI-hint: Manual pages distilled from the source comments of automation, sanitized, each passage anchored to the comment it came from. -->

# automation

### Ports are ALLOCATED from [ports.categories] (base +...

Ports are ALLOCATED from [ports.categories] (base + index*stride), not read
off the flat table -- and the allocation must honour the layered override
chain (vendor/OEM default < /etc operator < user). The shared resolver is the
only thing that does both, so prefer it; the awk fallback below can only see
the flat vendor projection and exists purely so a stripped build host without
python still produces SOMETHING rather than an empty install.env.

<!-- mios-src:d8ec2062e5d6 from automation/35-render-ports.sh:23-28 -->

### Layout differs by upstream release. Newer tags nest the...

Layout differs by upstream release. Newer tags nest the sources under
policy/<distro>/; older ones -- which is what the vendored tarball is --
keep k3s.te FLAT at the archive root with no policy/ directory at all. The
old `find policy ...` had no fallback for that and, with `set -euo pipefail`,
a missing policy/ aborted the whole phase two seconds in with a bare exit 1 --
which is what the bake logged as "[WARN] 37-k3s-selinux".

<!-- mios-src:dcb7ebbac1a4 from automation/37-k3s-selinux.sh:49-54 -->

### The 42 MB asset we actually ship. It is a SOURCE SNAPSHOT...

The 42 MB asset we actually ship. It is a SOURCE SNAPSHOT (pyproject.toml
+ setup.py under a hermes-agent-main/ root), not a wheelhouse -- it holds
zero .whl files. Nothing consumed it: none of the probes above name it,
and pip's --find-links ignores it because an sdist filename must carry a
version (hermes_agent-<ver>.tar.gz) for the finder to parse a candidate.
So every "offline" build silently fell through to the git clone below.

<!-- mios-src:540cc82d5b8d from automation/72-hermes-agent.sh:69-74 -->

### Pre-flight

Pre-flight: the three inputs must exist. Missing inputs is a hard error
(the lint cannot make any assertion) -- but stay degrade-friendly: if the
Quadlet dir is simply absent (e.g. a minimal checkout), PASS vacuously.

<!-- mios-src:3f7fe6a1077a from automation/97-ssot-lint.sh:57-59 -->

### (1) Collect every ${MIOS_*} referenced in an...

--- (1) Collect every ${MIOS_*} referenced in an Exec=/Environment= line. ----
We scan recursively (the dir has a users/ subtree). Match the directive at
line start (Exec=, ExecStart=, ExecStartPre=, ExecStartPost=, Environment=).
From those lines, extract bare placeholder NAMES of the form ${MIOS_...}
(with or without a ':-default' tail). Critically we extract only the
PLACEHOLDER inside ${...}; the left-hand `Environment=MIOS_FOO=` literal
(a container-internal env var name being SET) is NOT a placeholder and is
correctly ignored because it is not wrapped in ${...}.

<!-- mios-src:7daebbc3a66d from automation/97-ssot-lint.sh:78-85 -->

### (2) Build the userenv.sh wiring set....

--- (2) Build the userenv.sh wiring set. -------------------------------------
A var is "wired in userenv" if it appears, on a NON-comment line, either as
a typed slot target  ("section.field", "MIOS_X")  -> the quoted token
"MIOS_X"  -- or as an explicit  export MIOS_X=  /  MIOS_X=  assignment, or
named in a legacy for-loop. We strip full-line comments first so a var that
is only *mentioned* in prose (e.g. MIOS_CRAWL_CDP_URL in a doc paragraph)
does NOT count as wired.

<!-- mios-src:bd0d334822c4 from automation/97-ssot-lint.sh:103-109 -->

### (3) Build the render-quadlets.sh allowlist set....

--- (3) Build the render-quadlets.sh allowlist set. --------------------------
A var is "wired in render" if it appears in the envsubst allowlist string
( ${MIOS_X} ) and/or the bash-fallback `for var in ...` list ( MIOS_X ),
on a NON-comment line. Both forms reduce to: the bareword MIOS_X occurs in
render-quadlets.sh code. (render-quadlets.sh also EXPORTS a couple vars
dynamically -- e.g. MIOS_CODE_SERVER_UID via `id -u` -- which the bareword
match likewise accepts.)

<!-- mios-src:8abe5835330f from automation/97-ssot-lint.sh:136-142 -->

### Windows PowerShell 5.1 -- which is what runs the install...

Windows PowerShell 5.1 -- which is what runs the install path on a stock
Windows box -- reads a BOM-less file as ANSI, not UTF-8. Any .ps1 carrying
non-ASCII (the box-drawing run separators, arrows and accented text MiOS
prints) therefore MUST ship a UTF-8 BOM or its output is mojibake. This is the
same convention tools/render-globals.py already writes with (utf-8-sig).
Pure-ASCII scripts need no BOM and must not carry a pointless one.

<!-- mios-src:62f7b82da080 from automation/98-drift-checks.sh:6736-6741 -->

### 'MiOS' overlay -- make BUILDER look/feel like a Live 'MiOS'...

---------------------------------------------------------------------------
'MiOS' overlay -- make BUILDER look/feel like a Live 'MiOS' environment.
Rsyncs the user-facing assets (mios CLI, motd, vendor docs, paths.sh,
profile.d hooks) into the podman-machine without touching its systemd /
sysusers / tmpfiles plumbing (those live only in the bootc image).
---------------------------------------------------------------------------

<!-- mios-src:d0d74784cb5b from automation/mios-build-builder.ps1:219-224 -->

### validate-kargs.py -- 'MiOS' kargs.d schema validator....

validate-kargs.py -- 'MiOS' kargs.d schema validator.

Checks every *.toml in:
  kargs.d/                              (repo root drop-ins)
  usr/lib/bootc/kargs.d/  (image-baked drop-ins)

Schema rules (bootc-dev/bootc authoritative):
  - Top-level key `kargs` (required) must be a list of strings.
  - Top-level key `match-architectures` (optional) must be a list of strings.
  - NO other top-level keys.
  - NO [section] table headers anywhere in the file.
  - Each kargs entry must be a single string (not space-joined multi-arg).
  - Keys with "delete" in their name are invalid parameter -- reject.

Exit codes: 0 = pass, 1 = validation failure(s), 2 = usage error.

<!-- mios-src:ad7c112407e8 from automation/validate-kargs.py:4-20 -->
