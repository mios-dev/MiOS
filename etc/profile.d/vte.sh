
[ -n "${BASH_VERSION:-}" ] || [ -n "${ZSH_VERSION:-}" ] || return 0

[[ $- == *i* ]] || return 0

[ "${VTE_VERSION:-0}" -ge 3405 ] || return 0

case "$TERM" in
    xterm*|vte*|gnome*) :;;
    *) return 0 ;;
esac

__vte_termprop_signal() {
    local errsv="$?"
    printf '\033]666;%s!\033\\' "$1"
    return $errsv
}

__vte_termprop_set() {
    local errsv="$?"
    printf '\033]666;%s=%s\033\\' "$1" "$2"
    return $errsv
}

__vte_termprop_reset() {
    local errsv="$?"
    printf '\033]666;%s\033\\' "$1"
    return $errsv
}

__vte_osc7 () {
    local errsv="$?"
    printf "\033]7;file://%s%s\033\\" "${HOSTNAME}" "$(/usr/libexec/vte-urlencode-cwd)"
    return $errsv
}

__vte_precmd() {
    local errsv="$?"
    __vte_termprop_set "vte.shell.postexec" "$?"
    __vte_termprop_signal "vte.shell.precmd"
    return $errsv;
}

__vte_prompt_command() {
    local errsv="$?"
    __vte_termprop_set "vte.shell.postexec" "$errsv"
    __vte_osc7
    local pwd='~'
    [ "$PWD" != "$HOME" ] && pwd=${PWD/#$HOME\//\~\/}
    pwd="${pwd//[[:cntrl:]]}"
    printf "\033]0;%s@%s:%s\033\\" "${USER}" "${HOSTNAME%%.*}" "${pwd}"
    __vte_termprop_signal "vte.shell.precmd"
    return $errsv
}

if [[ -n "${BASH_VERSION:-}" ]]; then

    if [[ "$(declare -p PROMPT_COMMAND 2>&1)" =~ "declare -a" ]]; then
        PROMPT_COMMAND+=(__vte_precmd)
        PROMPT_COMMAND+=(__vte_osc7)
    else
        PROMPT_COMMAND="__vte_prompt_command"
    fi
    PS0=$(__vte_termprop_signal "vte.shell.preexec")

    if [[ "$PS1" != *\]133\;* ]]; then

        PS1='\[\e]133;D;$?\e\\\e]133;A\e\\\]'"$PS1"'\[\e]133;B\e\\\]'

        PS0='\e]133;C\e\\\r'"${PS0:-}"
    fi

elif [[ -n "${ZSH_VERSION:-}" ]]; then
    precmd_functions+=(__vte_osc7)
    precmd_functions+=(__vte_precmd)

    if [[ "$PS1" != *\]133\;* ]]; then

        PS1=$'%{\e]133;D;%?\e\\\e]133;A\e\\%}'"$PS1"$'%{\e]133;B\e\\%}'

        __vte_preexec() {
            local errsv="$?"
            printf '\e]133;C\e\\\r'
            return $errsv
        }
        preexec_functions=(__vte_preexec $preexec $preexec_functions)
        unset preexec
    fi

fi

return 0
