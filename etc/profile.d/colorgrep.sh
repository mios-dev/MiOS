# AI-hint: Configures shell environment aliases for grep, egrep, and fgrep to enable automatic color output for terminal-based text searching and filtering.
# color-grep initialization

/usr/libexec/grepconf.sh -c || return

alias grep='grep --color=auto' 2>/dev/null
alias egrep='grep -E --color=auto' 2>/dev/null
alias fgrep='grep -F --color=auto' 2>/dev/null
