#!/bin/sh
# AI-hint: Points the interactive opencode TUI/CLI at the MiOS local inference backend by exporting OPENCODE_CONFIG, so opencode resolves the MiOS provider (mios-llm-light :11450) + the mios-opencode model instead of prompting for a cloud login.
# AI-related: /etc/mios/opencode/opencode.json, opencode, mios-opencode-gateway, mios-llm-light, usr/lib/mios/agents/opencode-gateway/server.py
# /etc/profile.d/mios-opencode.sh
# MiOS opencode shell integration. The mios-opencode-gateway.service sets
# OPENCODE_CONFIG for its headless `opencode run`, but an interactive `opencode`
# (the TUI, or a manual `opencode run`) inherits no such env and would fall back
# to opencode's own default config -- which has NO MiOS provider, so it prompts
# for a cloud provider/login and never reaches the local backend. Exporting the
# SAME admin config here makes the TUI use the local MiOS lane out of the box
# (operator: "setup opencode to use the backend properly so we can also use the
# TUI"). The config is the read-only admin SoT (root:mios-ai 0640, readable by
# members of the mios-ai group); opencode writes session state to the user's XDG
# dirs, not here.

# Only set when not already overridden and the MiOS config is present + readable.
if [ -z "${OPENCODE_CONFIG-}" ] && [ -r /etc/mios/opencode/opencode.json ]; then
    OPENCODE_CONFIG=/etc/mios/opencode/opencode.json
    export OPENCODE_CONFIG
fi
