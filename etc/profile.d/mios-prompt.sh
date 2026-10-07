# AI-hint: Configures the Oh-My-Posh interactive shell prompt for bash and zsh by mapping the MiOS theme JSON to the shell's initialization sequence.
# AI-related: /usr/libexec/mios/oh-my-posh/oh-my-posh, /usr/share/mios/oh-my-posh/mios.omp.json, mios-prompt
# shellcheck shell=bash

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

# Render on shell startup, including SSH and existing tmux servers. Runtime
# projections are caller-owned; /usr stays immutable and user JSON cannot drift
# away from the layered TOML contract.
if [ "${MIOS_THEME_PROJECTED:-}" != 1 ] && [ -x /usr/libexec/mios/mios-unit-gen ] && [ -x /usr/libexec/mios/mios-gen ]; then
    _mios_projection="${XDG_RUNTIME_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}}/mios-terminal"
    [ -z "${MIOS_OMP_THEME:-}" ] || _mios_projection="${MIOS_OMP_THEME%/*}"
    if /usr/libexec/mios/mios-gen render-tmux-theme --runtime "$_mios_projection"; then
        export MIOS_OMP_THEME="$_mios_projection/mios.omp.json"
        [ -z "${TMUX:-}" ] || tmux source-file "$_mios_projection/tmux.conf"
    else
        printf 'MiOS: SSOT terminal projection failed\n' >&2
        return 1
    fi
    unset _mios_projection
fi
OMP_THEME="/usr/share/mios/oh-my-posh/mios.omp.json"
[ -n "${MIOS_OMP_THEME:-}" ] && [ -r "$MIOS_OMP_THEME" ] && OMP_THEME="$MIOS_OMP_THEME"
unset _u_omp

if [ -n "$OMP_BIN" ] && [ -x "$OMP_BIN" ] && [ -r "$OMP_THEME" ]; then
    _posh_cache="${XDG_CACHE_HOME:-$HOME/.cache}/oh-my-posh"
    if [ ! -d "$_posh_cache" ] || [ ! -w "$_posh_cache" ]; then
        mkdir -p "$_posh_cache" 2>/dev/null || true
    fi
    if [ ! -w "$_posh_cache" ]; then
        export POSH_CACHE_DIR="/tmp/posh-cache-${EUID:-$(id -u)}"
        mkdir -p "$POSH_CACHE_DIR" 2>/dev/null || true
    else
        export POSH_CACHE_DIR="$_posh_cache"
    fi
    if [ -n "${BASH_VERSION:-}" ]; then
        eval "$("$OMP_BIN" init bash --config="$OMP_THEME" --print)"
    elif [ -n "${ZSH_VERSION:-}" ]; then
        eval "$("$OMP_BIN" init zsh --config="$OMP_THEME" --print)"
    fi
    unset _posh_cache
fi
