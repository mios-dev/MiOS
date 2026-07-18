#!/bin/bash
# AI-hint: Phase-2 build sub-phase: now mostly logs that Cockpit/NVIDIA/Ceph .desktop entries are delivered via the 08-system-files overlay; the only active work is staging the MOTD/fastfetch dashboard (profile.d/mios-motd.sh fallback) for terminal sessions.
# AI-related: profile.d/mios-motd.sh, /usr/libexec/mios/motd., mios-motd
# 'MiOS' - 39-desktop-polish: Desktop entries, Cockpit webapp, MOTD
#
# CHANGELOG - :
#   - FIX: mios-motd source path was /tmp/automation/automation/ (never exists).
#     Scripts run from /ctx/automation/ in the buildroot. The bogus path + the
#     `|| true` swallowed the failure silently, so /usr/libexec/mios-motd
#     was never created. profile.d/mios-motd.sh falls back to it when
#     fastfetch is missing, so terminal MOTD printed nothing on every
#     v2.0-v2.2 image.
#   - FIX: SCRIPT_DIR-relative copy so this works whether build.sh invokes
#     us from /ctx/automation/ or any other future path. If the source is
#     missing, FAIL LOUDLY (remove the silencing `|| true`) so it can't
#     regress unnoticed.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[39-desktop-polish] staging profile.d/mios-motd.sh terminal MOTD; desktop entries delivered by 08-system-files overlay"

# ═══ COCKPIT DESKTOP ENTRY -- uses cockpit-desktop (no TLS warnings) ═══
echo "[39-desktop-polish] Cockpit desktop entry delivered via overlay."

# ═══ NVIDIA SETTINGS DESKTOP ENTRY ═══
echo "[39-desktop-polish] NVIDIA Settings desktop entry delivered via overlay."

# ═══ CEPH DASHBOARD -- update to use correct app name ═══
echo "[39-desktop-polish] Ceph Dashboard desktop entry delivered via overlay."

# ═══ MOTD DASHBOARD ═══
# : ARCHITECTURAL PURITY FIX. The MOTD script is now delivered via the
# system_files overlay to /usr/libexec/mios/motd. We no longer perform
# manual 'install' calls here.
echo "[39-desktop-polish] MOTD dashboard delivered via overlay."

# ═══ FASTFETCH CONFIG -- services dashboard on terminal open ═══
echo "[39-desktop-polish] Fastfetch config delivered via overlay."

# ═══ PROFILE.D -- fastfetch + MOTD on terminal/TTY open ═══
echo "[39-desktop-polish] Profile.d MOTD script delivered via overlay."

echo "[39-desktop-polish] MOTD/desktop-entry overlay delivery reported"
