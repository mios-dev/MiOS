# AI-hint: Defines the `mios()` shell function to intercept and route canonical verbs (mini, dash, build, config, etc.) to specific `/usr/libexec/mios/` helpers while allowing non-standard arguments to pass to the AI agent.
# AI-related: mios-dashboard.sh, /usr/libexec/mios/mios-dashboard.sh, /usr/libexec/mios/mios-build-driver, /usr/libexec/mios/mios-configurator-launch, /usr/libexec/mios/mios-dotfiles, mios-dashboard, mios-build-driver, mios-configurator-launch, mios-verbs, mios-motd
# AI-functions: mios, _mios_complete, command_not_found_handle
[ -n "${PS1:-}" ] || return 0

mios() {
    case "${1:-help}" in
        mini)
            shift
            local _dash=""
            for _c in /usr/libexec/mios/mios-dashboard.sh \
                      /mnt/m/usr/libexec/mios/mios-dashboard.sh; do
                [[ -x "$_c" ]] && { _dash="$_c"; break; }
            done
            if [[ -n "$_dash" ]]; then
                "$_dash" --mini "$@"
            else
                echo "Mios mini: mios-dashboard.sh not found" >&2
                return 127
            fi
            ;;
        dash|dashboard)
            shift
            local _dash=""
            for _c in /usr/libexec/mios/mios-dashboard.sh \
                      /mnt/m/usr/libexec/mios/mios-dashboard.sh; do
                [[ -x "$_c" ]] && { _dash="$_c"; break; }
            done
            if [[ -n "$_dash" ]]; then
                MIOS_DASH_SERVICES=1 MIOS_COMPACT=0 "$_dash" "$@"
            else
                echo "Mios dash: mios-dashboard.sh not found" >&2
                return 127
            fi
            ;;
        mon|monitor)
            shift
            local _dash=""
            for _c in /usr/libexec/mios/mios-dashboard.sh \
                      /mnt/m/usr/libexec/mios/mios-dashboard.sh; do
                [[ -x "$_c" ]] && { _dash="$_c"; break; }
            done
            if [[ -n "$_dash" ]]; then
                "$_dash" --monitor "$@"
            else
                echo "Mios monitor: mios-dashboard.sh not found" >&2
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
                echo "Mios build: mios-build-driver not found" >&2
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
                echo "Mios config: mios-configurator-launch not found" >&2
                return 127
            fi
            ;;
        dotfiles)
            shift
            if [[ -x /usr/libexec/mios/mios-dotfiles ]]; then
                /usr/libexec/mios/mios-dotfiles "$@"
            elif [[ -x /mnt/m/usr/libexec/mios/mios-dotfiles ]]; then
                /mnt/m/usr/libexec/mios/mios-dotfiles "$@"
            else
                echo "Mios dotfiles: mios-dotfiles not found" >&2
                return 127
            fi
            ;;
        dev)
            shift
            exec bash "$@"
            ;;
        pull)
            shift
            if [[ -d /mnt/m/.git ]]; then
                ( cd /mnt/m && git fetch --depth=1 origin main && git reset --hard FETCH_HEAD )
            else
                echo "Mios pull: /mnt/m is not a git working tree" >&2
                return 1
            fi
            ;;
        update)
            shift
            if [[ -x /mnt/m/MiOS/bin/mios-update.ps1 ]]; then
                echo "Mios update: re-run irm|iex Get-MiOS.ps1 from Windows side" >&2
            fi
            mios pull
            ;;
        help|"-h"|"--help"|"")
            cat <<'EOH'

  MiOS verbs (inside MiOS-DEV):
    mios mini    -- compact 80x20 framed banner + fastfetch (auto on shell spawn)
    mios dash    -- FULL dashboard: ASCII banner + services + extended sys specs
    mios mon     -- resource monitor + unified stack table (refreshes every 5s)
    mios build   -- run /usr/libexec/mios/mios-build-driver (OCI image build)
    mios config  -- open the unified MiOS Settings surface (:8640/configure; offline HTML fallback)
    mios dotfiles [status|diff|sync] -- project the SSOT dotfiles (theme, btop, gitconfig, VS Code / Windows Terminal) to your HOME
    mios dev     -- nested bash session (you're already in MiOS-DEV)
    mios pull    -- git fetch + reset M:\ to origin/main
    mios update  -- mios pull + hint to re-run bootstrap from Windows
    mios help    -- this list
    mios <prompt>-- pass to the AI agent (/usr/bin/mios)

EOH
            ;;
        *)
            command mios "$@"
            ;;
    esac
}
export -f mios 2>/dev/null || true

_mios_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "mini dash build config dotfiles dev pull update help mon monitor" -- "$cur") )
    fi
}
complete -F _mios_complete mios

command_not_found_handle() {
    if [[ "${1:-}" == @* ]] && [[ "${1}" != "@" ]]; then
        local first="${1#@}"
        shift
        if [[ -x /usr/bin/mios ]]; then
            /usr/bin/mios "$first" "$@"
            return $?
        fi
    fi
    printf '%s: %s: command not found\n' "${BASH_SOURCE[0]##*/}" "${1:-}" >&2
    return 127
}
export -f command_not_found_handle 2>/dev/null || true
