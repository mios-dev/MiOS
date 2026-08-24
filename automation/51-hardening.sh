#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Enables and symlinks security services (usbguard, auditd, fapolicyd) into the multi-user.target.wants directory and pr...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

chmod 0600 /usr/lib/usbguard/usbguard-daemon.conf 2>/dev/null || true

if command -v miosd >/dev/null 2>&1; then
    miosd harden
    mios_ok "Hardening services enabled via miosd"
else
    WANTS=/usr/lib/systemd/system/multi-user.target.wants
    install -d -m 0755 "${WANTS}"

    mios_log "Enable hardening services"
    for unit in \
        usbguard.service \
        auditd.service \
        fapolicyd.service
    do
        if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
            ln -sf "../${unit}" "${WANTS}/${unit}"
            mios_ok "Enabled ${unit}"
        else
            mios_skip "${unit} not installed"
        fi
    done
fi

if command -v fagenrules &>/dev/null; then
    mios_log "Pre-generate fapolicyd trust database"
    chown -R fapolicyd:fapolicyd /etc/fapolicyd 2>/dev/null || true
    fagenrules --load 2>/dev/null || true
    fapolicyd-cli --update 2>/dev/null || true
fi

mios_ok "Hardening services wired"
# Install the committed [security.luks] projection, never re-derive it, so /etc
# carries exactly the bytes check_clevis_luks diffed.
_clevis_env="$(dirname "${BASH_SOURCE[0]}")/../etc/mios/clevis-luks.env"
[[ -f "${_clevis_env}" ]] || { mios_err "clevis-luks.env absent: ${_clevis_env}"; exit 1; }
install -D -m 0644 "${_clevis_env}" /etc/mios/clevis-luks.env
mios_ok "Installed the committed clevis-luks.env projection"
