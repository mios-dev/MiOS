# MiOS v0.1.4 — Terminal/TTY dashboard
# Shows fastfetch services panel on interactive login.
# Suppress with:  export MIOS_NO_MOTD=1
if [[ $- == *i* ]] && [ -z "${MIOS_NO_MOTD:-}" ]; then
    if command -v fastfetch &>/dev/null; then
        fastfetch 2>/dev/null || true
    elif [[ -x /usr/libexec/mios/motd ]]; then
        /usr/libexec/mios/motd 2>/dev/null || true
    fi
fi
