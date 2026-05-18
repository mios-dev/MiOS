#!/bin/bash
# Deploy the firstboot + env-drop-in fixes, then re-run firstboot
# and report the final state of all canonical services.
set -u

echo "=== copying fixed files ==="
cp /mnt/c/MiOS/usr/libexec/mios/mios-hermes-firstboot \
   /usr/libexec/mios/mios-hermes-firstboot
chmod +x /usr/libexec/mios/mios-hermes-firstboot
cp /mnt/c/MiOS/usr/lib/systemd/system/hermes-agent.service.d/20-mios-paths-env.conf \
   /usr/lib/systemd/system/hermes-agent.service.d/20-mios-paths-env.conf
echo "  source files copied"

echo
echo "=== bash -n syntax-check firstboot ==="
bash -n /usr/libexec/mios/mios-hermes-firstboot && echo "OK"

echo
echo "=== systemd daemon-reload ==="
systemctl daemon-reload

echo
echo "=== reset-failed mios-hermes-firstboot + start ==="
systemctl reset-failed mios-hermes-firstboot.service 2>&1 || true
# Background so this script doesn't block on the full firstboot
# walk (it takes ~5s + the model pre-warm async).
systemctl start --no-block mios-hermes-firstboot.service
sleep 8

echo
echo "=== firstboot final state ==="
systemctl is-active mios-hermes-firstboot.service
journalctl -u mios-hermes-firstboot.service --since '30 sec ago' \
    --no-pager 2>&1 | tail -8

echo
echo "=== env drop-in parse check (no rejected lines) ==="
journalctl -u hermes-agent.service --since '30 sec ago' --no-pager \
    | grep -E 'Invalid environment assignment' | head -3 \
    || echo "  (none -- drop-in parses cleanly)"
