# AI-hint: Configures system locale environment variables and handles CJK fallback for terminal displays by parsing /etc/locale.conf and ~/.i18n to set LANG and LC_* variables.

unset LANG_backup

if [ -n "$(/usr/bin/locale 2>&1 1>/dev/null)" ]; then
    [ -z "$LANG" ] || LANG=C.utf8
    unset LC_ALL
    LC_CTYPE="C.utf8"
    LC_NUMERIC="C.utf8"
    LC_TIME="C.utf8"
    LC_COLLATE="C.utf8"
    LC_MONETARY="C.utf8"
    LC_MESSAGES="C.utf8"
    LC_PAPER="C.utf8"
    LC_NAME="C.utf8"
    LC_ADDRESS="C.utf8"
    LC_TELEPHONE="C.utf8"
    LC_MEASUREMENT="C.utf8"
    LC_IDENTIFICATION="C.utf8"
else
    LANG_backup="${LANG}"
fi

for config in /etc/locale.conf "${HOME}/.i18n"; do
    if [ -f "${config}" ]; then
        if [ -x /usr/bin/sed ]; then
            eval $(/usr/bin/sed -r -e 's/^[[:blank:]]*([[:upper:]_]+)=([[:print:][:digit:]\._-]+|"[[:print:][:digit:]\._-]+")/export \1=\2/;t;d' ${config})
        else
            [ -f "${config}" ] && . "${config}"
        fi
    fi
done

if [ -n "${LANG_backup}" ]; then
    LANG="${LANG_backup}"
fi

unset LANG_backup config

if [ -n "${LC_ALL}" ]; then
    if [ "${LC_ALL}" != "${LANG}" -a -n "${LANG}" ]; then
        export LC_ALL
    else
        unset LC_ALL
    fi
fi

if [ -n "${LANG}" ] && [ "${TERM}" = 'linux' ] && /usr/bin/tty | /usr/bin/grep --quiet -e '/dev/tty'; then
    if /usr/bin/grep --quiet -E -i -e '^.+\.utf-?8$' <<< "${LANG}"; then
        case ${LANG} in
            ja*)    LANG=en_US.UTF-8 ;;
            ko*)    LANG=en_US.UTF-8 ;;
            si*)    LANG=en_US.UTF-8 ;;
            zh*)    LANG=en_US.UTF-8 ;;
            ar*)    LANG=en_US.UTF-8 ;;
            fa*)    LANG=en_US.UTF-8 ;;
            he*)    LANG=en_US.UTF-8 ;;
            en_IN*) true             ;;
            *_IN*)  LANG=en_US.UTF-8 ;;
        esac
    else
        case ${LANG} in
            ja*)    LANG=en_US ;;
            ko*)    LANG=en_US ;;
            si*)    LANG=en_US ;;
            zh*)    LANG=en_US ;;
            ar*)    LANG=en_US ;;
            fa*)    LANG=en_US ;;
            he*)    LANG=en_US ;;
            en_IN*) true       ;;
            *_IN*)  LANG=en_US ;;
        esac
    fi

fi
