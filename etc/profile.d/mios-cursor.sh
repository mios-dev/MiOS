# AI-hint: Sets XCURSOR_THEME, XCURSOR_SIZE, and XCURSOR_PATH for interactive shells to ensure GUI applications launched from the terminal correctly inherit and display the Bibata cursor theme.
# AI-related: mios-cursor, mios-theme, mios-cursor-ensure

case "$-" in
    *i*) ;;
    *) return 0 ;;
esac

export XCURSOR_THEME="${XCURSOR_THEME:-Bibata-Modern-Classic}"
export XCURSOR_SIZE="${XCURSOR_SIZE:-24}"
export XCURSOR_PATH="${XCURSOR_PATH:-$HOME/.local/share/icons:$HOME/.icons:/usr/share/icons:/usr/share/pixmaps}"

if command -v mios-cursor-ensure >/dev/null 2>&1 \
   && [ ! -e "${XDG_CACHE_HOME:-$HOME/.cache}/mios/cursor-ensured" ] \
   && [ ! -d "/usr/share/icons/${XCURSOR_THEME}/cursors" ] \
   && [ ! -d "$HOME/.local/share/icons/${XCURSOR_THEME}/cursors" ]; then
    (mios-cursor-ensure >/dev/null 2>&1 &) 2>/dev/null || true
fi

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user import-environment XCURSOR_THEME XCURSOR_SIZE 2>/dev/null || true
fi
