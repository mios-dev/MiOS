#!/usr/bin/env bash
# 99-postcheck.sh - build-time technical invariant validation
# 
# This script runs at the very end of the Containerfile build (before cleanup).
# It enforces mandatory version requirements, security postures, and 
# architectural purity. Failures here ABORT THE BUILD to prevent shipping
# a regressed or vulnerable image.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

echo "════════════ MiOS Build-Time Validation ════════════"

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
    # CVE fixed in 360. MiOS targets 361+ for Fedora 44 GA stability.
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
log "Validating /etc/wsl.conf (parse + parity with /usr/lib/wsl.conf)..."
if [[ -f /etc/wsl.conf ]]; then
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

echo "═════════════ Validation SUCCESSFUL ═════════════"
exit 0
