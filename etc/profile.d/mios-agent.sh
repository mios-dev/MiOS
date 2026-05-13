#!/bin/sh
# /etc/profile.d/mios-agent.sh
# MiOS agent shell integration: @-prefix widget for bash and zsh.
# POSIX-compatible bootstrap; bash- and zsh-specific blocks gated by version vars.

# Ensure the @ binary is on PATH.
case ":${PATH}:" in
    *":/usr/bin:"*) ;;
    *) PATH="/usr/bin:${PATH}"; export PATH ;;
esac

# Interactive shell only; no-op in scripts.
case "$-" in *i*) ;; *) return 0 2>/dev/null || exit 0 ;; esac

# ---- bash ----
if [ -n "${BASH_VERSION-}" ]; then
    __mios_at_dispatch() {
        case "${READLINE_LINE}" in
            '@'*)
                _q="${READLINE_LINE#@}"
                _q="${_q# }"
                # Replace the line with a real command: '@' binary + quoted arg.
                READLINE_LINE="@ $(printf %q "$_q")"
                READLINE_POINT=${#READLINE_LINE}
                ;;
        esac
    }
    bind -x '"\C-x@": __mios_at_dispatch' 2>/dev/null || true
    bind '"\r": "\C-x@\C-m"'              2>/dev/null || true
fi

# ---- zsh ----
if [ -n "${ZSH_VERSION-}" ]; then
    __mios_at_widget() {
        case "$BUFFER" in
            '@'*)
                local q="${BUFFER#@}"
                q="${q# }"
                BUFFER="@ ${(q)q}"
                CURSOR=${#BUFFER}
                ;;
        esac
        zle .accept-line
    }
    zle -N __mios_at_widget 2>/dev/null && bindkey '^M' __mios_at_widget
fi

# Common env exports
export MIOS_AGENT_DEFAULT="${MIOS_AGENT_DEFAULT:-hermes}"
if [ -r /etc/mios/agents/.local_key ]; then
    MIOS_AGENT_LOCAL_KEY="$(cat /etc/mios/agents/.local_key)"
    export MIOS_AGENT_LOCAL_KEY
fi

# Helper for repo switching (cannot modify parent env from a binary; alias it).
mios_repo_use() {
    case "$1" in
        main)
            unset GIT_DIR GIT_WORK_TREE
            echo "mios repo: main"
            ;;
        bootstrap)
            export GIT_DIR=/.mios-bootstrap.git GIT_WORK_TREE=/
            echo "mios repo: bootstrap"
            ;;
        *)
            echo "usage: mios_repo_use {main|bootstrap}" >&2
            return 2
            ;;
    esac
}
alias 'mios-repo'='mios_repo_use'
