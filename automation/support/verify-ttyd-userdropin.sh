#!/bin/bash
# Verify the ttyd User= drop-in is in place and the units restart
# cleanly running as the SSOT [identity].username.
set -u

echo "── deploy fixed firstboot + tmpfiles ──"
cp /mnt/c/MiOS/usr/libexec/mios/mios-hermes-firstboot \
   /usr/libexec/mios/mios-hermes-firstboot
chmod +x /usr/libexec/mios/mios-hermes-firstboot
cp /mnt/c/MiOS/usr/lib/tmpfiles.d/mios-hermes.conf \
   /usr/lib/tmpfiles.d/mios-hermes.conf

echo
echo "── force firstboot re-run so the drop-ins get written ──"
systemctl reset-failed mios-hermes-firstboot.service 2>&1 || true
systemctl restart mios-hermes-firstboot.service
sleep 5
journalctl -u mios-hermes-firstboot.service --since '15 sec ago' \
    --no-pager 2>&1 | grep -E 'ttyd|MIOS_USER|User=' | tail -5

echo
echo "── inspect generated drop-ins ──"
for u in mios-ttyd-bash mios-ttyd-powershell; do
    f="/etc/systemd/system/${u}.service.d/10-mios-user.conf"
    if [[ -f "$f" ]]; then
        echo "  $f:"
        sed 's/^/    /' "$f"
    else
        echo "  $f: MISSING"
    fi
done

echo
echo "── ttyd unit state after firstboot ──"
for u in mios-ttyd-bash mios-ttyd-powershell; do
    state=$(systemctl is-active "${u}.service" 2>&1)
    main_pid=$(systemctl show -p MainPID --value "${u}.service" 2>&1)
    if [[ "$main_pid" != "0" && -n "$main_pid" ]]; then
        uid=$(stat -c %U "/proc/${main_pid}" 2>/dev/null || echo "?")
        printf '  %-26s active=%-10s running-as=%s\n' "$u" "$state" "$uid"
    else
        printf '  %-26s active=%s\n' "$u" "$state"
    fi
done

echo
echo "── tmpfiles for hermes cron/sessions/scratch/memory ──"
systemd-tmpfiles --create /usr/lib/tmpfiles.d/mios-hermes.conf 2>&1
for d in /var/lib/mios/hermes/cron /var/lib/mios/hermes/sessions \
         /var/lib/mios/hermes/scratch /var/lib/mios/hermes/memory; do
    if [[ -d "$d" ]]; then
        printf '  %s  (owner=%s mode=%s)\n' \
            "$d" "$(stat -c %U "$d")" "$(stat -c %a "$d")"
    else
        printf '  %s  MISSING\n' "$d"
    fi
done
