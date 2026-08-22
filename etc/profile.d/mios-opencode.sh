#!/bin/sh
# AI-hint: Points the interactive opencode TUI/CLI at the MiOS local inference backend by exporting OPENCODE_CONFIG, so opencode resolves the MiOS provider (mios-...
# AI-doc: usr/share/doc/mios/manual/_harvest/etc_profile_d_mios_opencode_sh.md

if [ -z "${OPENCODE_CONFIG-}" ] && [ -r /etc/mios/opencode/opencode.json ]; then
    OPENCODE_CONFIG=/etc/mios/opencode/opencode.json
    export OPENCODE_CONFIG
fi
