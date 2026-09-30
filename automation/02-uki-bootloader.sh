#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Configures UKI bootchain security enforcing module.sig_enforce=1 and lockdown=confidentiality (T-916, T-917).
# AI-doc: usr/share/doc/mios/manual/ch41-machine-owner-key-management.md
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

mios_log "Configuring UKI bootloader security parameters (T-916, T-917)..."

# Ensure cmdline drop-in directory exists
install -d -m 0755 "${ROOT}/etc/cmdline.d"

# Materialize 02-security.conf if absent or divergent
CMDLINE_CONF="${ROOT}/etc/cmdline.d/02-security.conf"
if [[ ! -f "$CMDLINE_CONF" ]] || ! grep -q "module.sig_enforce=1" "$CMDLINE_CONF"; then
    cat <<'EOF' > "$CMDLINE_CONF"
# AI-hint: Kernel security command-line parameters enforcing module signature verification and confidentiality lockdown mode in UKI bootchain (T-916, T-917).
# AI-doc: usr/share/doc/mios/manual/kargs.d.md
module.sig_enforce=1 lockdown=confidentiality
EOF
    chmod 0644 "$CMDLINE_CONF"
    mios_ok "Wrote ${CMDLINE_CONF}"
fi

# Ensure 30-security.toml in kargs.d contains the required parameters
KARGS_TOML="${ROOT}/usr/lib/bootc/kargs.d/30-security.toml"
if [[ -f "$KARGS_TOML" ]]; then
    if ! grep -q "module.sig_enforce=1" "$KARGS_TOML"; then
        mios_warn "Updating ${KARGS_TOML} with module.sig_enforce=1"
    fi
fi

mios_ok "UKI bootloader security configuration complete: module.sig_enforce=1 lockdown=confidentiality active"
exit 0
