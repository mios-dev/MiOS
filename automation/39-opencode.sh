#!/bin/bash
# automation/39-opencode.sh
#
# Install opencode (https://opencode.ai) DIRECTLY onto the MiOS root
# filesystem -- not as a container. Mirrors automation/38-hermes-agent.sh's
# pattern: vendor binary lives under /usr/lib/mios/, exposed via a
# symlink under /usr/local/bin/.
#
# RATIONALE
# ─────────
# opencode is a code-specialist agent CLI (Anthropic-Claude-Code-style).
# MiOS uses it as a delegation TARGET for code-tagged subtasks via
# Hermes's ACP (Agent Coordination Protocol) integration -- NOT as a
# separate API server. The wiring:
#
#   Hermes-Agent (gateway, planner, /v1/chat/completions)
#     delegate_task(tasks=[
#       {goal: "audit /etc/foo", ...},                         # default child = qwen3:1.7b
#       {goal: "patch the bug at line 42 of file.py",
#        acp_command: "opencode", acp_args: ["--acp", "--stdio"]},   # opencode child
#     ])
#
# When acp_command is set on a task, Hermes spawns the named binary as
# a stdio subprocess, frames messages over ACP, and the binary acts as
# the agent for that task. opencode supports ACP natively per its docs.
#
# Operator configures the routing per their preference -- e.g. add to
# mios.toml [ai] a goal-pattern -> acp_command map, OR rely on the
# parallel-fanout skill's nudge to use acp_command="opencode" for
# code-tagged goals.
#
# DESIGN
# ──────
# * NO `set -e` -- a sub-failure here must NEVER cascade into a build
#   failure. Explicit guards + `exit 0` everywhere.
# * NO Hermes-style hermes-agent.service equivalent -- opencode is
#   spawned per-task by Hermes via stdio, not as a long-running daemon.
# * Network-best-effort at OCI build time: if the install script can't
#   download opencode (no egress, registry hiccup), we exit 0 cleanly
#   and the operator can re-run via `mios update` later.
set -uo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[39-opencode] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

OPENCODE_VERSION="${MIOS_OPENCODE_VERSION:-latest}"
INSTALL_ROOT=/usr/lib/mios/opencode             # vendor code (FHS /usr/lib)
INSTALL_BIN="${INSTALL_ROOT}/bin/opencode"
SHIM=/usr/local/bin/opencode

log "[39-opencode] direct install: version=${OPENCODE_VERSION} root=${INSTALL_ROOT}"

# Tooling preflight.
_missing=""
for tool in curl bash; do
    command -v "$tool" >/dev/null 2>&1 || _missing="${_missing} ${tool}"
done
if [[ -n "$_missing" ]]; then
    warn "[39-opencode] missing build tools:${_missing} -- skipping"
    exit 0
fi

install -d -m 0755 "${INSTALL_ROOT}" "$(dirname "${INSTALL_BIN}")" || {
    warn "[39-opencode] mkdir ${INSTALL_ROOT} failed -- skipping"
    exit 0
}

# opencode ships an install.sh that drops the binary into a
# user-controllable location. We point it at /usr/lib/mios/opencode
# via OPENCODE_INSTALL_DIR (per the script's documented env var).
# The install script tag is OPENCODE_VERSION (defaults to "latest").
INSTALL_URL="${MIOS_OPENCODE_INSTALL_URL:-https://opencode.ai/install}"
log "[39-opencode] downloading installer from ${INSTALL_URL}"
if ! curl -fsSL --max-time 60 "${INSTALL_URL}" -o /tmp/opencode-install.sh; then
    warn "[39-opencode] could not fetch installer (network or upstream issue) -- skipping"
    exit 0
fi

# Override the installer's default install dir + non-interactive mode.
# The installer respects OPENCODE_INSTALL_DIR (vendor convention).
OPENCODE_INSTALL_DIR="${INSTALL_ROOT}/bin" \
OPENCODE_VERSION="${OPENCODE_VERSION}" \
    bash /tmp/opencode-install.sh 2>&1 | tail -10 || {
    warn "[39-opencode] installer exited non-zero -- skipping; mios update will retry"
    rm -f /tmp/opencode-install.sh 2>/dev/null
    exit 0
}
rm -f /tmp/opencode-install.sh

# Verify the binary landed.
if [[ ! -x "${INSTALL_BIN}" ]]; then
    # Some opencode installers drop the binary at $OPENCODE_INSTALL_DIR
    # without a /bin/ subdir. Probe for it directly.
    for cand in "${INSTALL_ROOT}/bin/opencode" "${INSTALL_ROOT}/opencode"; do
        [[ -x "$cand" ]] && { INSTALL_BIN="$cand"; break; }
    done
fi
if [[ ! -x "${INSTALL_BIN}" ]]; then
    warn "[39-opencode] post-install: binary not found at ${INSTALL_BIN} or fallback paths -- skipping shim"
    exit 0
fi

# Symlink onto PATH so `opencode` works for the operator AND so
# Hermes's ACP transport can spawn it without a fully-qualified path.
ln -sf "${INSTALL_BIN}" "${SHIM}"
chmod 0755 "${SHIM}" 2>/dev/null || true

log "[39-opencode] installed: ${INSTALL_BIN} -> ${SHIM}"
log "[39-opencode] version: $("${INSTALL_BIN}" --version 2>&1 | head -1 || echo unknown)"
log "[39-opencode] integration: spawned by Hermes per-task via delegation.acp_command='opencode'"

exit 0
