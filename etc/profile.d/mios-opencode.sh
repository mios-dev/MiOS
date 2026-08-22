#!/bin/sh
# AI-hint: Points the interactive opencode TUI/CLI at the MiOS local inference backend by exporting OPENCODE_CONFIG, so opencode resolves the MiOS provider (mios-llm-light, port key `llm_light`) + the mios-opencode model instead of prompting for a cloud login.
# AI-related: /etc/mios/opencode/opencode.json, opencode, mios-opencode-gateway, mios-llm-light, usr/lib/mios/agents/opencode-gateway/server.py

if [ -z "${OPENCODE_CONFIG-}" ] && [ -r /etc/mios/opencode/opencode.json ]; then
    OPENCODE_CONFIG=/etc/mios/opencode/opencode.json
    export OPENCODE_CONFIG
fi
