# AI-hint: Defines shell aliases for xzgrep, xzegrep, and xzfgrep with automatic color highlighting to ensure consistent, readable output when searching compressed files.
# shellcheck shell=sh
/usr/libexec/grepconf.sh -c || return
alias xzgrep='xzgrep --color=auto' 2>/dev/null
alias xzegrep='xzegrep --color=auto' 2>/dev/null
alias xzfgrep='xzfgrep --color=auto' 2>/dev/null
