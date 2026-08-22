# AI-hint: !/usr/bin/env bash mios-flatpaks CLI: operator-friendly wrapper over `flatpak` for the system-wide Flatpak surface (list/add/remove/update/search/bake-stat...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_libexec_mios_flatpaks_manage_sh.md
set -euo pipefail

cmd="${1:-list}"
shift || true

case "$cmd" in
    list|ls)
        flatpak list --system --app --columns=application,version,branch,origin "$@"
        ;;
    add|install)
        if [[ -z "${1:-}" ]]; then
            echo "Mios-flatpaks add <flathub-ref>" >&2
            exit 2
        fi
        if [[ $EUID -ne 0 ]]; then exec sudo -E "$0" add "$@"; fi
        flatpak install --system --noninteractive --assumeyes flathub "$@"
        ;;
    remove|uninstall|rm)
        if [[ -z "${1:-}" ]]; then
            echo "Mios-flatpaks remove <flathub-ref>" >&2
            exit 2
        fi
        if [[ $EUID -ne 0 ]]; then exec sudo -E "$0" remove "$@"; fi
        flatpak uninstall --system --noninteractive --assumeyes "$@"
        ;;
    update|upgrade)
        if [[ $EUID -ne 0 ]]; then exec sudo -E "$0" update "$@"; fi
        flatpak update --system --noninteractive --assumeyes "$@"
        ;;
    search)
        if [[ -z "${1:-}" ]]; then
            echo "Mios-flatpaks search <term>" >&2
            exit 2
        fi
        flatpak search "$@"
        ;;
    bake-state)
        if [[ -r /usr/lib/mios/state/flatpak-bake.env ]]; then
            cat /usr/lib/mios/state/flatpak-bake.env
        else
            echo "No bake state recorded"
        fi
        ;;
    --help|-h|help)
        sed -n '2,15p' "$0" | sed 's/^# \?//'
        ;;
    *)
        echo "Mios-flatpaks: unknown verb '$cmd'" >&2
        exit 2
        ;;
esac
