#!/usr/bin/env bash
# 40-composefs-verity.sh -- render /usr/lib/ostree/prepare-root.conf based
# on the operator-tunable [security].composefs_mode knob in mios.toml.
#
# SSOT: usr/share/mios/mios.toml [security].composefs_mode
#       (resolved through the documented overlay chain by lib/packages.sh
#        + this script's local _read_mios_scalar awk helper).
#
# Modes:
#   verity  -- composefs in fs-verity mode (tamper-evident root). Default.
#              Requires ext4 or btrfs. Also masks systemd-remount-fs.service
#              (known-broken on Fedora 42+ with composefs) when
#              [security].mask_systemd_remount_fs = true.
#   yes     -- composefs enabled without verity. Works on XFS too.
#   off     -- skip prepare-root.conf rewrite entirely; honor base image.
#
# See usr/share/mios/mios.toml [security] prose for the full rationale.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=lib/packages.sh
# Pulled in for _resolve_mios_toml; the same TOML overlay chain that
# packages.sh uses is what we want for [security] too.
source "${SCRIPT_DIR}/lib/packages.sh"

# _read_mios_scalar <table> <key> -- read a top-level scalar from the
# [<table>] block of the resolved mios.toml. Strips quotes and inline
# comments. Returns empty string when the key is absent.
_read_mios_scalar() {
    local table="$1" key="$2" toml_path
    toml_path="$(_resolve_mios_toml 2>/dev/null || true)"
    [[ -n "$toml_path" && -f "$toml_path" ]] || return 0
    awk -v table="$table" -v key="$key" '
        /^\[/ {
            in_section = 0
            line = $0
            sub(/^\[/, "", line); sub(/\][[:space:]]*$/, "", line)
            gsub(/[[:space:]]/, "", line)
            if (line == table) in_section = 1
            next
        }
        in_section {
            if (match($0, "^[[:space:]]*" key "[[:space:]]*=")) {
                value = $0
                sub(/^[^=]*=[[:space:]]*/, "", value)
                sub(/[[:space:]]*#.*$/, "", value)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
                gsub(/^"|"$/, "", value)
                print value
                exit 0
            }
        }
    ' "$toml_path"
}

MODE="$(_read_mios_scalar security composefs_mode)"
MODE="${MODE:-verity}"
MASK_REMOUNT="$(_read_mios_scalar security mask_systemd_remount_fs)"
MASK_REMOUNT="${MASK_REMOUNT:-true}"

case "$MODE" in
    verity|yes|off) ;;
    *)
        warn "[40-composefs-verity] unknown composefs_mode='${MODE}', falling back to 'verity'"
        MODE="verity"
        ;;
esac

if [[ "$MODE" == "off" ]]; then
    log "[40-composefs-verity] composefs_mode=off -- honoring base image's prepare-root.conf"
    exit 0
fi

conf=/usr/lib/ostree/prepare-root.conf
if [[ -f "$conf" ]]; then
    log "[40-composefs-verity] backing up existing $conf -> ${conf}.orig"
    cp -a "$conf" "${conf}.orig"
fi

# Render the table according to the requested mode. The [root] / [etc]
# transient = false stanzas are independent of verity vs yes -- they
# enforce immutable / non-tmpfs root and /etc on every composefs path.
log "[40-composefs-verity] writing $conf with composefs mode=${MODE}"
case "$MODE" in
    verity)
        cat > "$conf" <<'EOF'
# 'MiOS': composefs in verity mode. Tamper-evident root.
# Target filesystems must support fsverity (ext4, btrfs). XFS is NOT supported.
# SSOT: mios.toml [security].composefs_mode = "verity".
[composefs]
enabled = verity

[root]
transient = false

[etc]
transient = false
EOF
        ;;
    yes)
        cat > "$conf" <<'EOF'
# 'MiOS': composefs enabled (no verity). Read-only /usr without the
# fs-verity cryptographic chain -- works on every composefs-capable
# filesystem (ext4, btrfs, XFS). Default upstream FCOS / bootc posture.
# SSOT: mios.toml [security].composefs_mode = "yes".
[composefs]
enabled = yes

[root]
transient = false

[etc]
transient = false
EOF
        ;;
esac

# systemd-remount-fs masking: only relevant in verity mode (where the
# composefs/remount-fs interop bug surfaces). The "yes" path uses the
# upstream-default mount sequence and does not need the mask.
if [[ "$MODE" == "verity" && "$MASK_REMOUNT" =~ ^(true|TRUE|1|yes|YES)$ ]]; then
    log "[40-composefs-verity] masking systemd-remount-fs.service (composefs/remount interop bug)"
    install -d -m 0755 /etc/systemd/system
    ln -sf /dev/null /etc/systemd/system/systemd-remount-fs.service
fi

log "[40-composefs-verity] composefs mode=${MODE} configured"
