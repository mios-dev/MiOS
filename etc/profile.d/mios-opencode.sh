#!/bin/sh
# AI-hint: Points the interactive opencode TUI/CLI at the MiOS local inference backend by exporting OPENCODE_CONFIG, so opencode resolves the MiOS provider (mios-...
# AI-doc: usr/share/doc/mios/manual/profile.d.md

if [ -z "${OPENCODE_CONFIG-}" ] && [ -r /etc/mios/opencode/opencode.json ]; then
    OPENCODE_CONFIG=/etc/mios/opencode/opencode.json
    export OPENCODE_CONFIG
fi
