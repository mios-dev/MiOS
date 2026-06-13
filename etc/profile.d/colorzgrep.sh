# AI-hint: Configures shell aliases for zgrep, zfgrep, and zegrep to enable automatic color output, ensuring consistent visual highlighting for compressed file searches in the terminal.
[ -f /usr/libexec/grepconf.sh ] || return

/usr/libexec/grepconf.sh -c || return
alias zgrep='zgrep --color=auto' 2>/dev/null
alias zfgrep='zfgrep --color=auto' 2>/dev/null
alias zegrep='zegrep --color=auto' 2>/dev/null
