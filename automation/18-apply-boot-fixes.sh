#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# 'MiOS': Systemd execution analysis & WSL2 Boot Loop fixes
# Resolves ordering cycles, executable stripping, and hardware-dependent
# failure cascades detected during F44 boots on varied hardware/hypervisors.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

echo "==> Applying 'MiOS' system service fixes..."

# 1. Fix USBGuard Permissions
# Log trace: Permissions for /etc/usbguard/usbguard-daemon.conf should be 0600
if [ -f /etc/usbguard/usbguard-daemon.conf ]; then
    chmod 0600 /etc/usbguard/usbguard-daemon.conf
fi

# 2. Fix 203/EXEC for custom 'MiOS' services
# Log trace: mios-role.service & mios-cdi-detect.service exited 203/EXEC
# Global chmod commands in earlier pipelines stripped execution bits.
# Handle all scripts in /usr/libexec/mios/ and named patterns.
find ${MIOS_LIBEXEC_DIR} -type f -exec chmod +x {} \; || true
find /usr/libexec -type f \( -name 'mios-*' -o -name 'role-apply' -o -name 'selinux-init' -o -name 'gpu-detect' -o -name 'cpu-isolate' -o -name 'motd' -o -name 'dash' -o -name 'sb-audit' -o -name 'wsl-init' -o -name 'wsl-firstboot' -o -name 'sb-keygen' -o -name 'tpm-enroll' \) -exec chmod +x {} \; || true
find /usr/bin -name 'mios-*' -type f -exec chmod +x {} \; || true

# 3. Libvirt QEMU Hooks
# Ensure hooks are executable. We check both /etc and /usr/lib for bootc parity.
for hook in /etc/libvirt/hooks/qemu /usr/lib/libvirt/hooks/qemu; do
    if [ -f "$hook" ]; then
        chmod +x "$hook"
    fi
done

# 4. Fix systemd-resolved 217/USER
# Log trace: systemd-resolved.service exited 217/USER
# User mapping required at boot time; ensuring it's compiled statically.
if [ -f /usr/lib/sysusers.d/systemd-resolve.conf ]; then
    systemd-sysusers /usr/lib/sysusers.d/systemd-resolve.conf || true
fi

# 5. Fix Systemd Ordering Cycle for GPU Passthrough
# Log trace: sockets.target: Found ordering cycle: docker.socket/start after mios-gpu-nvidia.service/start after basic.target
# Drop-in handled via overlay.

# 6. OCI Container and WSL2 Service Gating
# Custom 'MiOS' services that require hardware access or full system init
# skip OCI containers and WSL2 via drop-ins in system_files overlay.
echo "==> Service gating drop-ins active via overlay"

# 7. WSL2 Compatibility Gating (Legacy section kept for unit-specific fallbacks)

