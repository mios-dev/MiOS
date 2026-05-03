#!/usr/bin/env bash
# 'MiOS' FreeIPA Zero-Touch Enrollment.
# Run by mios-freeipa-enroll.service (gated by:
#   ConditionPathExists=/etc/mios/ipa-enroll.env       <- operator opt-in
#   ConditionPathExists=!/etc/ipa/default.conf         <- not already enrolled
# ).
#
# Reads enrollment parameters from /etc/mios/ipa-enroll.env (sourced as
# shell). Required:
#     MIOS_IPA_REALM        e.g. EXAMPLE.COM
#     MIOS_IPA_DOMAIN       e.g. example.com
#     MIOS_IPA_SERVER       e.g. ipa.example.com
#     MIOS_IPA_PRINCIPAL    enrollment principal (e.g. admin)
#     MIOS_IPA_PASSWORD     enrollment password (read at exec time only)
# Optional:
#     MIOS_IPA_HOSTNAME     (defaults to current hostname)
#     MIOS_IPA_NTP          (defaults to true)
#     MIOS_IPA_AUTOMOUNT    (defaults to false)
#
# Service unit hardens UMask=0077 so the env file isn't world-readable
# during sourcing.
set -euo pipefail
# shellcheck source=/usr/lib/mios/paths.sh
source /usr/lib/mios/paths.sh

_log()  { logger -t mios-freeipa-enroll "$*" 2>/dev/null || true; echo "[freeipa-enroll] $*" >&2; }

CONF="${MIOS_ETC_DIR}/ipa-enroll.env"
if [[ ! -r "$CONF" ]]; then
    _log "no $CONF -- enrollment not requested"
    exit 0
fi
if [[ -e /etc/ipa/default.conf ]]; then
    _log "already enrolled (/etc/ipa/default.conf exists); nothing to do"
    exit 0
fi
if ! command -v ipa-client-install >/dev/null 2>&1; then
    _log "ipa-client-install not present -- freeipa-client RPM missing"
    exit 0
fi

umask 0077
# shellcheck disable=SC1090
. "$CONF"

for v in MIOS_IPA_REALM MIOS_IPA_DOMAIN MIOS_IPA_SERVER MIOS_IPA_PRINCIPAL MIOS_IPA_PASSWORD; do
    if [[ -z "${!v:-}" ]]; then
        _log "missing required var $v in $CONF"
        exit 1
    fi
done

: "${MIOS_IPA_HOSTNAME:=$(hostname -f 2>/dev/null || hostname)}"
: "${MIOS_IPA_NTP:=true}"
: "${MIOS_IPA_AUTOMOUNT:=false}"

_log "enrolling to realm=$MIOS_IPA_REALM domain=$MIOS_IPA_DOMAIN server=$MIOS_IPA_SERVER hostname=$MIOS_IPA_HOSTNAME"

ARGS=(
    --unattended
    --mkhomedir
    --no-ssh
    --no-sshd
    --realm="$MIOS_IPA_REALM"
    --domain="$MIOS_IPA_DOMAIN"
    --server="$MIOS_IPA_SERVER"
    --hostname="$MIOS_IPA_HOSTNAME"
    --principal="$MIOS_IPA_PRINCIPAL"
    --password="$MIOS_IPA_PASSWORD"
)
[[ "$MIOS_IPA_NTP" == "true" ]] || ARGS+=(--no-ntp)
[[ "$MIOS_IPA_AUTOMOUNT" == "true" ]] && ARGS+=(--enable-automount)

ipa-client-install "${ARGS[@]}"
rc=$?
if (( rc == 0 )); then
    _log "enrollment successful"
    MIOS_IPA_PASSWORD="$(printf '%*s' "${#MIOS_IPA_PASSWORD}" '' | tr ' ' x)"
    exit 0
fi
_log "enrollment FAILED (rc=$rc)"
exit "$rc"
