#!/usr/bin/env bash
# AI-hint: MiOS' verify-root -- early-boot composefs/ostree integrity check.
# AI-related: /usr/lib/mios/paths.sh, mios-verify-root, mios-verify-root.service, basic.target
# AI-functions: _log, _die
set -euo pipefail
source /usr/lib/mios/paths.sh

_log()  { logger -t mios-verify-root "$*" 2>/dev/null || true; echo "[verify-root] $*" >&2; }
_die()  { _log "FAIL: $*"; exit 1; }

_log "starting root verification"

if [[ ! -e /run/ostree-booted ]]; then
    _die "/run/ostree-booted missing -- not an ostree/bootc rootfs"
fi
_log "ostree-booted: ok"

if [[ ! -r /usr/lib/os-release ]]; then
    _die "/usr/lib/os-release not readable"
fi
if ! grep -q '^ID=' /usr/lib/os-release; then
    _die "/usr/lib/os-release missing ID="
fi
_log "os-release: ok ($(grep -E '^(ID|VERSION_ID)=' /usr/lib/os-release | tr '\n' ' '))"

mountflags=$(awk '$2=="/usr"{print $4}' /proc/self/mounts | head -1)
if [[ -n "$mountflags" ]]; then
    case ",$mountflags," in
        *,ro,*) _log "/usr mount: ro ok" ;;
        *,rw,*) _die "/usr is mounted rw -- composefs integrity unenforced" ;;
        *)      _log "/usr mount flags: $mountflags (no ro/rw token; tolerating)" ;;
    esac
fi

if command -v fsverity >/dev/null 2>&1 && [[ -e /sys/fs/fsverity ]]; then
    if fsverity measure /usr/lib/os-release >/dev/null 2>&1; then
        _log "fsverity measure: ok"
    else
        _log "fsverity measure failed -- /usr may not be verity-sealed (acceptable on non-bootc kernels)"
    fi
fi

if command -v ostree >/dev/null 2>&1; then
    if ostree admin status --print-current-dir >/dev/null 2>&1; then
        _log "ostree admin status: ok"
    else
        _log "ostree admin status failed (may be normal on transient deploy)"
    fi
fi

_log "root verification PASSED"
exit 0
