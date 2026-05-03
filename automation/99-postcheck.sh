#!/usr/bin/env bash
# 99-postcheck.sh - build-time technical invariant validation
# 
# This script runs at the very end of the Containerfile build (before cleanup).
# It enforces mandatory version requirements, security postures, and 
# architectural purity. Failures here ABORT THE BUILD to prevent shipping
# a regressed or vulnerable image.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "'MiOS' build-time validation"

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
log "  ✓ OpenSSH version is safe"

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
    log "  ✓ Cockpit LoginTo = false is enforced"
else
    log "  ⚠ Cockpit config not found at expected paths; skipping check"
fi

# 3. Kernel Argument Validation (Schema Strictness Preparation)
log "Validating kargs.d files..."
if [[ -d /usr/lib/bootc/kargs.d ]]; then
    for f in /usr/lib/bootc/kargs.d/*; do
        [[ -e "$f" ]] || continue
        # Future: run 'bootc container lint' or specialized schema check
        log "  found karg: $(basename "$f")"
    done
    log "  ✓ kargs.d presence verified"
fi

# 4. Critical Package Verification
log "Verifying critical system binaries..."
CRITICAL_TOOLS=(podman bootc cockpit-bridge rpm-ostree)
for tool in "${CRITICAL_TOOLS[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        die "Critical tool '$tool' is missing from the image"
    fi
    log "  ✓ $tool present"
done

# 5. NVIDIA Container Toolkit Version Check
log "Checking NVIDIA Container Toolkit version..."
if command -v nvidia-ctk >/dev/null 2>&1; then
    NCT_VER=$(nvidia-ctk --version | head -n1 | grep -oP 'version \K[0-9.]+')
    log "  Found: $NCT_VER"
    if [[ $(printf '%s\n1.18' "$NCT_VER" | sort -V | head -n1) != "1.18" ]]; then
        die "nvidia-container-toolkit version $NCT_VER is below required 1.18"
    fi
    log "  ✓ NVIDIA Container Toolkit version is safe"
fi

# 6. Cockpit Version Check (for CVE-2026-4631)
log "Checking Cockpit version..."
if rpm -q cockpit >/dev/null 2>&1; then
    COCKPIT_VER=$(rpm -q cockpit --queryformat '%{VERSION}')
    log "  Found: Cockpit $COCKPIT_VER"
    # CVE fixed in 360. 'MiOS' targets 361+ for Fedora 44 GA stability.
    if [[ $(printf '%s\n361' "$COCKPIT_VER" | sort -V | head -n1) != "361" ]]; then
        log "  ⚠ Cockpit version $COCKPIT_VER is below 361 (Risk: CVE-2026-4631 / Regressions)"
    else
        log "  ✓ Cockpit version is safe"
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
    # WSL2's INI parser is byte-naive — multibyte chars (em-dashes, smart quotes,
    # NBSP) shift its line counter and surface as bogus "Expected ' ' or '\n' in
    # /etc/wsl.conf:N" errors at boot. Python configparser tolerates UTF-8 so a
    # parse-only check misses these. Enforce strict ASCII before the parse runs.
    if LC_ALL=C grep -nP '[^\x00-\x7F]' /etc/wsl.conf >&2; then
        die "/etc/wsl.conf contains non-ASCII bytes (WSL2's parser will choke)"
    fi
    log "  pure ASCII"
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
        log "  ⚠ python3 unavailable — skipping wsl.conf parse (post-build only)"
    fi
    if [[ -f /usr/lib/wsl.conf ]]; then
        if ! cmp -s /etc/wsl.conf /usr/lib/wsl.conf; then
            die "/etc/wsl.conf drifted from /usr/lib/wsl.conf reference at build time"
        fi
        log "  ✓ /etc/wsl.conf matches /usr/lib/wsl.conf reference"
    fi
else
    log "  ⚠ /etc/wsl.conf not present in image — WSL2 deploys will fall back to defaults"
fi

# 8. sysusers.d sanity — login-shell users MUST have a fixed UID.
# Auto-allocation ('-') picks from the SYSTEM range (<UID_MIN), and logind
# then refuses to create /run/user/<uid>/. The cascade kills dbus user
# session, dconf, Wayland session services, and every GTK app that needs
# a session bus.
#
# Files in /etc/sysusers.d/ override files of the same basename in
# /usr/lib/sysusers.d/ (systemd-sysusers.d(5)), so when an override exists
# the /usr/lib/ file is shadowed at runtime — validate the effective file.
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

# 8b. sysusers.d: every `u user UID:NUM` must be preceded by a `g name NUM`
# line in the same file (or use a name reference instead of NUM). If the
# numeric GID is unresolvable, sysusers fails with "please create GID NUM"
# at first boot and the user never gets created.
log "Validating sysusers.d UID:GID resolves to a created group..."
_sysusers_unresolved=$(
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        awk '
            # collect g lines in this file
            /^g[[:space:]]+/ {
                # 2nd field = group name, 3rd = id (or "-")
                groups[$2] = 1
                if ($3 ~ /^[0-9]+$/) gids[$3] = $2
            }
            /^u[[:space:]]+/ {
                # 3rd field is UID:GID. Split on colon.
                split($3, a, ":")
                # If GID part is numeric and no g line in this file claims it, flag.
                if (a[2] ~ /^[0-9]+$/ && !(a[2] in gids)) {
                    print FILENAME ":" NR ": " $0
                }
            }' "$f"
    done < <(_sysusers_effective)
)
if [[ -n "$_sysusers_unresolved" ]]; then
    printf '%s\n' "$_sysusers_unresolved" >&2
    die "sysusers.d: u-line references a numeric GID with no matching 'g name GID' line in the same file"
fi
log "  all u-line GIDs resolve to created groups"

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
log "Validating MiOS tmpfiles.d syntax..."
if command -v systemd-tmpfiles >/dev/null 2>&1; then
    _bad_tmpfiles=$(
        for f in /usr/lib/tmpfiles.d/mios-*.conf; do
            [[ -f "$f" ]] || continue
            # --dry-run alone reports parse errors; combine with --create
            # (also dry-run) so it exercises the full directive interpreter.
            out=$(systemd-tmpfiles --dry-run --create "$f" 2>&1 || true)
            echo "$out" | grep -E "^${f}:" || true
        done
    )
    if [[ -n "$_bad_tmpfiles" ]]; then
        printf '%s\n' "$_bad_tmpfiles" >&2
        die "systemd-tmpfiles reported errors in MiOS tmpfiles.d config(s)"
    fi
    log "  MiOS tmpfiles.d configs parse clean"
else
    log "  systemd-tmpfiles unavailable -- skipping tmpfiles verification"
fi

log "Validation SUCCESSFUL"
exit 0
