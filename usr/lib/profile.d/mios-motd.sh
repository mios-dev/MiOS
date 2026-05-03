# 'MiOS' v0.2.2 -- System dashboard on interactive login.
# fastfetch for hardware overview, then 'MiOS' service dashboard.
# Suppress: export MIOS_NO_MOTD=1
if [[ $- == *i* ]] && [[ -z "${MIOS_NO_MOTD:-}" ]]; then
    if command -v fastfetch &>/dev/null; then
        fastfetch 2>/dev/null || true
    fi
    if [[ -x /usr/libexec/mios/motd ]]; then
        /usr/libexec/mios/motd 2>/dev/null || true
    fi
fi
