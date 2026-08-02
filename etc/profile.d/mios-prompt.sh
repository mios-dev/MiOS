# AI-hint: Configures the Oh-My-Posh interactive shell prompt for bash and zsh by mapping the MiOS theme JSON to the shell's initialization sequence.
# AI-related: /usr/libexec/mios/oh-my-posh/oh-my-posh, /usr/share/mios/oh-my-posh/mios.omp.json, mios-prompt

[ -n "${PS1:-}" ] || return 0
[ -t 0 ] && [ -t 1 ] || return 0

OMP_BIN="$(command -v oh-my-posh 2>/dev/null)"
[ -z "$OMP_BIN" ] && [ -x /usr/libexec/mios/oh-my-posh/oh-my-posh ] \
    && OMP_BIN=/usr/libexec/mios/oh-my-posh/oh-my-posh
OMP_THEME="/usr/share/mios/oh-my-posh/mios.omp.json"

if [ -n "$OMP_BIN" ] && [ -x "$OMP_BIN" ] && [ -r "$OMP_THEME" ]; then
    if [ -n "${BASH_VERSION:-}" ]; then
        eval "$("$OMP_BIN" init bash --config="$OMP_THEME")"
    elif [ -n "${ZSH_VERSION:-}" ]; then
        eval "$("$OMP_BIN" init zsh --config="$OMP_THEME")"
    fi
fi
