# /etc/profile.d/mios-verbs.sh
#
# `mios <verb>` dispatcher for interactive bash shells inside MiOS-DEV.
# Operator 2026-05-09 image #21: typing `mios dash` produced
# "bash: mios: command not found" because /usr/bin/mios is the Python
# AI agent shell (takes prompts), not a verb dispatcher.
#
# Solution: define `mios()` as a shell FUNCTION that intercepts the
# canonical verbs (build / config / dash / dev / pull / update / help)
# and routes them to the appropriate /usr/libexec/mios/ helper. Any
# OTHER first-arg falls through to /usr/bin/mios (the AI agent) so
# `mios "fix this code"` still works as a prompt.
#
# Function (not script) so the routed helpers can use `exec` without
# replacing the operator's interactive shell.
#
# Conditional: only defines `mios()` for interactive shells. Cron and
# background scripts that source /etc/profile see /usr/bin/mios
# directly (the AI agent).
[ -n "${PS1:-}" ] || return 0

mios() {
    case "${1:-help}" in
        mini)
            shift
            # MINI dashboard -- compact framed banner + fastfetch row
            # set, fits inside the 80x20 portal. Auto-fired on every
            # interactive shell spawn via /etc/profile.d/zz-mios-motd.sh
            # which dispatches the verb declared in
            # mios.toml [terminal.startup].linux (vendor default = mini).
            # Operator 2026-05-10: "have launch be the mini-dashboard
            # ... NOT PRINT ON LAUNCH" -- the dotfile fires this verb,
            # the verb's command output is what renders.
            local _dash=""
            for _c in /usr/libexec/mios/mios-dashboard.sh \
                      /mnt/m/usr/libexec/mios/mios-dashboard.sh; do
                [[ -x "$_c" ]] && { _dash="$_c"; break; }
            done
            if [[ -n "$_dash" ]]; then
                # --mini flag = MODE=mini in dashboard.sh: NO ASCII
                # banner, NO Stack section, NO Tree git-state, NO verb
                # hints, single-line up/down service count recap.
                # Fits 80x20 with rows free for the prompt.
                "$_dash" --mini "$@"
            else
                echo "mios mini: mios-dashboard.sh not found" >&2
                return 127
            fi
            ;;
        dash|dashboard)
            shift
            # FULL dashboard -- ASCII banner + fastfetch + Quadlet
            # service status + git/working-tree state + endpoint
            # health. Operator-triggered explicitly; doesn't fit in
            # 80x20 so NOT auto-fired on shell spawn.
            local _dash=""
            for _c in /usr/libexec/mios/mios-dashboard.sh \
                      /mnt/m/usr/libexec/mios/mios-dashboard.sh; do
                [[ -x "$_c" ]] && { _dash="$_c"; break; }
            done
            if [[ -n "$_dash" ]]; then
                # Force the full path: services block + non-compact
                # ASCII banner + extended sys info. mios-dashboard.sh
                # already supports this via env toggles.
                MIOS_DASH_SERVICES=1 MIOS_COMPACT=0 "$_dash" "$@"
            else
                echo "mios dash: mios-dashboard.sh not found" >&2
                return 127
            fi
            ;;
        build)
            shift
            if [[ -x /usr/libexec/mios/mios-build-driver ]]; then
                /usr/libexec/mios/mios-build-driver "$@"
            elif [[ -x /mnt/m/usr/libexec/mios/mios-build-driver ]]; then
                /mnt/m/usr/libexec/mios/mios-build-driver "$@"
            else
                echo "mios build: mios-build-driver not found" >&2
                return 127
            fi
            ;;
        config)
            shift
            if [[ -x /usr/libexec/mios/mios-configurator-launch ]]; then
                /usr/libexec/mios/mios-configurator-launch "$@"
            elif [[ -x /mnt/m/usr/libexec/mios/mios-configurator-launch ]]; then
                /mnt/m/usr/libexec/mios/mios-configurator-launch "$@"
            else
                echo "mios config: mios-configurator-launch not found" >&2
                return 127
            fi
            ;;
        dev)
            # Inside MiOS-DEV already -- `mios dev` is a no-op (drops
            # the operator into a fresh interactive bash if invoked
            # explicitly).  On Windows side this verb wsl's into the
            # dev VM; from inside the dev VM we ARE that target.
            shift
            exec bash "$@"
            ;;
        pull)
            shift
            # `mios pull` -- update mios.git working tree at /mnt/m/.
            if [[ -d /mnt/m/.git ]]; then
                ( cd /mnt/m && git fetch --depth=1 origin main && git reset --hard FETCH_HEAD )
            else
                echo "mios pull: /mnt/m is not a git working tree" >&2
                return 1
            fi
            ;;
        update)
            shift
            # `mios update` -- re-run bootstrap inside MiOS-DEV. Touches
            # /mnt/m only; full irm|iex re-run is operator-side on Windows.
            if [[ -x /mnt/m/MiOS/bin/mios-update.ps1 ]]; then
                echo "mios update: re-run irm|iex Get-MiOS.ps1 from Windows side." >&2
            fi
            mios pull
            ;;
        help|"-h"|"--help"|"")
            cat <<'EOH'

  MiOS verbs (inside MiOS-DEV):
    mios mini    -- compact 80x20 framed banner + fastfetch (auto on shell spawn)
    mios dash    -- FULL dashboard: ASCII banner + services + extended sys specs
    mios build   -- run /usr/libexec/mios/mios-build-driver (OCI image build)
    mios config  -- launch the configurator (mios.html in default browser)
    mios dev     -- nested bash session (you're already in MiOS-DEV)
    mios pull    -- git fetch + reset M:\ to origin/main
    mios update  -- mios pull + hint to re-run bootstrap from Windows
    mios help    -- this list
    mios <prompt>-- pass to the AI agent (/usr/bin/mios)

EOH
            ;;
        *)
            # Not a known verb -- forward everything to the AI agent.
            command mios "$@"
            ;;
    esac
}
export -f mios 2>/dev/null || true

# Completion for `mios <TAB>` -- list the canonical verbs. Anything
# typed after the verb falls through to the AI agent's prompt, so we
# only complete position 1.
_mios_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "mini dash build config dev pull update help" -- "$cur") )
    fi
}
complete -F _mios_complete mios

# ── @<query> bash prompt shortcut for Hermes ───────────────────────────────
# Operator-requested 2026-05-11: type `@how do I X` (no space after @) and
# it routes to the live MiOS agent (Hermes-Agent on :8642 via /usr/bin/mios).
# Why `@`: bash leaves it untouched at command-position (no expansion).
# Why NOT alternatives:
#   ~  -- bash expands to $HOME (`~/Documents` -> `/var/home/mios/Documents`)
#   !  -- history expansion (`!!`, `!ls`)
#   ?  -- glob wildcard at command-position
#   :  -- shell builtin (no-op)
#   #  -- comment marker
# Mechanism: bash's `command_not_found_handle` fires whenever the shell
# can't resolve a command-position word. We inspect the first token; if
# it starts with `@` we strip the `@`, glue it to the remaining args, and
# forward to /usr/bin/mios (the OpenAI-compatible agent CLI). Anything
# else gets the default "command not found" error.
#
# Examples:
#   @hello                       -> mios hello
#   @how do I list pods          -> mios how do I list pods
#   @"explain this code"         -> mios explain this code
#   @--no-tools quick question   -> mios --no-tools quick question
command_not_found_handle() {
    if [[ "${1:-}" == @* ]] && [[ "${1}" != "@" ]]; then
        local first="${1#@}"
        shift
        if [[ -x /usr/bin/mios ]]; then
            /usr/bin/mios "$first" "$@"
            return $?
        fi
    fi
    # Default behavior: 127 with stderr message, matching bash's
    # untouched-shell fallback.
    printf '%s: %s: command not found\n' "${BASH_SOURCE[0]##*/}" "${1:-}" >&2
    return 127
}
export -f command_not_found_handle 2>/dev/null || true
