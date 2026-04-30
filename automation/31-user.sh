#!/bin/bash
# MiOS v0.1.4 — 31-user: PAM, user creation, groups, sudoers
# Must run AFTER skel is populated (31-locale-theme writes skel/.bashrc)
# and BEFORE any service that references the user.
set -euo pipefail

echo "——————————————————————?"
echo "  MiOS v0.1.4 — User & Authentication"
echo "——————————————————————?"

# — PAM FIX —
echo "[31-user] Configuring PAM via authselect..."
if command -v authselect &>/dev/null; then
    authselect select local --force 2>/dev/null || {
        echo "[31-user] WARNING: authselect failed — using system_files overlay fallback"
    }
fi

# — USER CREATION —
# Password is pre-hashed (SHA-512) by the orchestrator — plaintext NEVER in build log.
# Defaults for CI builds or when environment variables are not provided:
C_USER="${MIOS_USER:-mios}"
# Note: MIOS_PASSWORD_HASH should be a SHA-512 crypt-style hash

echo "[31-user] Creating user ${C_USER} via sysusers..."
if [[ "${C_USER}" != "mios" ]]; then
    # Generate dynamic sysusers for custom username
    cat <<EOF > /usr/lib/sysusers.d/15-mios-custom.conf
u ${C_USER} - "MiOS Custom User" /var/home/${C_USER} /bin/bash
m ${C_USER} wheel
m ${C_USER} libvirt
m ${C_USER} kvm
m ${C_USER} video
m ${C_USER} render
m ${C_USER} input
m ${C_USER} dialout
m ${C_USER} docker
EOF
fi

# Apply sysusers declarative config
systemd-sysusers --root=/ 2>/dev/null || true

if getent passwd "${C_USER}" >/dev/null; then
    home=$(getent passwd "${C_USER}" | cut -d: -f6)
    if [ ! -d "$home" ]; then
        echo "[31-user] Creating home directory for ${C_USER} from /etc/skel..."
        mkdir -p "$home"
        cp -a /etc/skel/. "$home/"
    fi
    passwd -u "${C_USER}" 2>/dev/null || true
else
    echo "[31-user] ERROR: Failed to create user ${C_USER}"
fi

# — GROUP INJECTION —
# Groups are pre-created and memberships injected via /usr/lib/sysusers.d/*.conf
# and processed by systemd-sysusers above. Imperative calls removed.

# — SUDOERS —
# Managed via usr/lib/sudoers.d/10-mios-wheel
chmod 440 /usr/lib/sudoers.d/10-mios-wheel 2>/dev/null || true

# — LOCALE —
# Managed via usr/lib/locale.conf
localedef -i en_US -f UTF-8 en_US.UTF-8 2>/dev/null || true

# — CLOUD-INIT —
# Managed via usr/lib/cloud/cloud.cfg.d/10-mios.cfg

# — MULTIPATH —
# Managed via usr/lib/multipath.conf

# — FIX HOME DIRECTORY OWNERSHIP —
echo "[31-user] Fixing home directory ownership..."
awk -F: '$3 >= 1000 && $3 < 65000 {print $1}' /etc/passwd | while read -r u; do
    home=$(getent passwd "$u" | cut -d: -f6)
    if [ -d "$home" ]; then
        uid=$(id -u "$u"); gid=$(id -g "$u")
        chown -R "${uid}:${gid}" "$home"
    fi
done

# — NFS STATE DIRECTORY —
# Managed via usr/lib/tmpfiles.d/mios-nfs.conf

echo "[31-user] User & authentication configured."
