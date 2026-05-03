#!/usr/bin/env bash
# usr/libexec/mios/ceph-bootstrap.sh
#
# 'MiOS' Ceph cluster bootstrap (first-boot only). Targeted by both
# usr/lib/systemd/system/ceph-bootstrap.service (legacy name) and
# mios-ceph-bootstrap.service (canonical MiOS name) -- the two units
# share this single ExecStart so the bootstrap is consistent regardless
# of which one fires first. Sentinel-guarded so re-runs are no-ops.
#
# Path: /usr/libexec/mios/ -- the MiOS-private libexec tree, immutable
# composefs surface. The previous /usr/local/bin path was wrong: on
# bootc/FCOS layouts /usr/local is a symlink to /var/usrlocal which is
# mutable per-host, so a binary written there at build time gets
# wiped by the standard /var-cleanup at image commit (Architectural
# Law 2 -- NO-MKDIR-IN-VAR).
#
# Operation:
#   1. Skip if /var/lib/ceph/.bootstrapped sentinel exists.
#   2. Skip if cephadm is missing (Ceph stack not installed -- the
#      mios-ceph Quadlet is gated by ConditionPathExists=/etc/ceph/
#      ceph.conf so the cluster only comes up after this script
#      writes that file).
#   3. Resolve the host's primary IP via 'ip route get 1.1.1.1'.
#   4. Run 'cephadm bootstrap --single-host-defaults' (workstation-
#      friendly defaults: replication=1, no monmap, single OSD).
#   5. Drop the sentinel.
#
# References:
#   - https://docs.ceph.com/en/latest/cephadm/install/
#   - https://docs.ceph.com/en/latest/cephadm/install/#single-host
set -euo pipefail

SENTINEL_DIR="/var/lib/ceph"
SENTINEL="${SENTINEL_DIR}/.bootstrapped"

_log() { logger -t mios-ceph-bootstrap "$*" 2>/dev/null || true; echo "[ceph-bootstrap] $*" >&2; }

if [[ -f "$SENTINEL" ]]; then
    _log "sentinel exists ($SENTINEL); cluster already bootstrapped -- nothing to do"
    exit 0
fi

if ! command -v cephadm >/dev/null 2>&1; then
    _log "cephadm not installed -- skipping (Ceph stack not present in this build)"
    install -d -m 0755 "$SENTINEL_DIR"
    touch "$SENTINEL"
    exit 0
fi

# Resolve the bootstrap monitor IP. 'ip route get' returns the source
# address the kernel would use for outbound traffic to 1.1.1.1, which
# is the right answer for a single-host workstation deployment.
MON_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '/src/{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1 || true)"
if [[ -z "$MON_IP" ]]; then
    _log "WARN: could not resolve a usable IPv4 source address; skipping bootstrap"
    exit 0
fi

_log "running 'cephadm bootstrap --single-host-defaults --mon-ip ${MON_IP}'"
if cephadm bootstrap \
    --single-host-defaults \
    --mon-ip "${MON_IP}" \
    --skip-monitoring-stack \
    --skip-dashboard \
    --allow-fqdn-hostname \
    --output-config /etc/ceph/ceph.conf \
    --output-keyring /etc/ceph/ceph.client.admin.keyring \
    2>&1 | logger -t mios-ceph-bootstrap; then
    _log "cephadm bootstrap completed"
else
    _log "ERROR: cephadm bootstrap failed (cluster may be partially configured)"
    exit 1
fi

install -d -m 0755 "$SENTINEL_DIR"
touch "$SENTINEL"
_log "first-boot bootstrap complete"
exit 0
