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


firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_HERMES}/tcp          # mios-hermes (Hermes-Agent /v1)
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_OPEN_WEBUI}/tcp     # mios-open-webui (rich chat UI)
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_CODE_SERVER:-8800}/tcp # mios-code-server (VS Code in a browser)
firewall-offline-cmd --zone=public --add-port=${MIOS_GUACAMOLE_PORT}/tcp       # mios-guacamole (Browser desktop)
firewall-offline-cmd --zone=public --add-port=${MIOS_CEPH_DASHBOARD_PORT}/tcp  # Ceph dashboard
firewall-offline-cmd --zone=public --add-port=${MIOS_K3S_API_PORT}/tcp         # K3s API
firewall-offline-cmd --zone=public --add-port=${MIOS_RDP_PORT}/tcp             # RDP
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_FORGE_HTTP}/tcp      # mios-forge HTTP
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_FORGE_SSH}/tcp       # mios-forge git+ssh
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_COCKPIT_LINK}/tcp    # mios-cockpit-link discovery shim
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_ADGUARD_UI:-8053}/tcp  # mios-adguard web UI/API
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_ADGUARD_DNS:-53}/tcp   # mios-adguard DNS (TCP: large/AXFR)
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_ADGUARD_DNS:-53}/udp   # mios-adguard DNS (UDP: normal queries)
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_SSH}/tcp             # host admin sshd (hardened off :22; was --add-service=ssh, which opened only 22 and locked out the 49955 sshd)
firewall-offline-cmd --zone=public --add-service=ssh                            # :22 kept open for Forgejo git-ssh squatting the host port (Forge port drift -- drop once Forge moves to ${MIOS_PORT_FORGE_SSH})
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_COCKPIT}/tcp          # ${MIOS_PORT_COCKPIT} (host service)
firewall-offline-cmd --zone=public --add-service=mios-pxe
