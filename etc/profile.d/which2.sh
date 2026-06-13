# AI-hint: Configures the 'which' command alias across different shells (bash, ksh, zsh) to ensure it correctly resolves functions and aliases in the current environment.
# shellcheck shell=sh
# Initialization script for bash, sh, mksh and ksh

if [ -r /proc/$$/exe ]; then
    SHELLNAME=$(basename $(readlink /proc/$$/exe))
else
    SHELLNAME="unknown"
fi
case "$SHELLNAME" in
*ksh*|zsh)
    alias which='alias | /usr/bin/which --tty-only --read-alias --show-tilde --show-dot'
    ;;
bash|sh)
    alias which='(alias; declare -f) | /usr/bin/which --tty-only --read-alias --read-functions --show-tilde --show-dot'
    ;;
*)
    ;;
esac
