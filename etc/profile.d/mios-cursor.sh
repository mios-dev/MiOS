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
# Operator-flagged 2026-05-11: "bibata cursor is NOT global at all!!
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
export XCURSOR_SIZE="${XCURSOR_SIZE:-16}"

# wsl.exe-spawned bash sessions bypass pam_systemd, so the user-systemd
# manager doesn't see XCURSOR_*. Push them in via `systemctl --user
# import-environment` when the user manager is running. Idempotent;
# noop if systemctl --user is unreachable (early boot, no logind).
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user import-environment XCURSOR_THEME XCURSOR_SIZE 2>/dev/null || true
fi
