# AI-hint: Configures the LESSOPEN environment variable to pipe input through lesspipe.sh, enabling interactive viewing of remote or dynamic content via the less pager.


if [ -z "$LESSOPEN" ] && [ -x /usr/bin/lesspipe.sh ]; then
    export LESSOPEN="||/usr/bin/lesspipe.sh %s"
fi
