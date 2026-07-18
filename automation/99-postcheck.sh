#!/usr/bin/env bash
# AI-hint: Final build-time validation script that enforces mandatory security invariants, such as OpenSSH version minimums and Cockpit configuration checks, to abort the build if the image is insecure or non-compliant.
# AI-related: /usr/share/mios/ai, /etc/mios/ai, mios-ceph, mios-k3s, wsl-init.service
# AI-functions: _sysusers_effective, _gid_in_etc_group
# 99-postcheck.sh - build-time technical invariant validation
# 
# This script runs at the very end of the Containerfile build (before cleanup).
# It enforces mandatory version requirements, security postures, and 
# architectural purity. Failures here ABORT THE BUILD to prevent shipping
# a regressed or vulnerable image.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "'MiOS' build-time validation"

# 0. Materialize sysusers.d entries so subsequent checks (#11 in particular)
# see the same /etc/passwd + /etc/group state the deployed image will have
# at first boot. Without this, upstream-RPM-shipped sysusers.d files (e.g.
# cockpit-ws shipping a 'g cockpit' line) are present on disk but their
# users/groups are not yet in /etc/group, so 'systemd-tmpfiles --dry-run'
# reports false-positive 'Failed to resolve group cockpit: Unknown group'
# warnings on lines that will resolve fine at runtime. systemd-sysusers
# is idempotent and the same operation that runs at first boot anyway.
if command -v systemd-sysusers >/dev/null 2>&1; then
    log "Materializing sysusers.d into /etc/passwd + /etc/group..."
    if systemd-sysusers --no-pager 2>/dev/null; then
        log "  [ok] sysusers.d entries materialized"
    else
        log "  [warn] systemd-sysusers exited non-zero; subsequent checks may have false-positives"
    fi
fi

# 1. OpenSSH Version Check (CVE-2026-4631 / Cockpit RCE mitigation)
# Requirement: ≥ 9.6
log "Checking OpenSSH version..."
if ! command -v sshd >/dev/null 2>&1; then
    die "sshd not found in image (required for Podman-machine & remote mgmt)"
fi

SSH_VER_RAW=$(sshd -V 2>&1 | head -n1 | grep -oP 'OpenSSH_\K[0-9.]+')
log "  Found: OpenSSH $SSH_VER_RAW"

# Compare version (simple dot-split comparison)
if [[ $(printf '%s\n9.6' "$SSH_VER_RAW" | sort -V | head -n1) != "9.6" ]]; then
    die "OpenSSH version $SSH_VER_RAW is below required 9.6 (Vulnerable to CVE-2026-4631 in Cockpit context)"
fi
log "  [ok] OpenSSH version is safe"

# 2. Cockpit Security Posture
log "Checking Cockpit configuration..."
# In Rootfs-Native, config might be in /etc or /usr/lib
if [[ -f "/etc/cockpit/cockpit.conf" ]]; then
    COCKPIT_CONF="/etc/cockpit/cockpit.conf"
elif [[ -f "/usr/lib/cockpit/cockpit.conf" ]]; then
    COCKPIT_CONF="/usr/lib/cockpit/cockpit.conf"
else
    COCKPIT_CONF=""
fi

if [[ -f "$COCKPIT_CONF" ]]; then
    if ! grep -q "LoginTo = false" "$COCKPIT_CONF"; then
        die "Cockpit LoginTo mitigation missing in $COCKPIT_CONF (CVE-2026-4631)"
    fi
    log "  [ok] Cockpit LoginTo = false is enforced"
else
    log "  [!] Cockpit config not found at expected paths; skipping check"
fi

# 3. Kernel Argument Validation (Schema Strictness Preparation)
log "Validating kargs.d files..."
if [[ -d /usr/lib/bootc/kargs.d ]]; then
    for f in /usr/lib/bootc/kargs.d/*; do
        [[ -e "$f" ]] || continue
        # Future: run 'bootc container lint' or specialized schema check
        log "  found karg: $(basename "$f")"
    done
    log "  [ok] kargs.d presence verified"
fi

# 4. Critical Package Verification
log "Verifying critical system binaries..."
CRITICAL_TOOLS=(podman bootc cockpit-bridge rpm-ostree)
for tool in "${CRITICAL_TOOLS[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        die "Critical tool '$tool' is missing from the image"
    fi
    log "  [ok] $tool present"
done

# 5. NVIDIA Container Toolkit Version Check
log "Checking NVIDIA Container Toolkit version..."
if command -v nvidia-ctk >/dev/null 2>&1; then
    NCT_VER=$(nvidia-ctk --version | head -n1 | grep -oP 'version \K[0-9.]+')
    log "  Found: $NCT_VER"
    if [[ $(printf '%s\n1.18' "$NCT_VER" | sort -V | head -n1) != "1.18" ]]; then
        die "nvidia-container-toolkit version $NCT_VER is below required 1.18"
    fi
    log "  [ok] NVIDIA Container Toolkit version is safe"
fi

# 6. Cockpit Version Check (for CVE-2026-4631)
log "Checking Cockpit version..."
if rpm -q cockpit >/dev/null 2>&1; then
    COCKPIT_VER=$(rpm -q cockpit --queryformat '%{VERSION}')
    log "  Found: Cockpit $COCKPIT_VER"
    # CVE fixed in 360. 'MiOS' targets 361+ for Fedora 44 GA stability.
    if [[ $(printf '%s\n361' "$COCKPIT_VER" | sort -V | head -n1) != "361" ]]; then
        log "  [!] Cockpit version $COCKPIT_VER is below 361 (Risk: CVE-2026-4631 / Regressions)"
    else
        log "  [ok] Cockpit version is safe"
    fi
fi

# 7. WSL2 wsl.conf parse + parity check
# A malformed /etc/wsl.conf takes down systemd-as-PID1 in WSL2, which
# cascades to a broken user session, missing /var/home/mios, and a fallback
# cwd of /mnt/c/.... Catch drift at build time so we never ship a broken
# file. Also enforces parity with /usr/lib/wsl.conf (the canonical reference
# wsl-init.service uses to auto-restore).
log "Validating /etc/wsl.conf (ASCII + parse + parity with /usr/lib/wsl.conf)..."
if [[ -f /etc/wsl.conf ]]; then
    # WSL2's INI parser is byte-naive -- multibyte chars (em-dashes, smart quotes,
    # NBSP) shift its line counter and surface as bogus "Expected ' ' or '\n' in
    # /etc/wsl.conf:N" errors at boot. Python configparser tolerates UTF-8 so a
    # parse-only check misses these. Enforce strict ASCII before the parse runs.
    if LC_ALL=C grep -nP '[^\x00-\x7F]' /etc/wsl.conf >&2; then
        die "/etc/wsl.conf contains non-ASCII bytes (WSL2's parser will choke)"
    fi
    log "  pure ASCII"
    # CRLF detection. .gitattributes pins *.conf to eol=lf, but on a
    # Windows host with core.autocrlf=true the working tree can carry
    # CRLF that the build context inherits. WSL2's INI parser treats
    # the trailing \r as garbage and reports "Expected ' ' or '\n' in
    # /etc/wsl.conf:N+1" past the last LF -- exactly the same shape
    # as a non-ASCII failure. Catch it independently here.
    if LC_ALL=C grep -lP '\r' /etc/wsl.conf >/dev/null 2>&1; then
        die "/etc/wsl.conf contains CRLF line endings (must be LF; WSL2's parser will choke)"
    fi
    log "  pure LF line endings"
    if command -v python3 >/dev/null 2>&1; then
        python3 -c '
import configparser, sys
p = configparser.ConfigParser(strict=True, interpolation=None)
try:
    with open("/etc/wsl.conf") as f:
        p.read_file(f)
except Exception as e:
    sys.stderr.write(f"wsl.conf parse failed: {e}\n"); sys.exit(1)
required = {"boot": ["systemd"], "user": ["default"]}
for section, keys in required.items():
    if not p.has_section(section):
        sys.stderr.write(f"wsl.conf missing required [section]: {section}\n"); sys.exit(1)
    for k in keys:
        if not p.has_option(section, k):
            sys.stderr.write(f"wsl.conf missing required key: {section}.{k}\n"); sys.exit(1)
print("  /etc/wsl.conf parses cleanly with all required sections/keys")
' || die "/etc/wsl.conf failed parse/required-keys validation"
    else
        log "  [!] python3 unavailable -- skipping wsl.conf parse (post-build only)"
    fi
    if [[ -f /usr/lib/wsl.conf ]]; then
        if ! cmp -s /etc/wsl.conf /usr/lib/wsl.conf; then
            die "/etc/wsl.conf drifted from /usr/lib/wsl.conf reference at build time"
        fi
        log "  [ok] /etc/wsl.conf matches /usr/lib/wsl.conf reference"
    fi
else
    log "  [!] /etc/wsl.conf not present in image -- WSL2 deploys will fall back to defaults"
fi

# 8. sysusers.d sanity -- login-shell users MUST have a fixed UID.
# Auto-allocation ('-') picks from the SYSTEM range (<UID_MIN), and logind
# then refuses to create /run/user/<uid>/. The cascade kills dbus user
# session, dconf, Wayland session services, and every GTK app that needs
# a session bus.
#
# Files in /etc/sysusers.d/ override files of the same basename in
# /usr/lib/sysusers.d/ (systemd-sysusers.d(5)), so when an override exists
# the /usr/lib/ file is shadowed at runtime -- validate the effective file.
log "Validating sysusers.d login users have fixed UIDs..."
_sysusers_effective() {
    local d
    declare -A _seen=()
    for d in /etc/sysusers.d /usr/lib/sysusers.d; do
        [[ -d "$d" ]] || continue
        for f in "$d"/*.conf; do
            [[ -f "$f" ]] || continue
            local base
            base="$(basename "$f")"
            [[ -n "${_seen[$base]:-}" ]] && continue
            _seen[$base]=1
            printf '%s\n' "$f"
        done
    done
}
_sysusers_bad=$(
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        # u <name> <uid_or_-> [<gecos>] [<home>] [<shell>]
        # Match users whose shell is a login shell and uid is bare '-'.
        awk '
            /^u[[:space:]]+/ {
                # field 3 = uid spec, last field = shell (or empty)
                shell = $NF
                if ($3 == "-" && shell ~ /\/(bash|zsh|sh|fish|dash|csh|tcsh|ksh)$/) {
                    print FILENAME ":" NR ": " $0
                }
            }' "$f"
    done < <(_sysusers_effective)
)
if [[ -n "$_sysusers_bad" ]]; then
    printf '%s\n' "$_sysusers_bad" >&2
    die "sysusers.d defines login-shell user(s) with auto-allocated UID; pin to a value >= 1000"
fi
log "  all login-shell sysusers entries have fixed UIDs"

# 8b. sysusers.d: every `u user UID:GID` must reference a GID that
# systemd-sysusers will be able to resolve at first boot. Resolution order
# matches sysusers itself:
#   1. `g <name> <gid>` line in ANY effective sysusers.d file (cross-file).
#   2. Existing entry in /etc/group at build time (NSS).
# Either path satisfies the invariant; both must miss before we flag.
#
# Upstream packages (setup, nfs-utils, ...) ship u-lines like
# `u root 0:0 ...` and `u nfsnobody 65534:65534 ...` whose GIDs come from
# /etc/group seeded by the base image, not from a co-located g-line.
# Single-file scope flagged those as broken; the cross-file + NSS lookup
# below matches what sysusers actually does at boot.
log "Validating sysusers.d UID:GID resolves to a created group..."
# First pass: collect every `g <name> <gid>` declared anywhere in the
# effective sysusers tree.
_sysusers_known_gids=$(
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        awk '/^g[[:space:]]+/ && $3 ~ /^[0-9]+$/ { print $3 }' "$f"
    done < <(_sysusers_effective) | sort -u
)
# Helper: is GID resolvable via /etc/group at build time?
_gid_in_etc_group() {
    [[ -r /etc/group ]] || return 1
    awk -F: -v g="$1" '$3 == g {found=1} END {exit !found}' /etc/group
}
_sysusers_unresolved=$(
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        awk -v known="$_sysusers_known_gids" '
            BEGIN {
                n = split(known, k, "\n")
                for (i = 1; i <= n; i++) if (k[i] != "") seen[k[i]] = 1
            }
            /^u[[:space:]]+/ {
                # field 3 = UID:GID. Skip "-" or empty.
                split($3, a, ":")
                if (a[2] !~ /^[0-9]+$/) next
                if (a[2] in seen) next
                print FILENAME ":" NR ":" a[2] ": " $0
            }' "$f"
    done < <(_sysusers_effective)
)
# Second pass: drop hits whose GID is already in /etc/group.
_sysusers_truly_unresolved=$(
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        gid="${line#*:*:}"; gid="${gid%%:*}"
        if _gid_in_etc_group "$gid"; then continue; fi
        # Strip the synthetic ':<gid>:' marker before reporting.
        echo "${line%%:*}:${line#*:}" | sed -E 's/:[0-9]+:/:/'
    done <<< "$_sysusers_unresolved"
)
if [[ -n "$_sysusers_truly_unresolved" ]]; then
    printf '%s\n' "$_sysusers_truly_unresolved" >&2
    die "sysusers.d: u-line references a numeric GID with no 'g name GID' anywhere in /etc/sysusers.d or /usr/lib/sysusers.d AND no matching entry in /etc/group"
fi
log "  all u-line GIDs resolve via cross-file g-lines or /etc/group"

# 9. tmpfiles.d: no /var/run or /var/lock paths.
# Both are FHS-compat symlinks to /run subdirs. systemd-tmpfiles emits
# "Line references path below /var/run" and refuses to act on the entry.
# Catch the bug class at build time so we never ship a broken declaration.
log "Validating tmpfiles.d uses /run (not /var/run / /var/lock)..."
_tmpfiles_legacy=$(
    for f in /usr/lib/tmpfiles.d/*.conf /etc/tmpfiles.d/*.conf; do
        [[ -f "$f" ]] || continue
        # Match non-comment lines whose path field starts with /var/run or /var/lock.
        # Field 2 of a tmpfiles line is the path; tolerate leading whitespace and
        # tabs after the type field.
        awk '
            /^[[:space:]]*[a-zA-Z]/ {
                if ($2 ~ /^\/var\/(run|lock)\//) {
                    print FILENAME ":" NR ": " $0
                }
            }' "$f"
    done
)
if [[ -n "$_tmpfiles_legacy" ]]; then
    printf '%s\n' "$_tmpfiles_legacy" >&2
    die "tmpfiles.d entry uses /var/run or /var/lock (use /run or /run/lock instead)"
fi
log "  tmpfiles.d entries use canonical /run paths"

# 10. systemd-analyze verify on MiOS-owned services + targets.
# Catches: bad directive names, malformed values, missing required sections,
# unparseable [Install] entries. Drop-ins that reference non-shipped units
# generate noise so we only verify our own self-contained units. Errors
# referenced as "Failed to load configuration" or "directive not understood"
# are fatal; everything else (file-not-found from external Wants=, etc.) is
# tolerable and gets filtered out.
log "Validating MiOS systemd unit syntax..."
if command -v systemd-analyze >/dev/null 2>&1; then
    _bad_units=$(
        for u in /usr/lib/systemd/system/mios-*.service \
                 /usr/lib/systemd/system/mios-*.target; do
            [[ -f "$u" ]] || continue
            out=$(systemd-analyze --no-pager verify "$u" 2>&1 || true)
            # Filter: only complaints about THIS file are real (filename prefix).
            # External-reference warnings name the dependency, not "$u".
            echo "$out" | grep -E "^${u}:" || true
        done
    )
    if [[ -n "$_bad_units" ]]; then
        printf '%s\n' "$_bad_units" >&2
        die "systemd-analyze verify reported errors in MiOS unit(s)"
    fi
    log "  MiOS units lint clean"
else
    log "  systemd-analyze unavailable -- skipping unit verification"
fi

# 11. systemd-tmpfiles --dry-run on MiOS-owned tmpfiles configs.
# Catches: bad path syntax, unsupported types, missing required fields. The
# legacy /var/run / /var/lock case is already covered by #9; this catches
# every other tmpfiles syntax error.
#
# Boot-order caveat: at runtime systemd-sysusers runs before
# systemd-tmpfiles, so groups/users declared in sysusers.d are present
# in /etc/{passwd,group} by the time tmpfiles resolves them. At build
# time inside the OCI image, sysusers has not run, so dry-running
# tmpfiles reports false-positive "Failed to resolve user/group X:
# Unknown user/group" warnings for entities declared in sysusers.d.
# We harvest the declared name set and filter those warnings out --
# every other tmpfiles error still fails the build.
log "Validating MiOS tmpfiles.d syntax..."
if command -v systemd-tmpfiles >/dev/null 2>&1; then
    # Build the union of users + groups declared by sysusers.d (any file).
    _sysusers_declared=$(
        for d in /etc/sysusers.d /usr/lib/sysusers.d; do
            [[ -d "$d" ]] || continue
            for f in "$d"/*.conf; do
                [[ -f "$f" ]] || continue
                awk '/^[ug][[:space:]]+/ { print $2 }' "$f"
            done
        done | sort -u
    )
    _bad_tmpfiles=$(
        for f in /usr/lib/tmpfiles.d/mios-*.conf; do
            [[ -f "$f" ]] || continue
            # --dry-run alone reports parse errors; combine with --create
            # (also dry-run) so it exercises the full directive interpreter.
            out=$(systemd-tmpfiles --dry-run --create "$f" 2>&1 || true)
            # Keep only lines that name THIS file (filename prefix).
            echo "$out" | awk -v f="$f" -v decl="$_sysusers_declared" '
                BEGIN {
                    n = split(decl, a, "\n")
                    for (i = 1; i <= n; i++) if (a[i] != "") known[a[i]] = 1
                }
                # Only this-file lines are real findings.
                $0 !~ "^" f ":" { next }
                {
                    # If the warning is the boot-order false positive,
                    # extract the missing entity name and drop the line
                    # if it is declared in sysusers.d.
                    if (match($0, /Failed to resolve (user|group) [\x27"]([^\x27"]+)[\x27"]/, m)) {
                        if (m[2] in known) next
                    }
                    print
                }'
        done
    )
    if [[ -n "$_bad_tmpfiles" ]]; then
        printf '%s\n' "$_bad_tmpfiles" >&2
        die "systemd-tmpfiles reported errors in MiOS tmpfiles.d config(s)"
    fi
    log "  MiOS tmpfiles.d configs parse clean (sysusers-declared names accepted)"
else
    log "  systemd-tmpfiles unavailable -- skipping tmpfiles verification"
fi

# 12. UNIFIED-AI-REDIRECTS (Architectural Law 5).
# Active configuration MUST NOT hard-code vendor cloud URLs. Comments may
# show alternatives for documentation, so we strip comment lines before
# matching. Scope: actual config dirs in the deployed image, not docs.
log "Validating UNIFIED-AI-REDIRECTS (Law 5): no vendor URLs in active config..."
_law5_dirs=(
    /etc/containers/systemd
    /usr/share/containers/systemd
    /usr/lib/systemd/system
    /usr/share/mios/ai
    /etc/mios/ai
)
_law5_pattern='https?://(api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|api\.cohere\.|api\.mistral\.|api\.cline\.bot|api\.cursor\.com|api\.githubcopilot\.com)'
_law5_hits=""
for d in "${_law5_dirs[@]}"; do
    [[ -d "$d" ]] || continue
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        # Strip leading-whitespace + comment lines for the file's syntax;
        # then match. Cover #-comment files (toml/yaml/conf/sh/Quadlet) and
        # //-comment files. JSON has no comments so the strip is a no-op.
        active=$(sed -E '/^[[:space:]]*(#|\/\/)/d' "$f")
        if printf '%s\n' "$active" | grep -qE "$_law5_pattern"; then
            _law5_hits+="$f"$'\n'
        fi
    done < <(find "$d" -type f \( -name '*.container' -o -name '*.service' \
        -o -name '*.json' -o -name '*.toml' -o -name '*.conf' -o -name '*.yaml' \
        -o -name '*.yml' \) 2>/dev/null)
done
if [[ -n "$_law5_hits" ]]; then
    printf '%s' "$_law5_hits" >&2
    die "UNIFIED-AI-REDIRECTS: vendor cloud URL found in active config (must route through MIOS_AI_ENDPOINT)"
fi
log "  no vendor URLs in active config"

# 12b. UNIFIED-AI-REDIRECTS (Law 5) -- retired :11434 (ollama) inference lane.
# WS-0B drift-gate: the ollama lane on :11434 is retired ENTIRELY (G5/G17 ->
# everything moved to mios-llm-light :8450). MiOS is OpenAI-/v1-only, so NO
# :11434 ref is legitimate -- local OR remote (the old remote-tailnet exception
# is removed). Active config in the AI plane must NOT dial it; a stale ref
# silently 404s a refine / sys-agent / DCI call. Scope: the SAME dirs as the
# vendor-URL check.
log "Validating UNIFIED-AI-REDIRECTS (Law 5): no retired :11434 lane in active config..."
_dead_lane_pattern=':11434'
_dead_lane_hits=""
for d in "${_law5_dirs[@]}"; do
    [[ -d "$d" ]] || continue
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        active=$(sed -E '/^[[:space:]]*(#|\/\/)/d' "$f")
        if printf '%s\n' "$active" | grep -qE "$_dead_lane_pattern"; then
            _dead_lane_hits+="$f"$'\n'
        fi
    done < <(find "$d" -type f \( -name '*.container' -o -name '*.service' \
        -o -name '*.conf' -o -name '*.json' -o -name '*.toml' -o -name '*.yaml' \
        -o -name '*.yml' \) 2>/dev/null)
done
if [[ -n "$_dead_lane_hits" ]]; then
    printf '%s' "$_dead_lane_hits" >&2
    die "UNIFIED-AI-REDIRECTS: retired :11434 (ollama) lane in active config -- MiOS is /v1-only; use the live lane, e.g. mios-llm-light :8450"
fi
log "  no retired :11434 lane in active config"

# 12c. UNIFIED-AI-REDIRECTS (Law 5) -- agent dispatch-target recursion guard.
# WS-4 structural invariant (the BUILD-TIME half; the runtime half is the
# X-MiOS-Hop / X-MiOS-Via hop-budget guard in agent-pipe). A dispatch TARGET in
# [agents.*] must point at a real worker ingress / model lane, NEVER back at the
# ORCHESTRATOR ([ai].endpoint, the :8640 meta-pipeline) or a THIN GATEWAY
# ([ports].hermes Discord/CLI ingress, :8642). A target that loops to the
# orchestrator/gateway re-creates the dGPU-pegging recursion (the
# runaway class). Ports are DERIVED from the SSOT ([ai].endpoint + [ports].hermes)
# -- no hardcoded port literal. python3-guarded (TOML parse); skipped only when
# python3 is absent (the bash Law checks above still run).
log "Validating UNIFIED-AI-REDIRECTS (Law 5): no [agents.*] dispatch target loops to the orchestrator/gateway..."
if command -v python3 >/dev/null 2>&1; then
    if _recursion_out=$(python3 - <<'PYEOF'
import os, re, sys
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("SKIP: no tomllib"); sys.exit(0)
toml = "/usr/share/mios/mios.toml"
if not os.path.exists(toml):
    print("SKIP: %s not found" % toml); sys.exit(0)
with open(toml, "rb") as f:
    d = tomllib.load(f)
def _port(u):
    m = re.search(r":(\d+)", str(u or ""))
    return m.group(1) if m else ""
ai = d.get("ai") or {}
ports = d.get("ports") or {}
orch = _port(ai.get("endpoint"))
gw = str(ports.get("hermes") or "").strip()
label = {}
if orch:
    label[orch] = "orchestrator"
if gw:
    label[gw] = "thin-gateway"
bad = []
for name, cfg in (d.get("agents") or {}).items():
    if not isinstance(cfg, dict):
        continue
    ep = str(cfg.get("endpoint") or "").strip()
    if not ep:
        continue
    p = _port(ep)
    if p and p in label:
        bad.append("  [agents.%s] endpoint %s loops to the %s (:%s)" % (name, ep, label[p], p))
if bad:
    sys.stderr.write("\n".join(bad) + "\n")
    sys.stderr.write("  a dispatch target must be a real worker ingress / model lane, "
                     "never :%s (orchestrator) / :%s (gateway)\n" % (orch, gw))
    sys.exit(1)
print("orchestrator=:%s gateway=:%s agents=%d clean" % (orch, gw, len(d.get("agents") or {})))
PYEOF
    ); then
        log "  $_recursion_out"
    else
        die "UNIFIED-AI-REDIRECTS: an [agents.*] dispatch target loops back to the orchestrator/gateway (recursion risk -- see above)"
    fi
else
    log "  [!] python3 unavailable -- skipping agent-recursion guard"
fi

# 13. UNPRIVILEGED-QUADLETS (Architectural Law 6).
# Every Quadlet *.container under /etc/containers/systemd or
# /usr/share/containers/systemd MUST declare User=, with the DOCUMENTED root
# exceptions below (kept in sync with CLAUDE.md Law 6). Two classes of root
# exception: NO User= line -> mios-ceph + mios-k3s (need uid 0) + mios-llm-heavy
# (SGLang needs root for the nvidia-smi probe); explicit User=root -> mios-
# forgejo-runner (CI runner, --privileged) + mios-coderun-sandbox@ (root but
# Network=none + ReadOnly). Group= + Delegate=yes are SHOULD-have. (SHOULD-have
# follow-up: also flag an UNDOCUMENTED User=root Quadlet, not just a missing User=.)
log "Validating UNPRIVILEGED-QUADLETS (Law 6): every Quadlet declares User=..."
_law6_exceptions='^(mios-ceph|mios-k3s|mios-llm-heavy|mios-forgejo-runner|mios-coderun-sandbox.*)\.container$'
_law6_missing=""
for d in /etc/containers/systemd /usr/share/containers/systemd; do
    [[ -d "$d" ]] || continue
    for f in "$d"/*.container "$d"/*/*.container; do
        [[ -f "$f" ]] || continue
        base=$(basename "$f")
        if [[ "$base" =~ $_law6_exceptions ]]; then continue; fi
        if ! grep -qE '^[[:space:]]*User=' "$f"; then
            _law6_missing+="$f: missing User= directive"$'\n'
        fi
    done
done
if [[ -n "$_law6_missing" ]]; then
    printf '%s' "$_law6_missing" >&2
    die "UNPRIVILEGED-QUADLETS: Quadlet missing User= (exceptions: mios-ceph, mios-k3s, mios-llm-heavy, mios-forgejo-runner, mios-coderun-sandbox)"
fi
log "  every Quadlet declares User= (or is a documented root exception)"

# 14. BOUND-IMAGES (Architectural Law 3).
# Every Quadlet *.container in /etc/containers/systemd or
# /usr/share/containers/systemd MUST be symlinked (by basename) into
# /usr/lib/bootc/bound-images.d/ so the image bind-binds with the host.
# Detected drift = a Quadlet that ships without its image binding, or
# a stale binding pointing at a Quadlet that no longer exists.
log "Validating BOUND-IMAGES (Law 3): Quadlet -> bound-images.d/ coverage..."
_bind_dir=/usr/lib/bootc/bound-images.d
_law3_missing=""
_law3_extra=""
if [[ -d "$_bind_dir" ]]; then
    declare -A _seen_quadlets=()
    for d in /etc/containers/systemd /usr/share/containers/systemd; do
        [[ -d "$d" ]] || continue
        for f in "$d"/*.container "$d"/*/*.container; do
            [[ -f "$f" ]] || continue
            base=$(basename "$f")
            _seen_quadlets["$base"]=1
            if [[ ! -e "$_bind_dir/$base" ]]; then
                _law3_missing+="$base: no symlink in $_bind_dir/"$'\n'
            fi
        done
    done
    for b in "$_bind_dir"/*.container; do
        [[ -e "$b" ]] || continue
        base=$(basename "$b")
        if [[ -z "${_seen_quadlets[$base]:-}" ]]; then
            _law3_extra+="$base: stale binding in $_bind_dir/ (no source Quadlet)"$'\n'
        fi
    done
    if [[ -n "$_law3_missing" || -n "$_law3_extra" ]]; then
        [[ -n "$_law3_missing" ]] && printf '%s' "$_law3_missing" >&2
        [[ -n "$_law3_extra" ]] && printf '%s' "$_law3_extra" >&2
        die "BOUND-IMAGES: Quadlet/binder drift (every *.container must symlink into $_bind_dir/)"
    fi
    log "  every Quadlet has a corresponding bound-images.d/ symlink"
else
    log "  $_bind_dir not present -- skipping (binder loop did not run)"
fi


# 15. BENCHMARK INTEGRATION (T-039).
# Runs the benchmark suite using a mock API server in the background
# and prints the results table to the build log.
log "Running build-time capability benchmark (T-039)..."
if command -v python3 >/dev/null 2>&1; then
    # Spin up mock server in the background
    python3 -c '
import http.server, json, threading
class MockHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "choices": [{"message": {"content": "42 Paris"}}]
        }).encode())
server = http.server.HTTPServer(("127.0.0.1", 8649), MockHandler)
server.serve_forever()
' &
    MOCK_PID=$!
    # Wait for mock server to be ready
    sleep 0.5
    
    # Run mios-bench (resolved using relative path if needed, but absolute is safer since overlay is applied)
    # If /usr/libexec/mios/mios-bench doesn't exist, we fall back to absolute path relative to script dir.
    BENCH_BIN="/usr/libexec/mios/mios-bench"
    if [[ ! -x "$BENCH_BIN" ]]; then
        BENCH_BIN="$(dirname "${BASH_SOURCE[0]}")/../usr/libexec/mios/mios-bench"
    fi
    
    python3 "$BENCH_BIN" run --suite gaia-lite --endpoint http://127.0.0.1:8649/v1 --k 1
    
    # Kill mock server
    kill "$MOCK_PID" || true
    log "  [ok] benchmark harness executed successfully"
else
    log "  [!] python3 missing -- skipping benchmark run"
fi

# 16. BARE-SAFE-ENV (Architectural Law 10).
# system-sync-env.sh renders /etc/mios/install.env as BARE KEY=value lines that
# must be safe under all three parsers (systemd EnvironmentFile=, bash `source`,
# podman --env-file). Render --dry-run and assert: no double-quoted values (`="`),
# every non-comment line is a bare KEY=value, no secret NAMES leak in, and the
# whole render sources clean under `set -u`. (This is the build gate behind
# system-sync-env's own non-fatal R4 self-test.)
log "Validating BARE-SAFE-ENV (Law 10): system-sync-env --dry-run is bare KEY=value..."
_sync_env="/usr/libexec/mios/system-sync-env.sh"
[[ -x "$_sync_env" ]] || _sync_env="$(dirname "${BASH_SOURCE[0]}")/../usr/libexec/mios/system-sync-env.sh"
if [[ -f "$_sync_env" ]]; then
    if ! _env_render="$(bash "$_sync_env" --dry-run 2>/dev/null)"; then
        die "BARE-SAFE-ENV: 'system-sync-env.sh --dry-run' failed to render install.env"
    fi
    # (a) no double-quoted values (breaks podman --env-file)
    if printf '%s\n' "$_env_render" | grep -nE '="' >&2; then
        die "BARE-SAFE-ENV: install.env render contains a double-quoted value (breaks podman --env-file)"
    fi
    # (b) every non-comment/non-blank line is a bare KEY=value
    _law10_bad="$(printf '%s\n' "$_env_render" | grep -vE '^[[:space:]]*(#|$)' | grep -vE '^[A-Za-z_][A-Za-z0-9_]*=' || true)"
    if [[ -n "$_law10_bad" ]]; then
        printf '%s\n' "$_law10_bad" >&2
        die "BARE-SAFE-ENV: install.env render has a non-bare 'KEY=value' line"
    fi
    # (c) no secret NAMES in the derived env
    if printf '%s\n' "$_env_render" | grep -nE '^(MIOS_USER_PASSWORD_HASH|MIOS_FORGE_ADMIN_PASSWORD|MIOS_GITHUB_TOKEN)=' >&2; then
        die "BARE-SAFE-ENV: a secret name leaked into install.env (secrets live ONLY in /etc/mios/secrets.env)"
    fi
    # (d) sources clean under set -u
    _law10_tmp="$(mktemp)"
    printf '%s\n' "$_env_render" > "$_law10_tmp"
    if ! bash -u -c ". '$_law10_tmp'" >/dev/null 2>&1; then
        rm -f "$_law10_tmp"
        die "BARE-SAFE-ENV: install.env render does not source clean under 'set -u'"
    fi
    rm -f "$_law10_tmp"
    log "  [ok] install.env render is bare KEY=value, secret-free, and set -u clean"
else
    log "  [!] system-sync-env.sh not found -- skipping BARE-SAFE-ENV render check"
fi

# 17. SECRETS-NEVER-IN-ENV (Architectural Law 11).
# Password hashes/tokens live ONLY in /etc/shadow + /etc/mios/secrets.env (0600).
# Scan every *.env / *secrets* file in the deployed config roots: if it carries one
# of the three secret NAMES (MIOS_USER_PASSWORD_HASH / MIOS_FORGE_ADMIN_PASSWORD /
# MIOS_GITHUB_TOKEN) OR a unix-crypt hash literal ($6$.../$y$...), the carrying file
# MUST be mode 0600 -- otherwise a group/world-readable file leaks a secret.
# Comment lines are stripped so a doc mention of a secret name never trips the gate.
log "Validating SECRETS-NEVER-IN-ENV (Law 11): secret-bearing env files are 0600..."
_law11_secret_re='(MIOS_USER_PASSWORD_HASH|MIOS_FORGE_ADMIN_PASSWORD|MIOS_GITHUB_TOKEN)=|[$]6[$]|[$]y[$]'
_law11_dirs=(/etc /run/secrets /usr/share/mios /usr/lib/mios /var/lib/mios)
_law11_bad=""
for d in "${_law11_dirs[@]}"; do
    [[ -d "$d" ]] || continue
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        if sed -E '/^[[:space:]]*#/d' "$f" 2>/dev/null | grep -qE "$_law11_secret_re"; then
            mode="$(stat -c '%a' "$f" 2>/dev/null || echo '???')"
            if [[ "$mode" != "600" ]]; then
                _law11_bad+="$f (mode $mode, must be 0600)"$'\n'
            fi
        fi
    done < <(find "$d" -type f \( -name '*.env' -o -name '*secrets*' \) 2>/dev/null)
done
if [[ -n "$_law11_bad" ]]; then
    printf '%s' "$_law11_bad" >&2
    die "SECRETS-NEVER-IN-ENV: a secret-bearing env file is not mode 0600 (secret leak; move it to /etc/mios/secrets.env @ 0600)"
fi
log "  [ok] every secret-bearing env file is mode 0600 (or none present)"

# 18. BOUND-IMAGES-RESOLVE (AGY-92 / B1).
# Every Quadlet (.container or .image) linked under /usr/lib/bootc/bound-images.d/
# must target a valid file, and the Image= it declares must exist in the built/baked
# image registry (/usr/share/mios/artifacts/sbom/bound-images.tsv).
log "Validating BOUND-IMAGES-RESOLVE: bound-images.d symlinks resolve to baked images..."
_lbi_dir="/usr/lib/bootc/bound-images.d"
_lbi_tsv="/usr/share/mios/artifacts/sbom/bound-images.tsv"
if [[ -d "$_lbi_dir" ]]; then
    declare -A _lbi_baked=()
    if [[ -f "$_lbi_tsv" ]]; then
        while IFS=$'\t' read -r img_ref digest group || [[ -n "$img_ref" ]]; do
            [[ -z "$img_ref" || "$img_ref" == "image" ]] && continue
            _lbi_baked["$img_ref"]=1
        done < "$_lbi_tsv"
    fi
    # Local base images are always valid
    _lbi_baked["localhost/mios-sys:latest"]=1
    _lbi_baked["localhost/mios-cuda:latest"]=1

    while IFS= read -r link || [[ -n "$link" ]]; do
        [[ -L "$link" ]] || continue
        target="$(readlink -f "$link")"
        if [[ ! -f "$target" ]]; then
            die "BOUND-IMAGES-RESOLVE: symlink $(basename "$link") points to nonexistent file: $target"
        fi
        img_line="$(grep -i '^[[:space:]]*Image=' "$target" | head -n1 || true)"
        if [[ -n "$img_line" ]]; then
            raw_ref="${img_line#*=}"
            raw_ref="${raw_ref%%#*}"
            raw_ref="$(echo "$raw_ref" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
            resolved_ref="$raw_ref"
            if [[ "$raw_ref" =~ \$\{[A-Za-z0-9_]+:-(.+)\} ]]; then
                resolved_ref="${BASH_REMATCH[1]}"
            elif [[ "$raw_ref" =~ \$\{[A-Za-z0-9_]+\} ]]; then
                var_name="${raw_ref:2:${#raw_ref}-3}"
                resolved_ref="${!var_name:-}"
            elif [[ "$raw_ref" =~ \$[A-Za-z0-9_]+ ]]; then
                var_name="${raw_ref:1}"
                resolved_ref="${!var_name:-}"
            fi
            resolved_ref="${resolved_ref//\"/}"
            resolved_ref="${resolved_ref//\'/}"
            [[ -z "$resolved_ref" ]] && continue
            if [[ "$resolved_ref" != "localhost/mios"* && -z "${_lbi_baked[$resolved_ref]:-}" ]]; then
                die "BOUND-IMAGES-RESOLVE: Image '$resolved_ref' (declared in $target) was not baked. Check your bake plan or plan.d groups."
            fi
        fi
    done < <(find "$_lbi_dir" -type l 2>/dev/null)
    log "  [ok] every bound-images.d symlink resolves to a baked image"
fi

log "Validation SUCCESSFUL"
exit 0
