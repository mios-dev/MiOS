# AI-hint: !/bin/bash MIOS_APPLY_CLASS=universal Sets executable permissions for the core mios- suite of CLI tools in /usr/bin/ and installs auxiliary scripts like mios-toggle-hea...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_59_tools_sh.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mios_log "Configure MiOS CLI tools"


TOOLS=(
    mios
    mios-backup
    mios-build
    mios-chrome
    mios-deploy
    mios-pull
    mios-rebuild
    mios-update
    hermes
)

for tool in "${TOOLS[@]}"; do
    if [ -f "/usr/bin/$tool" ]; then
        chmod +x "/usr/bin/$tool"
    fi
done

[[ -f "/usr/bin/mios-dash" ]] || ln -sf /usr/libexec/mios/mios-dashboard.sh /usr/bin/mios-dash 2>/dev/null || true

mios_log "Install mios-toggle-headless"
if [ -f "${SCRIPT_DIR}/mios-toggle-headless" ]; then
    install -Dm0755 "${SCRIPT_DIR}/mios-toggle-headless" "/usr/bin/mios-toggle-headless"
fi

USERENV_SRC=""
for cand in \
    "${SCRIPT_DIR}/../tools/lib/userenv.sh" \
    "/tmp/build/tools/lib/userenv.sh" \
    "/ctx/tools/lib/userenv.sh"
do
    if [[ -f "$cand" ]]; then USERENV_SRC="$cand"; break; fi
done
if [[ -n "$USERENV_SRC" ]]; then
    install -D -m 0644 "$USERENV_SRC" /usr/lib/mios/userenv.sh
    mios_ok "Installed userenv.sh resolver to /usr/lib/mios/userenv.sh"
else
    mios_warn "Tools/lib/userenv.sh not found in build context; mios-env will fall back to legacy env-style files only"
fi

mios_ok "CLI tools configured; run 'mios"
