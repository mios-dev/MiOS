#!/usr/bin/env bash
# 22-freeipa-client.sh -- install FreeIPA/SSSD client + arm zero-touch enrollment.
#
# Runtime path: mios-freeipa-enroll.service runs only when
# /etc/mios/ipa-enroll.env is present and /etc/ipa/default.conf is absent.
#
# Upstream regression notes (April 2026):
#   bz 2320133 -- SSSD file caps stripped by rpm-ostree < bootc v0.2.0-2.fc41.
#                Asserted post-install; build fails fast if caps are missing.
#   bz 2332433 -- /var/lib/ipa-client/sysrestore/ missing on first boot.
#                Pre-created via tmpfiles.d.
set -euo pipefail

echo "==> Installing FreeIPA & SSSD for zero-touch enrollment..."

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"

# Install client + SSSD tooling.
install_packages "freeipa"

# ── SSSD file capability regression check (bz 2320133) ─────────────────────
echo "==> Verifying SSSD file capabilities..."
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
        echo "ERROR: $bin missing file capabilities (bz 2320133 regression)"
        CAP_FAIL=$((CAP_FAIL + 1))
    fi
done
if (( CAP_FAIL > 0 )); then
    echo "WARNING: ${CAP_FAIL} SSSD binary(ies) lost file capabilities -- FreeIPA authentication may require 'setcap' at runtime."
fi

# Arm the zero-touch enrollment oneshot (gated by ConditionPathExists).
systemctl enable mios-freeipa-enroll.service
