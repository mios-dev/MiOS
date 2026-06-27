# AI-hint: Sets XCURSOR_THEME, XCURSOR_SIZE, and XCURSOR_PATH for interactive shells to ensure GUI applications launched from the terminal correctly inherit and display the Bibata cursor theme.
# AI-related: mios-cursor, mios-theme, mios-cursor-ensure
# /etc/profile.d/mios-cursor.sh
#
# Export XCURSOR_THEME + XCURSOR_SIZE for every interactive shell on
# MiOS. Apps spawned from a shell (Epiphany, Nautilus, code-server,
# btop, ptyxis, anything via xdg-open) inherit this env and resolve
# the Bibata cursor instead of the libXcursor default Adwaita.
#
# Why a profile.d entry exists alongside /usr/lib/environment.d/50-mios.conf:
# systemd's environment.d is loaded by `systemd --user` and via
# `pam_systemd`, but a wsl.exe-spawned bash session bypasses both
# (pam_systemd is condition-skipped on WSL2; the user-systemd manager
# doesn't paint the parent shell's env). Without a profile.d export,
# bash-spawned apps see neither XCURSOR_THEME nor XCURSOR_SIZE and
# fall back to Adwaita via /usr/share/icons/default/index.theme.
# Operator-flagged "bibata cursor is NOT global at all!!
# still see broken cursor in epiphany and other Linux windows"
#
# Values mirror the canonical SSOT cursor settings:
#   - mios.toml [theme].cursor_theme   (deferred -- not yet wired)
#   - /usr/lib/environment.d/50-mios.conf XCURSOR_THEME/SIZE
#   - /etc/dconf/db/local.d/00-mios-theme cursor-theme/size
#   - /etc/skel/.config/gtk-{3,4}.0/settings.ini gtk-cursor-theme-*
# Edit all four when changing the global cursor theme.

# Bail early on non-interactive shells (cron, scripts) so we don't
# pollute their env unnecessarily. Interactive XCURSOR_* propagates
# to children that need it (Wayland clients, X apps, flatpaks).
case "$-" in
    *i*) ;;
    *) return 0 ;;
esac

export XCURSOR_THEME="${XCURSOR_THEME:-Bibata-Modern-Classic}"
export XCURSOR_SIZE="${XCURSOR_SIZE:-24}"
# /usr is read-only on bootc, so when the build's /usr/share/icons fetch
# is unavailable Bibata is installed into ~/.local/share/icons instead
# (see mios-cursor-ensure). libXcursor's DEFAULT path does NOT include
# ~/.local/share/icons, so add it explicitly -- otherwise shell-launched
# host apps fall back to the default cursor even with XCURSOR_THEME set.
export XCURSOR_PATH="${XCURSOR_PATH:-$HOME/.local/share/icons:$HOME/.icons:/usr/share/icons:/usr/share/pixmaps}"

# Self-heal: if the cursor theme is absent from every search path, fetch
# it into ~/.local/share/icons ONCE (marker-guarded, backgrounded so it
# never blocks the shell). No-op when /usr/share/icons already has it.
if command -v mios-cursor-ensure >/dev/null 2>&1 \
   && [ ! -e "${XDG_CACHE_HOME:-$HOME/.cache}/mios/cursor-ensured" ] \
   && [ ! -d "/usr/share/icons/${XCURSOR_THEME}/cursors" ] \
   && [ ! -d "$HOME/.local/share/icons/${XCURSOR_THEME}/cursors" ]; then
    (mios-cursor-ensure >/dev/null 2>&1 &) 2>/dev/null || true
fi

# wsl.exe-spawned bash sessions bypass pam_systemd, so the user-systemd
# manager doesn't see XCURSOR_*. Push them in via `systemctl --user
# import-environment` when the user manager is running. Idempotent;
# noop if systemctl --user is unreachable (early boot, no logind).
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user import-environment XCURSOR_THEME XCURSOR_SIZE 2>/dev/null || true
fi
