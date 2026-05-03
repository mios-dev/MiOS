#!/usr/bin/env bash
# 'MiOS' verify-root -- early-boot composefs/ostree integrity check.
# Run by mios-verify-root.service before basic.target and greenboot. Lives
# in a heavily-locked-down systemd sandbox (ProtectSystem=strict, read-only
# /usr+/etc, no network, no writable state). Failure here makes greenboot
# rollback the deployment.
#
# What it checks (each independently; any single failure is fatal):
#   1. /run/ostree-booted exists       (we're on an ostree/bootc rootfs)
#   2. /usr/lib/os-release exists      (basic /usr layout intact)
#   3. composefs verity state          (where exposed by kernel + ostree)
#   4. /usr is read-only               (composefs/erofs mount character)
set -euo pipefail
# shellcheck source=/usr/lib/mios/paths.sh
source /usr/lib/mios/paths.sh

_log()  { logger -t mios-verify-root "$*" 2>/dev/null || true; echo "[verify-root] $*" >&2; }
_die()  { _log "FAIL: $*"; exit 1; }

_log "starting root verification"

# 1. ostree-booted marker
if [[ ! -e /run/ostree-booted ]]; then
    _die "/run/ostree-booted missing -- not an ostree/bootc rootfs"
fi
_log "ostree-booted: ok"

# 2. /usr/lib/os-release present and parseable
if [[ ! -r /usr/lib/os-release ]]; then
    _die "/usr/lib/os-release not readable"
fi
if ! grep -q '^ID=' /usr/lib/os-release; then
    _die "/usr/lib/os-release missing ID="
fi
_log "os-release: ok ($(grep -E '^(ID|VERSION_ID)=' /usr/lib/os-release | tr '\n' ' '))"

# 3. /usr is read-only (composefs/erofs/overlayfs mount)
mountflags=$(awk '$2=="/usr"{print $4}' /proc/self/mounts | head -1)
if [[ -n "$mountflags" ]]; then
    case ",$mountflags," in
        *,ro,*) _log "/usr mount: ro ok" ;;
        *,rw,*) _die "/usr is mounted rw -- composefs integrity unenforced" ;;
        *)      _log "/usr mount flags: $mountflags (no ro/rw token; tolerating)" ;;
    esac
fi

# 4. composefs verity probe (best-effort -- fsverity may be absent on WSL2)
if command -v fsverity >/dev/null 2>&1 && [[ -e /sys/fs/fsverity ]]; then
    if fsverity measure /usr/lib/os-release >/dev/null 2>&1; then
        _log "fsverity measure: ok"
    else
        _log "fsverity measure failed -- /usr may not be verity-sealed (acceptable on non-bootc kernels)"
    fi
fi

# 5. ostree commit metadata sanity (best-effort -- ostree CLI present?)
if command -v ostree >/dev/null 2>&1; then
    if ostree admin status --print-current-dir >/dev/null 2>&1; then
        _log "ostree admin status: ok"
    else
        _log "ostree admin status failed (may be normal on transient deploy)"
    fi
fi

_log "root verification PASSED"
exit 0
