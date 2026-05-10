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
        dash|dashboard)
            shift
            if [[ -x /usr/libexec/mios/mios-dashboard.sh ]]; then
                /usr/libexec/mios/mios-dashboard.sh "$@"
            elif [[ -x /mnt/m/usr/libexec/mios/mios-dashboard.sh ]]; then
                /mnt/m/usr/libexec/mios/mios-dashboard.sh "$@"
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
    mios dash    -- show the MiOS dashboard (framed banner + fastfetch)
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
