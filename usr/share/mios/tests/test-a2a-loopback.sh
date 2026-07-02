#!/usr/bin/env bash
# AI-hint: Shell entrypoint for the A2A federation loopback smoke test (roadmap B5 / T-066). Thin wrapper over mios-a2a-test --loopback: MiOS speaks to itself over the /a2a JSON-RPC surface and asserts a Message -> Task -> Artifact round-trip plus a recorded delegation chain. Operator runs this on a booted host.
# AI-related: usr/libexec/mios/mios-a2a-test, usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py
set -euo pipefail

# Resolve the agent-pipe endpoint from the SSOT bridge if present (install.env
# exports MIOS_PORT_AGENT_PIPE from mios.toml [ports]); mios-a2a-test falls back
# to the Law-5 default endpoint when the env is unset.
if [[ -z "${MIOS_AGENT_PIPE_URL:-}" && -r /etc/mios/install.env ]]; then
    # shellcheck disable=SC1091
    . /etc/mios/install.env || true
    if [[ -n "${MIOS_PORT_AGENT_PIPE:-}" ]]; then
        export MIOS_AGENT_PIPE_URL="http://127.0.0.1:${MIOS_PORT_AGENT_PIPE}"
    fi
fi

TESTER="$(command -v mios-a2a-test || echo /usr/libexec/mios/mios-a2a-test)"

echo "[test-a2a-loopback] driving A2A loopback round-trip via ${MIOS_AGENT_PIPE_URL:-default endpoint}"
exec "$TESTER" --loopback "$@"
