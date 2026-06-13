# AI-hint: Configures the GPG_TTY environment variable for interactive shells to ensure GPG prompts and agents function correctly in non-interactive or multiplexed terminal sessions.
if [[ $- == *i* ]]; then
    export GPG_TTY=$(tty)
fi
