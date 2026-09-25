# AI-hint: Configures the Oh-My-Posh interactive shell prompt for bash and zsh by mapping the MiOS theme JSON to the shell's initialization sequence.
# AI-related: /usr/libexec/mios/oh-my-posh/oh-my-posh, /usr/share/mios/oh-my-posh/mios.omp.json, mios-prompt

[ -n "${PS1:-}" ] || [ -n "${ZSH_VERSION:-}" ] || return 0
[ -t 0 ] && [ -t 1 ] || return 0

OMP_BIN="$(command -v oh-my-posh 2>/dev/null || true)"
[ -z "$OMP_BIN" ] && [ -x /usr/libexec/mios/oh-my-posh/oh-my-posh ] && OMP_BIN=/usr/libexec/mios/oh-my-posh/oh-my-posh
[ -z "$OMP_BIN" ] && [ -x /usr/bin/oh-my-posh ] && OMP_BIN=/usr/bin/oh-my-posh

# Seed user config directories from SSOT if missing
_u_omp="${HOME:-/root}/.config/oh-my-posh/mios.omp.json"
[ -f "$_u_omp" ] || { mkdir -p "$(dirname "$_u_omp")" 2>/dev/null && cp /usr/share/mios/oh-my-posh/mios.omp.json "$_u_omp" 2>/dev/null || true; }
_u_ff="${HOME:-/root}/.config/fastfetch/config.jsonc"
[ -f "$_u_ff" ] || { mkdir -p "$(dirname "$_u_ff")" 2>/dev/null && cp /usr/share/mios/fastfetch/config.jsonc "$_u_ff" 2>/dev/null || true; }
unset _u_ff

OMP_THEME="/usr/share/mios/oh-my-posh/mios.omp.json"
[ -r "$_u_omp" ] && OMP_THEME="$_u_omp"
unset _u_omp

if [ -n "$OMP_BIN" ] && [ -x "$OMP_BIN" ] && [ -r "$OMP_THEME" ]; then
    if [ -n "${BASH_VERSION:-}" ]; then
        eval "$("$OMP_BIN" init bash --config="$OMP_THEME")"
    elif [ -n "${ZSH_VERSION:-}" ]; then
        eval "$("$OMP_BIN" init zsh --config="$OMP_THEME")"
    fi
fi
