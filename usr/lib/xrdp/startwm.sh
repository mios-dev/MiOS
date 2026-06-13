#!/bin/sh
# AI-hint: Executes the GNOME desktop environment for xrdp sessions, configuring XDG environment variables and cursor themes to initialize the graphical user interface for remote users.
if [ -r /etc/profile ]; then . /etc/profile; fi
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=GNOME
export XDG_SESSION_DESKTOP=gnome
export GNOME_SHELL_SESSION_MODE=gnome
export XCURSOR_THEME=Bibata-Modern-Classic
export XCURSOR_SIZE=24
exec gnome-session
