#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures firewalld rules via firewall-offline-cmd to open specific TCP ports for MiOS services (Hermes, Open WebUI, Code Server, etc.) based on environment-derived port variables.
# AI-related: mios-hermes, mios-open-webui, mios-code-server, mios-guacamole, mios-forge, mios-cockpit-link, mios-adguard, mios-pxe
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

source "$(dirname "$0")/lib/common.sh"

mios_log "Configuring firewalld ports for 'MiOS' services"

if command -v miosd >/dev/null 2>&1; then
    miosd firewall-ports
    mios_ok "Configured firewalld ports via miosd"
    exit 0
fi


# Derive open ports from SSOT [firewall.open_ports]
_ssot_ports=()
if python3 -c 'import tomllib' 2>/dev/null; then
    mapfile -t _ssot_ports < <(python3 -c '
import tomllib, os
path = "/usr/share/mios/mios.toml"
if not os.path.exists(path):
    path = os.path.join(os.path.dirname(__file__), "../usr/share/mios/mios.toml")
if os.path.exists(path):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    fw = data.get("firewall", {}).get("open_ports", [])
    ports = data.get("ports", {})
    for k in fw:
        val = ports.get(k)
        if val is not None:
            print(f"{val}")
' 2>/dev/null || true)
fi

if [ "${#_ssot_ports[@]}" -gt 0 ]; then
    for port in "${_ssot_ports[@]}"; do
        firewall-offline-cmd --zone=public --add-port="${port}/tcp" || true
    done
else
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_HERMES}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_OPEN_WEBUI}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_CODE_SERVER:-8900}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_GUACAMOLE_PORT}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_CEPH_DASHBOARD_PORT}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_K3S_API_PORT}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_RDP_PORT}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_FORGE_HTTP}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_FORGE_SSH}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_COCKPIT_LINK}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_ADGUARD_UI:-8050}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_SSH}/tcp
    firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_COCKPIT}/tcp
fi

firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_ADGUARD_DNS:-53}/tcp
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_ADGUARD_DNS:-53}/udp
firewall-offline-cmd --zone=public --add-service=ssh
firewall-offline-cmd --zone=public --add-service=mios-pxe

