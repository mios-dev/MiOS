#!/usr/bin/env bash
# AI-hint: Configures the host's admin sshd to bind to the SSOT port defined in mios.toml by creating a drop-in config in /etc/ssh/sshd_config.d/ to avoid port conflicts with Forgejo's git-ssh.
# AI-related: mios-forge, mios-ssh-port, mios-forge.container
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

# Pin the host ADMIN sshd to the SSOT port (mios.toml [ports] ssh -> MIOS_PORT_SSH).
#
# MiOS hardens the admin sshd OFF the default :22 -- :22 on the host is the
# Forgejo container's git-ssh (see mios-forge.container; forge_ssh=2222 is the
# intended host port, but the container historically squats :22). The admin
# sshd therefore listens on MIOS_PORT_SSH (e.g. 49955), and automation/
# 25-firewall-ports.sh + 33-firewall.sh open exactly that port.
#
# The stock /etc/ssh/sshd_config carries only `#Port 22` (commented) and an
# `Include /etc/ssh/sshd_config.d/*.conf` near the top. Without an explicit
# Port a CLEAN build's sshd binds :22 -- which the firewall does NOT open and
# which Forgejo occupies -> the admin sshd is unreachable = total SSH lockout
# (the incident). We ship the port as a drop-in so it is reproducible
# and stays the single SSOT value, not an out-of-band edit to the main file.
#
# Port values resolve through the layered SSOT (mios.toml [ports] ->
# tools/lib/userenv.sh -> MIOS_PORT_* env vars -> automation/lib/globals.sh
# fallbacks). Hardcoded port literals are bugs; lift them.

echo "==> Pinning host admin sshd to MIOS_PORT_SSH=${MIOS_PORT_SSH} via drop-in..."

install -d -m 0755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/09-mios-ssh-port.conf <<EOF
# MiOS: host admin sshd port. SSOT = mios.toml [ports] ssh (MIOS_PORT_SSH).
# Baked at build by automation/34-sshd-port.sh -- do not hand-edit.
# Hardened off :22 (Forgejo git-ssh); the firewall opens this port.
Port ${MIOS_PORT_SSH}
EOF
chmod 0644 /etc/ssh/sshd_config.d/09-mios-ssh-port.conf

# Best-effort sanity check. `sshd -t` needs host keys, which are usually absent
# in the OCI build container, so this must NEVER fail the build.
if command -v sshd >/dev/null 2>&1; then
    sshd -t 2>/dev/null \
        && echo "==> sshd config valid; admin sshd will bind ${MIOS_PORT_SSH}." \
        || echo "==> drop-in written; skipped sshd -t (host keys absent at build is normal)."
fi
