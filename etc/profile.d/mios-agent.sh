#!/bin/sh
# AI-hint: Configures shell environment for MiOS agents by injecting @-prefix command dispatching, setting MIOS_AGENT_DEFAULT, and providing the mios_repo_use helper...
# AI-doc: usr/share/doc/mios/manual/_harvest/etc_profile_d_mios_agent_sh.md

case ":${PATH}:" in
    *":/usr/bin:"*) ;;
    *) PATH="/usr/bin:${PATH}"; export PATH ;;
esac

case "$-" in *i*) ;; *) return 0 2>/dev/null || exit 0 ;; esac

if [ -n "${BASH_VERSION-}" ]; then
    __mios_at_dispatch() {
        case "${READLINE_LINE}" in
            '@'*)
                _q="${READLINE_LINE#@}"
                _q="${_q# }"
                READLINE_LINE="@ $(printf %q "$_q")"
                READLINE_POINT=${#READLINE_LINE}
                ;;
        esac
    }
    bind -x '"\C-x@": __mios_at_dispatch' 2>/dev/null || true
    bind '"\r": "\C-x@\C-j"'              2>/dev/null || true
fi

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

export MIOS_AGENT_DEFAULT="${MIOS_AGENT_DEFAULT:-hermes}"
if [ -r /etc/mios/agents/.local_key ]; then
    MIOS_AGENT_LOCAL_KEY="$(cat /etc/mios/agents/.local_key)"
    export MIOS_AGENT_LOCAL_KEY
fi

mios_repo_use() {
    case "$1" in
        main)
            unset GIT_DIR GIT_WORK_TREE
            echo "Mios repo: main"
            ;;
        bootstrap)
            export GIT_DIR=/.mios-bootstrap.git GIT_WORK_TREE=/
            echo "Mios repo: bootstrap"
            ;;
        *)
            echo "Usage: mios_repo_use {main|bootstrap}" >&2
            return 2
            ;;
    esac
}
alias 'mios-repo'='mios_repo_use'
