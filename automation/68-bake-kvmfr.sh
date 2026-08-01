#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Builds, signs, and embeds the Looking Glass kvmfr kernel module into the image during the container build process to enable high-performance KVMFR support for the guest.
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

source "$(dirname "$0")/lib/common.sh"

KVER="$(find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" 2>/dev/null | sort -V | tail -1)"
if [[ -z "$KVER" ]]; then
    mios_warn "no kernel modules directory; cannot determine kernel version"
    mios_skip "kvmfr bake - Looking Glass runs IVSHMEM-only mode"
    exit 0
fi
mios_log "Building against kernel: $KVER"

if [[ ! -d "/usr/src/kernels/$KVER" ]]; then
    mios_log "Installing kernel-devel-$KVER"
    set +e
    $DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" "kernel-devel-$KVER" >/dev/null 2>&1
    RC=$?
    set -e
    if [[ $RC -ne 0 ]]; then
        set +e
        AVAIL="$(rpm -qa 'kernel-devel*' 2>/dev/null | tr '\n' ' ')"
        set -e
        mios_skip "no exact kernel-devel for $KVER (dnf rc=$RC; installed: ${AVAIL:-none})"
        mios_warn "The ucore-hci base kernel $KVER is typically newer/older than"
        mios_warn "F44's repo-published kernel-devel. Project principle is 'never"
        mios_warn "upgrade base kernel in-container', so kvmfr is skipped here."
        mios_warn "Looking Glass still works in IVSHMEM-only mode. To enable kvmfr"
        mios_warn "on the booted image once the kernel matches, run:"
        mios_warn "  sudo dnf install kernel-devel-\$(uname -r) akmod-kvmfr"
        mios_warn "  sudo akmods --force --kernels \$(uname -r)"
        exit 0
    fi
fi

mios_log "Enabling hikariknight/looking-glass-kvmfr COPR"
set +e
$DNF_BIN "${DNF_SETOPT[@]}" copr enable -y hikariknight/looking-glass-kvmfr 2>/dev/null
set -e

mios_log "Installing akmod-kvmfr"
set +e
$DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" akmod-kvmfr >/dev/null 2>&1
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
    mios_skip "akmod-kvmfr install failed (rc=$RC; COPR unreachable or package missing)"
    mios_warn "verify COPR enabled: dnf5 copr list | grep looking-glass-kvmfr"
    exit 0
fi

mios_log "Akmods"
set +e
akmods --force --kernels "$KVER" 2>&1 | sed 's/^/[akmods] /'
RC=${PIPESTATUS[0]}
set -e
if [[ $RC -ne 0 ]]; then
    mios_skip "akmods build failed (rc=$RC)"
    mios_warn "checking /var/cache/akmods/kvmfr/ for build log"
    find /var/cache/akmods/ -name '*.log' -exec tail -50 {} \; 2>/dev/null || true
    exit 0
fi

KMOD_PATH="/usr/lib/modules/$KVER/extra/kvmfr/kvmfr.ko"
if [[ -f "$KMOD_PATH" ]] || [[ -f "${KMOD_PATH}.xz" ]] || [[ -f "${KMOD_PATH}.zst" ]]; then
    mios_ok "kvmfr.ko baked at /usr/lib/modules/$KVER/extra/kvmfr/"
    ls -la "/usr/lib/modules/$KVER/extra/kvmfr/"
else
    mios_skip "kvmfr.ko not found after akmods build"
    mios_warn "listing /usr/lib/modules/$KVER/extra/:"
    ls -la "/usr/lib/modules/$KVER/extra/" 2>/dev/null || mios_warn "no extra/ dir"
    exit 0
fi

mios_log "Depmod -a -b /usr $KVER"
depmod -a -b /usr "$KVER" || mios_warn "depmod failed (non-fatal)"

PRIV_KEY="/etc/pki/akmods/private/private_key.priv"
PUB_KEY="/etc/pki/akmods/certs/public_key.der"
if [[ -f "$PRIV_KEY" && -f "$PUB_KEY" ]]; then
    mios_log "Signing kvmfr.ko with akmods private key"
    SIGN_FILE="/usr/src/kernels/$KVER/automation/sign-file"
    if [[ -x "$SIGN_FILE" ]]; then
        for ko in /usr/lib/modules/$KVER/extra/kvmfr/*.ko; do
            [[ -f "$ko" ]] && "$SIGN_FILE" sha256 "$PRIV_KEY" "$PUB_KEY" "$ko" && \
                mios_ok "signed: $ko"
        done
    else
        mios_warn "sign-file not found at $SIGN_FILE; kvmfr unsigned"
    fi
else
    mios_log "Ublue MOK private key not in image; users enroll MOK"
    mios_log "Kvmfr will use the public cert shipped by ublue-os-akmods-addons"
fi

mios_ok "kvmfr.ko installed under /usr/lib/modules/$KVER/extra/kvmfr/"
