#!/bin/bash
# AI-hint: Hot-deploys source-only MiOS binaries, configuration files (tmpfiles/sysusers), and OWUI tools to the live VM's /usr path without a full image rebuild to apply immediate updates to the broker and system services.
# AI-related: /usr/share/mios/openwebui/tools, /usr/share/mios/openwebui/tools/mios_computer_use.py, mios-coderun-sandbox, mios-launcher-daemon, mios-db, mios-docgen, mios-coderun-codemode, mios-stresstest, mios-owui-install-computer-use, mios-hermes-firstboot
# automation/support/deploy-tooling-live.sh
# Deploy the SOURCE-ONLY tooling to the LIVE VM /usr (no image rebuild): the new/
# changed libexec tools + shim-links + tmpfiles + sysusers, reload, restart the
# broker (WS-4 capture-timeout fix), and register the OWUI computer-use tool.
# CR-strips every file. REBUILD-GATED items are NOT handled here (dnf packages:
# pandoc/libreoffice for docgen; localhost/ container image: mios-coderun-sandbox
# for code_mode; boot-config: WS-7 fapolicyd/UKI).
set -euo pipefail
SRC=/mnt/c/MiOS
LX=/usr/libexec/mios

echo "[live] libexec tools -> $LX"
for f in mios-launcher-daemon mios-db mios-docgen mios-coderun-codemode \
         mios-stresstest mios-owui-install-computer-use mios-hermes-firstboot \
         mios-codemode-api.py test_mios_docgen.py; do
    s="$SRC/usr/libexec/mios/$f"
    [ -f "$s" ] || { echo "  MISSING $s"; continue; }
    tr -d '\r' < "$s" | sudo tee "$LX/$f" >/dev/null
    sudo chmod 0755 "$LX/$f"
    echo "  + $f"
done

echo "[live] tmpfiles + sysusers"
for f in mios-shim-links.conf mios-pgvector.conf mios-llamacpp.conf \
         mios-agent-pipe.conf mios-surrealdb.conf; do
    s="$SRC/usr/lib/tmpfiles.d/$f"
    [ -f "$s" ] && tr -d '\r' < "$s" | sudo tee "/usr/lib/tmpfiles.d/$f" >/dev/null && echo "  + tmpfiles/$f"
done
[ -f "$SRC/usr/lib/sysusers.d/50-mios-services.conf" ] && \
    tr -d '\r' < "$SRC/usr/lib/sysusers.d/50-mios-services.conf" | sudo tee /usr/lib/sysusers.d/50-mios-services.conf >/dev/null && echo "  + sysusers/50-mios-services.conf"
sudo systemd-sysusers 2>&1 | tail -2 || true
sudo systemd-tmpfiles --create /usr/lib/tmpfiles.d/mios-shim-links.conf 2>&1 | tail -2 || true
sudo systemd-tmpfiles --create /usr/lib/tmpfiles.d/mios-pgvector.conf /usr/lib/tmpfiles.d/mios-llamacpp.conf 2>&1 | tail -2 || true

echo "[live] restart broker (WS-4 capture-timeout fix)"
sudo systemctl restart mios-launcher-daemon.service 2>&1 || true
sleep 2
echo "  broker: $(systemctl is-active mios-launcher-daemon.service)"

echo "[live] shim resolution check"
for t in mios-docgen mios-coderun-codemode mios-stresstest mios-db; do
    p="$(command -v "$t" 2>/dev/null || true)"
    [ -n "$p" ] && echo "  resolves: $t -> $p" || echo "  NOT-on-PATH: $t"
done

echo "[live] OWUI computer-use tool file + installer"
sudo install -d -m 0755 /usr/share/mios/openwebui/tools
tr -d '\r' < "$SRC/usr/share/mios/openwebui/tools/mios_computer_use.py" | sudo tee /usr/share/mios/openwebui/tools/mios_computer_use.py >/dev/null
if [ -x "$LX/mios-owui-install-computer-use" ]; then
    sudo "$LX/mios-owui-install-computer-use" 2>&1 | tail -6 || echo "  (OWUI install failed -- is OWUI reachable on :3030?)"
fi

echo "[live] DONE. REBUILD-GATED (NOT deployed): docgen pandoc/libreoffice (dnf), code_mode mios-coderun-sandbox image (localhost/, build-time), WS-7 fapolicyd/UKI (boot)."
