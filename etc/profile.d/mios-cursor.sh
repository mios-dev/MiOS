# AI-hint: Sets XCURSOR_THEME, XCURSOR_SIZE, and XCURSOR_PATH for interactive shells to ensure GUI applications launched from the terminal correctly inherit and display the Bibata cursor theme.
# AI-related: mios-cursor, mios-theme, mios-cursor-ensure
# shellcheck shell=sh

case "$-" in
    *i*) ;;
    *) return 0 ;;
esac

_mios_cursor_env=$(python3 - <<'PY'
import os, shlex, sys
sys.path.insert(0, "/usr/lib/mios")
import mios_toml
data = mios_toml.load_merged()
cursor = data["theme"]["cursor_linux"]
values = {"XCURSOR_THEME": cursor["theme"], "XCURSOR_SIZE": cursor["size"],
          "XCURSOR_PATH": ":".join(os.path.expanduser(p) for p in data["graphics"]["xcursor_path"].split(":"))}
for key, value in values.items():
    print(f"export {key}={shlex.quote(str(value))}")
PY
) || return 1
eval "$_mios_cursor_env"
unset _mios_cursor_env

if command -v mios-cursor-ensure >/dev/null 2>&1 \
   && [ ! -d "$HOME/.local/share/icons/${XCURSOR_THEME}/cursors" ]; then
    (mios-cursor-ensure >/dev/null 2>&1 &) 2>/dev/null || true
fi

if [ -n "${DISPLAY:-}" ] && [ -x /usr/libexec/mios/mios-cursor-apply ]; then
    /usr/libexec/mios/mios-cursor-apply >/dev/null 2>&1 || true
fi

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user import-environment XCURSOR_THEME XCURSOR_SIZE 2>/dev/null || true
fi
