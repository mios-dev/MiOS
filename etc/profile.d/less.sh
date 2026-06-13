# AI-hint: Configures the LESSOPEN environment variable to pipe input through lesspipe.sh, enabling interactive viewing of remote or dynamic content via the less pager.
# less initialization script (sh)

# All less.*sh files should have the same semantics!

if [ -z "$LESSOPEN" ] && [ -x /usr/bin/lesspipe.sh ]; then
    # The '||' here is intentional, see rhbz#1254837.
    export LESSOPEN="||/usr/bin/lesspipe.sh %s"
fi
