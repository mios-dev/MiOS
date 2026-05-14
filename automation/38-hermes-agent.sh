#!/bin/bash
# automation/38-hermes-agent.sh
#
# Install Hermes-Agent DIRECTLY onto the MiOS root filesystem -- not as
# a container. Operator directive 2026-05-13: "Hermes-Agent should be
# installed on the Local MiOS-DEV machine directly at the root
# directory and ALL other MiOS Images/deployment types".
#
# Rationale: Hermes-Agent IS the live MiOS agent at `/` (AGENTS.md §6).
# A container boundary between the agent and the system it operates on
# meant the agent couldn't see the real root FS / systemd / git tree
# without bind-mount gymnastics. A direct host install removes that
# boundary: the agent runs as a host systemd service (hermes-agent.
# service), sees `/` natively, and uses the ollama CONTAINER as a
# swappable OpenAI-compatible inference backend.
#
# CRITICAL: this script MUST NOT fail the OCI build. Network egress,
# PyPI, and git are best-effort at build time -- if any step fails the
# script logs a warning and `exit 0`s. hermes-agent.service carries
# ConditionPathExists so it cleanly no-ops on hosts where the install
# didn't land; `mios update` / a firstboot retry can complete it later.
#
# TOML-first: HERMES_REPO/REF resolve from MIOS_HERMES_AGENT_* env vars
# (exported by tools/lib/userenv.sh from mios.toml [ai].hermes_agent_*),
# with the canonical upstream as the `:-` shell default -- the same
# pattern 37-ollama-prep.sh uses for MIOS_OLLAMA_BAKE_MODELS.
#
# NO `set -e` -- a sub-failure here must never cascade into a build
# failure. Explicit guards + `exit 0` everywhere.
set -uo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[38-hermes-agent] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

HERMES_REPO="${MIOS_HERMES_AGENT_REPO:-https://github.com/NousResearch/hermes-agent.git}"
HERMES_REF="${MIOS_HERMES_AGENT_REF:-main}"
VENV_ROOT=/usr/lib/mios/hermes-agent          # vendor code (FHS /usr/lib)
VENV_DIR="${VENV_ROOT}/.venv"
BIN_DIR="${VENV_ROOT}/bin"

log "[38-hermes-agent] direct install: repo=${HERMES_REPO} ref=${HERMES_REF}"

# Tooling preflight -- python3 + pip + git must all be present. They're
# pulled by [packages.base] (git) + policycoreutils-python-utils
# (python3). If any is missing, skip cleanly rather than die.
_missing=""
for tool in python3 git; do
    command -v "$tool" >/dev/null 2>&1 || _missing="${_missing} ${tool}"
done
if [[ -n "$_missing" ]]; then
    warn "[38-hermes-agent] missing build tools:${_missing} -- skipping direct install (hermes-agent.service will no-op via ConditionPathExists)"
    exit 0
fi

install -d -m 0755 "${VENV_ROOT}" "${BIN_DIR}" || { warn "[38-hermes-agent] mkdir ${VENV_ROOT} failed -- skipping"; exit 0; }

# Build the venv. pip install directly from the git ref -- no editable
# checkout, no leftover src tree in the image.
if ! python3 -m venv "${VENV_DIR}" 2>/dev/null; then
    warn "[38-hermes-agent] python3 -m venv failed -- skipping direct install"
    exit 0
fi

# `pip install git+URL@ref` plus aiohttp -- single step, network
# best-effort. aiohttp is REQUIRED by hermes-agent's api_server adapter
# (the OpenAI /v1 surface). The base package doesn't pull it as a hard
# dep, so the gateway starts but logs "API Server: aiohttp not installed
# / No adapter available for api_server" and /v1 never comes up
# (operator-confirmed 2026-05-14). Installing it explicitly alongside.
# --no-input keeps it non-interactive; failure here is non-fatal.
if "${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check \
        "git+${HERMES_REPO}@${HERMES_REF}" aiohttp 2>&1 | tail -5; then
    :
else
    warn "[38-hermes-agent] pip install git+${HERMES_REPO}@${HERMES_REF} + aiohttp failed (network? PyPI?) -- removing partial venv, skipping"
    rm -rf "${VENV_DIR}"
    exit 0
fi

# The pip install drops a `hermes` entry-point into the venv's bin.
# Verify it landed; symlink it to a stable vendor path the
# /usr/bin/hermes wrapper + hermes-agent.service both reference.
if [[ -x "${VENV_DIR}/bin/hermes" ]]; then
    ln -sf "${VENV_DIR}/bin/hermes" "${BIN_DIR}/hermes"
    log "[38-hermes-agent] installed: ${VENV_DIR}/bin/hermes -> ${BIN_DIR}/hermes"
    record_version "hermes-agent" "${HERMES_REF}" "$(${VENV_DIR}/bin/hermes --version 2>&1 | head -1)" 2>/dev/null || true
else
    warn "[38-hermes-agent] pip succeeded but no 'hermes' entry-point in venv -- skipping symlink"
    exit 0
fi

log "[38-hermes-agent] done -- runtime: hermes-agent.service (gateway mode); backend = mios.toml [ai].hermes_backend_url"
exit 0
