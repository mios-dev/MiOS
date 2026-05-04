# /etc/profile.d/mios-prompt.sh
#
# Initializes the MiOS-themed Oh-My-Posh prompt for every interactive
# bash login shell. zsh + fish are wired the same way via their own
# init lines below.
#
# Oh-My-Posh ships as a static Go binary at
#   /usr/libexec/mios/oh-my-posh/oh-my-posh
# (installed by automation/38-oh-my-posh.sh at build time -- not a
# Fedora RPM). The MiOS theme lives at
#   /usr/share/mios/oh-my-posh/mios.omp.json
# Both paths are guarded with -x / -r so a missing binary or theme
# (e.g. mid-build, or after a manual rm) silently falls back to the
# distro default prompt.
#
# Conditional: only initializes for interactive shells (PS1 set, stdio
# attached to a TTY). Background scripts and cron jobs that source
# /etc/profile keep their plain-bash prompt unchanged.

[ -n "${PS1:-}" ] || return 0
[ -t 0 ] && [ -t 1 ] || return 0

OMP_BIN="/usr/libexec/mios/oh-my-posh/oh-my-posh"
OMP_THEME="/usr/share/mios/oh-my-posh/mios.omp.json"

if [ -x "$OMP_BIN" ] && [ -r "$OMP_THEME" ]; then
    if [ -n "${BASH_VERSION:-}" ]; then
        eval "$("$OMP_BIN" init bash --config="$OMP_THEME")"
    elif [ -n "${ZSH_VERSION:-}" ]; then
        eval "$("$OMP_BIN" init zsh --config="$OMP_THEME")"
    fi
    # fish uses its own init.fish path; sourced from /etc/fish/config.fish
fi
