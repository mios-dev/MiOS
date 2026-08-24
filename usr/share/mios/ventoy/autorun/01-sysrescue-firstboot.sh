#!/bin/bash
set -euo pipefail

echo "[MiOS SystemRescue Firstboot] Setting up SSH and SSOT credentials"

if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    ssh-keygen -A 2>/dev/null || true
fi

mkdir -p /etc/ssh/sshd_config.d
cat <<'EOF' > /etc/ssh/sshd_config.d/10-mios-ssh.conf
PermitRootLogin yes
PasswordAuthentication yes
X11Forwarding yes
PubkeyAuthentication yes
EOF

SYS_USER="${MIOS_IDENTITY_USERNAME:-mios}"
SYS_PASS="${MIOS_IDENTITY_DEFAULT_PASSWORD:-mios}"

echo "root:${SYS_PASS}" | chpasswd
if ! id "${SYS_USER}" &>/dev/null; then
    useradd -m -g wheel -s /bin/bash "${SYS_USER}" 2>/dev/null || true
fi
echo "${SYS_USER}:${SYS_PASS}" | chpasswd

systemctl enable --now sshd 2>/dev/null || systemctl restart sshd 2>/dev/null || true

IP_LIST=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' || echo "No IP detected yet")
BANNER="
===================================================================
  MiOS SystemRescue Live Diagnostic Environment
  SSH Service: ACTIVE (Port 22)
  Credentials: root / ${SYS_PASS}  |  ${SYS_USER} / ${SYS_PASS}
  IP Address(es): ${IP_LIST}
===================================================================
"
echo "${BANNER}" >> /etc/issue
echo "${BANNER}" >> /etc/motd
if [ -c /dev/tty1 ]; then
    echo "${BANNER}" > /dev/tty1 || true
fi

echo "[MiOS SystemRescue Firstboot] SSH fully enabled. User '${SYS_USER}' and 'root' ready with SSOT credentials"
