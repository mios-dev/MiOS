#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs FreeIPA and SSSD packages and enables the mios-freeipa-enroll.service; use this script to provision iden...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Installing FreeIPA & SSSD for zero-touch enrollment"

source "$(dirname "$0")/lib/packages.sh"

install_packages "freeipa"

mios_log "Verifying SSSD file capabilities"
SSSD_CAP_BINS=(
    /usr/libexec/sssd/krb5_child
    /usr/libexec/sssd/ldap_child
    /usr/libexec/sssd/selinux_child
    /usr/lib/sssd/sssd_pam
)
CAP_FAIL=0
for bin in "${SSSD_CAP_BINS[@]}"; do
    [[ -f "$bin" ]] || continue
    caps=$(getcap "$bin" 2>/dev/null || true)
    if [[ -z "$caps" ]]; then
        mios_err "$bin missing file capabilities (bz 2320133 regression)"
        CAP_FAIL=$((CAP_FAIL + 1))
    fi
done
if (( CAP_FAIL > 0 )); then
    mios_warn "${CAP_FAIL} SSSD binary lost file capabilities"
fi

_ipa_root="$(cd "$(dirname "$0")/.." && pwd)"
mios_log "Rendering /etc/mios/ipa-enroll.env from mios.toml [identity.ipa] SSOT"
mios_project_config "$_ipa_root" ipa-enroll
install -D -m 0644 "${_ipa_root}/etc/mios/ipa-enroll.env" /etc/mios/ipa-enroll.env

systemctl enable mios-freeipa-enroll.service
