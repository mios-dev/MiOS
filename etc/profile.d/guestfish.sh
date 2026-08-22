# AI-hint: Upstream libguestfs profile snippet that sets the guestfish interactive prompt and output colours; shipped verbatim, MiOS adds only this header.
GUESTFISH_PS1='\[\e[1;32m\]><fs>\[\e[0;31m\] '
GUESTFISH_OUTPUT='\e[0m'
GUESTFISH_RESTORE="$GUESTFISH_OUTPUT"
GUESTFISH_INIT='\e[1;34m'
export GUESTFISH_PS1 GUESTFISH_OUTPUT GUESTFISH_RESTORE GUESTFISH_INIT
