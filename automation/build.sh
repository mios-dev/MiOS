#!/bin/bash
# MiOS v0.1.1 — Master build runner
# Executes all numbered scripts in order, then cleans up.
# Called from Containerfile RUN layer via bind mount.
#
# CHANGELOG v0.1.1:
#   - Standardized versioning across the entire stack.
#   - FIX: install_weakdeps=False (was True in v1.3 — contradicted docs)
#   - FIX: Safe arithmetic: VAR=$((VAR + 1)) not ((VAR++)) (set -e compat)
#   - Base: ucore-hci:stable-nvidia (Rawhide overlay in 01-repos.sh)
#   - Post-build validates malcontent-libs present (flatpak needs it)
#   - Footgun list includes malcontent-control/pam/tools
#   - PackageKit/gnome-tour removed via dnf (safe, no cascade)
#   - gnome-software KEPT (manages Flatpaks on immutable systems)
#   - malcontent-control hidden via NoDisplay (dnf remove cascades)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
register_common_masks
export PACKAGES_MD="${PACKAGES_MD:-/ctx/PACKAGES.md}"
BUILD_LOG="/tmp/mios-build.log"

exec > >(mask_filter | tee -a "$BUILD_LOG") 2>&1

log_ts() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

VERSION_STR="$(cat "${SCRIPT_DIR}/../VERSION" 2>/dev/null || cat /ctx/VERSION 2>/dev/null || echo 'v0.1.1')"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MiOS v${VERSION_STR} — Building OS Image"
echo "  Base: ucore-hci:stable-nvidia + F44 + Rawhide kernel"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
log_ts "Build started"
log_ts "PACKAGES.MD : $PACKAGES_MD"
log_ts "SCRIPT_DIR  : $SCRIPT_DIR"
echo ""

if [[ ! -f "$PACKAGES_MD" ]]; then
    log_ts "FATAL: $PACKAGES_MD not found. Build context missing."
    exit 1
fi

# ── DNF config ──────────────────────────────────────────────────────────────
export SYSTEMD_OFFLINE=1
export container=podman

# ── Execute numbered scripts ────────────────────────────────────────────────
# Scripts 18/19/20-fapolicyd/21/22 are called explicitly by the Containerfile
# AFTER this script completes. Skip them here to prevent double-execution.
CONTAINERFILE_SCRIPTS="08-system-files-overlay.sh 18-apply-boot-fixes.sh 19-k3s-selinux.sh 20-fapolicyd-trust.sh 21-moby-engine.sh 22-freeipa-client.sh 23-uki-render.sh 25-firewall-ports.sh 26-gnome-remote-desktop.sh 37-ollama-prep.sh"

TOTAL_START=$SECONDS
SCRIPT_COUNT=0
SCRIPT_FAIL=0
FAILED_SCRIPTS=()

for script in "$SCRIPT_DIR"/[0-9][0-9]-*.sh; do
    SCRIPT_NAME="$(basename "$script")"
    if echo "$CONTAINERFILE_SCRIPTS" | grep -qF "$SCRIPT_NAME"; then
        log_ts "==> Skipping (Containerfile post-step): $SCRIPT_NAME"
        continue
    fi
    SCRIPT_COUNT=$((SCRIPT_COUNT + 1))
    echo "───────────────────────────────────────────────────────────────────"
    log_ts "==> STEP $SCRIPT_COUNT: $SCRIPT_NAME"
    echo "───────────────────────────────────────────────────────────────────"

    STEP_START=$SECONDS

    set +e
    bash "$script"
    SCRIPT_EXIT=$?
    set -e

    STEP_ELAPSED=$(( SECONDS - STEP_START ))

    if [[ $SCRIPT_EXIT -eq 0 ]]; then
        log_ts "✓ $SCRIPT_NAME completed (${STEP_ELAPSED}s)"
    else
        log_ts "✗ $SCRIPT_NAME FAILED (exit $SCRIPT_EXIT, ${STEP_ELAPSED}s)"
        SCRIPT_FAIL=$((SCRIPT_FAIL + 1))
        FAILED_SCRIPTS+=("$SCRIPT_NAME")
    fi
    echo ""
done

# ── Bloat Removal (active removal approach) ──────────
# Per user mandate: remove anything that's bloat.
# malcontent-libs must remain (gnome-control-center hard dep), but
# malcontent-control/pam/tools are UI/CLI components we don't need.
# Leaf apps like gnome-tour and gnome-initial-setup are safe to remove.
echo ""
log_ts "==> Removing known bloat packages..."
BLOAT_PACKAGES=$(source "${SCRIPT_DIR}/lib/packages.sh"; get_packages "bloat")
if [[ -n "$BLOAT_PACKAGES" ]]; then
    $DNF_BIN "${DNF_SETOPT[@]}" remove -y "${DNF_OPTS[@]}" $BLOAT_PACKAGES 2>/dev/null || true
else
    log_ts "NOTE: No bloat packages defined in manifest."
fi

# ── Suppress remaining ucore base bloat (mask/hide) ──────────
# For things that can't be easily removed without cascade, hide them.
echo ""
log_ts "==> Suppressing remaining base image bloat (mask/hide)..."
systemctl mask packagekit.service 2>/dev/null || true
for app in gnome-tour gnome-initial-setup; do
    desktop="/usr/share/applications/${app}.desktop"
    if [ -f "$desktop" ]; then
        # Ensure target directory exists for NoDisplay override
        mkdir -p /usr/local/share/applications
        grep -v '^NoDisplay=' "$desktop" > "/usr/local/share/applications/${app}.desktop"
        echo "NoDisplay=true" >> "/usr/local/share/applications/${app}.desktop"
        echo "  ✓ Hidden: $app (NoDisplay=true)"
    fi
done

# ── Post-build validation ──────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_ts "Post-build validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

source "${SCRIPT_DIR}/lib/packages.sh"
CRITICAL_PACKAGES=($(get_packages "critical"))
VALIDATION_FAIL=0
if [[ ${#CRITICAL_PACKAGES[@]} -eq 0 ]]; then
    log_ts "WARNING: No critical packages found in manifest validation section!"
else
    for pkg in "${CRITICAL_PACKAGES[@]}"; do
        if rpm -q "$pkg" > /dev/null 2>&1; then
            echo "  ✓ $pkg"
        else
            echo "  ✗ $pkg MISSING"
            VALIDATION_FAIL=$((VALIDATION_FAIL + 1))
        fi
    done
fi

# Hardware & Driver Verification (Moved from legacy 41-akmods-copy.sh)
if rpm -qa 'kmod-nvidia*' 2>/dev/null | grep -q . ; then
    echo "  ✓ NVIDIA kmod(s) present"
else
    echo "  ⚠ NVIDIA kmod(s) MISSING (using ucore base?)"
fi

if compgen -G "/etc/pki/akmods/certs/*.der" > /dev/null; then
    echo "  ✓ MOK certs present"
fi

# RTX 50 Blackwell Karg Check
if grep -q "vfio_pci.disable_idle_d3=1" /usr/lib/bootc/kargs.d/*.toml 2>/dev/null; then
    echo "  ✓ Blackwell VFIO workaround present in kargs.d"
else
    echo "  ⚠ Blackwell VFIO workaround missing in kargs.d"
fi

# malcontent-libs MUST be present (flatpak links against libmalcontent-0.so.0)
if rpm -q malcontent-libs > /dev/null 2>&1; then
    echo "  ✓ malcontent-libs (required by flatpak)"
else
    echo "  ⚠ malcontent-libs MISSING — flatpak may break"
fi

# gnome-software: expected (manages Flatpaks on immutable systems)
if rpm -q gnome-software > /dev/null 2>&1; then
    echo "  ✓ gnome-software (Flatpak manager)"
fi

# Footgun check — these should NOT be present after bloat removal
FOOTGUN_PACKAGES=($(get_packages "bloat"))
for pkg in "${FOOTGUN_PACKAGES[@]}"; do
    if rpm -q "$pkg" > /dev/null 2>&1; then
        echo "  ⚠ FOOTGUN: $pkg is installed (should not be in build-up image)"
    fi
done

if [[ $VALIDATION_FAIL -gt 0 ]]; then
    log_ts "WARNING: $VALIDATION_FAIL critical packages missing!"
fi

# ── Technical Invariant Validation ──
echo ""
log_ts "==> Running Technical Invariant Validation (99-postcheck.sh)..."
if [[ -f "${SCRIPT_DIR}/99-postcheck.sh" ]]; then
    bash "${SCRIPT_DIR}/99-postcheck.sh"
else
    log_ts "⚠ automation/99-postcheck.sh not found — skipping"
fi

# ── Cleanup ─────────────────────────────────────────────────────────────────

# Preserve logs in an immutable path for Day-2 diagnostics
echo ""
log_ts "Preserving build logs to /usr/lib/mios/logs/..."
mkdir -p /usr/lib/mios/logs
cp -v /var/log/dnf5.log* /var/log/hawkey.log /tmp/mios-build.log /usr/lib/mios/logs/ 2>/dev/null || true

echo ""
log_ts "Cleaning up..."
$DNF_BIN "${DNF_SETOPT[@]}" clean all
rm -rf /var/cache/dnf /var/cache/libdnf5 /tmp/geist-font /tmp/*.tar* /tmp/*.rpm 2>/dev/null || true
rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/* 2>/dev/null || true
rm -rf /usr/share/gnome/help/* /usr/share/help/* 2>/dev/null || true

# Clean bootc lint triggers (logs now preserved in /usr/lib/mios/logs)
rm -f /var/log/dnf5.log* /var/log/hawkey.log 2>/dev/null || true
rm -rf /run/ceph /run/cockpit /run/k3s /tmp/* 2>/dev/null || true
rm -f /var/lib/systemd/random-seed 2>/dev/null || true

rm -f /tmp/mios-build.log

# ── Summary ─────────────────────────────────────────────────────────────────
TOTAL_ELAPSED=$(( SECONDS - TOTAL_START ))
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  BUILD SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Scripts:   $SCRIPT_COUNT executed, $SCRIPT_FAIL failed"
if [[ $SCRIPT_FAIL -gt 0 ]]; then
    echo "  Failed:    ${FAILED_SCRIPTS[*]}"
fi
echo "  Packages:  $VALIDATION_FAIL critical missing"
echo "  Duration:  ${TOTAL_ELAPSED}s ($((TOTAL_ELAPSED / 60))m $((TOTAL_ELAPSED % 60))s)"
echo "  Version:   v$VERSION_STR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ $SCRIPT_FAIL -gt 0 ]]; then
    log_ts "FATAL: $SCRIPT_FAIL scripts failed — review build output above"
    exit 1
fi
