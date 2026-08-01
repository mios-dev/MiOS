#!/usr/bin/env bash
# AI-hint: Initializes the Ceph cluster on first boot by running cephadm bootstrap with single-host defaults and creating a sentinel file to prevent re-execution; use this to trigger or debug the initial Ceph cluster setup.
# AI-related: mios-ceph-bootstrap, mios-ceph, ceph-bootstrap.service, mios-ceph-bootstrap.service
# AI-functions: _log
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

MON_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '/src/{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1 || true)"
if [[ -z "$MON_IP" ]]; then
    _log "WARN: could not resolve a usable IPv4 source address; skipping bootstrap"
    exit 0
fi

BOOTSTRAP_CONFIG="/tmp/ceph-bootstrap-config.conf"
cat <<EOF > "$BOOTSTRAP_CONFIG"
[global]
mds_cache_memory_limit = 4294967296
EOF

_log "running 'cephadm bootstrap --single-host-defaults --mon-ip ${MON_IP}'"
if cephadm bootstrap \
    --single-host-defaults \
    --mon-ip "${MON_IP}" \
    --skip-monitoring-stack \
    --skip-dashboard \
    --allow-fqdn-hostname \
    --output-config /etc/ceph/ceph.conf \
    --output-keyring /etc/ceph/ceph.client.admin.keyring \
    --config "$BOOTSTRAP_CONFIG" \
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
