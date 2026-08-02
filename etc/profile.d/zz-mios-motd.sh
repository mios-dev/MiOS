# AI-hint: Dispatches the interactive shell startup verb defined in mios.toml [terminal.startup] to the terminal on login, ensuring the MiOS dashboard or "mini" view is rendered only in valid TTY sessions.
# AI-related: /etc/mios/mios.toml, /usr/share/mios/mios.toml, mios-motd, mios-env, mios-verbs
# AI-functions: _mios_startup_verb

[ -n "${PS1:-}" ] || return 0
[ -t 0 ] && [ -t 1 ] || return 0
[ -z "${MIOS_MOTD_SHOWN:-}" ] || return 0
[ -z "${TMUX:-}" ] || return 0
[ -z "${STY:-}" ] || return 0
[ -z "${MIOS_SKIP_MOTD:-}" ] || return 0

_mios_startup_verb() {
    local toml verb section_started key val
    for toml in \
        "${HOME:-/var/home/mios}/.config/mios/mios.toml" \
        /etc/mios/mios.toml \
        /usr/share/mios/mios.toml; do
        [ -r "$toml" ] || continue
        verb="$(awk '
            BEGIN { in_section=0; linux_val=""; verb_val="" }
            /^\[/ {
                line=$0; sub(/[[:space:]]*#.*$/, "", line)
                in_section = (line == "[terminal.startup]") ? 1 : 0
                next
            }
            in_section && /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=/ {
                line=$0; sub(/[[:space:]]*#.*$/, "", line)
                eq=index(line, "="); if (eq==0) next
                key=substr(line, 1, eq-1); val=substr(line, eq+1)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
                gsub(/^"|"$/, "", val)
                if (key == "linux") linux_val = val
                if (key == "verb")  verb_val  = val
            }
            END { if (linux_val != "") print linux_val; else print verb_val }
        ' "$toml" 2>/dev/null)"
        if [ -n "$verb" ]; then
            printf '%s' "$verb"
            return 0
        fi
    done
    printf 'mini'
}

_mios_verb="$(_mios_startup_verb)"
if [ -n "$_mios_verb" ]; then
    if type mios 2>/dev/null | head -1 | grep -q 'function'; then
        mios "$_mios_verb"
    fi
fi

MIOS_MOTD_SHOWN=1
export MIOS_MOTD_SHOWN
unset _mios_verb
