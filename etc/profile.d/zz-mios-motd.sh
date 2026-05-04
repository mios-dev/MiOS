# /etc/profile.d/zz-mios-motd.sh
#
# MiOS MOTD trigger -- runs the live system dashboard once per
# interactive shell session at login. The `zz-` prefix forces this to
# sort last in /etc/profile.d/, so /etc/profile.d/mios-env.sh has
# already exported MIOS_* env vars by the time we render.
#
# Skipped when:
#   - $PS1 unset (non-interactive shell)
#   - stdin/stdout are not TTYs (cron, sudo, scripted bash -c, ...)
#   - $MIOS_MOTD_SHOWN already set (already shown in this session)
#   - $TMUX or $STY set (re-printing the dashboard inside every new
#     tmux/screen pane is too noisy; first parent shell already saw it)
#
# Compatible with bash, sh, zsh, dash login shells -- avoids any
# bashism so /bin/sh sources it cleanly.

[ -n "${PS1:-}" ] || return 0
[ -t 0 ] && [ -t 1 ] || return 0
[ -z "${MIOS_MOTD_SHOWN:-}" ] || return 0
[ -z "${TMUX:-}" ] || return 0
[ -z "${STY:-}" ] || return 0

if [ -x /usr/libexec/mios/mios-dashboard.sh ]; then
    /usr/libexec/mios/mios-dashboard.sh
    MIOS_MOTD_SHOWN=1
    export MIOS_MOTD_SHOWN
fi
