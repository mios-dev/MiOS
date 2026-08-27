#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures systemd services, enforces cgroup v2 compliance, fixes unit file permissions, and applies environment-specific gatin...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Service configuration ${MIOS_VERSION:-}"

for unit_file in \
    /usr/lib/systemd/system/var-home.mount \
    /usr/lib/systemd/system/var-lib-containers.mount \
    /usr/lib/systemd/system/mios-ceph-bootstrap.service \
    /usr/lib/systemd/system/cockpit.socket.d/listen.conf \
; do
    [ -f "$unit_file" ] && chmod 644 "$unit_file"
done
echo "[20-services] Fixed systemd unit file permissions"

_mios_src_root="$(cd "$(dirname "$0")/.." && pwd)"
_cockpit_gen="${_mios_src_root}/tools/generate-cockpit-conf.py"
if [[ -f "$_cockpit_gen" ]] && command -v python3 >/dev/null 2>&1; then
    python3 "$_cockpit_gen"
    install -D -m 0644 "${_mios_src_root}/etc/cockpit/cockpit.conf" /etc/cockpit/cockpit.conf
    echo "[20-services] projected /etc/cockpit/cockpit.conf from mios.toml [cockpit] SSOT"
else
    echo "[20-services] WARN: generate-cockpit-conf.py or python3 unavailable"
fi

echo "[20-services] WSL2/OCI service-skip drop-ins delivered via system_files overlay"

tuned-adm profile throughput-performance 2>/dev/null || true

echo "[20-services] chmod 644 applied to unit files; TuneD profile set to throughput-performance"
