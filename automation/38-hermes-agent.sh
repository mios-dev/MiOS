#!/bin/bash
# automation/38-hermes-agent.sh
#
# Install Hermes-Agent DIRECTLY onto the MiOS root filesystem -- not as
# a container. Operator directive 2026-05-13: "Hermes-Agent should be
# installed on the Local MiOS-DEV machine directly at the root
# directory and ALL other MiOS Images/deployment types".
#
# Rationale: Hermes-Agent IS the live MiOS agent at `/` (AGENTS.md §6).
# Running it as a Quadlet sidecar put a container boundary between the
# agent and the system it operates on -- the agent couldn't see the
# real root FS, the real systemd, the real git working tree without
# bind-mount gymnastics. A direct host install removes that boundary:
# the agent runs as a host systemd service, sees `/` natively, and
# uses the ollama CONTAINER (plus vllm / llama.cpp when present) purely
# as a swappable inference backend over the OpenAI-compatible /v1 wire.
#
# This script runs at OCI BUILD time (numbered 38-*, after
# 37-ollama-prep.sh so the inference backend's model seed is staged
# first). It installs into a vendor-owned venv under /usr/lib/ per FHS;
# /var + /etc paths for runtime state are declared via tmpfiles.d /
# the unit file, never written here (NO-MKDIR-IN-VAR law).
#
# Backend wiring is TOML-first: hermes-agent.service reads
# MIOS_AI_ENDPOINT / MIOS_AI_MODEL from /etc/profile.d/mios-env.sh
# (resolved from mios.toml [ai].* via tools/lib/userenv.sh).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# ── SSOT: read the pinned hermes-agent ref from mios.toml ─────────────
# [image.sidecars].hermes carries the upstream ref the project tracks;
# for the direct install we want the git ref, exposed as
# [ai].hermes_agent_ref (default: main). Falls back to main.
HERMES_REPO="$(mios_toml_get 'ai' 'hermes_agent_repo' 'https://github.com/NousResearch/hermes-agent.git')"
HERMES_REF="$(mios_toml_get 'ai'  'hermes_agent_ref'  'main')"

VENV_ROOT=/usr/lib/mios/hermes-agent           # vendor code (FHS /usr/lib)
SRC_DIR=/usr/lib/mios/hermes-agent/src
VENV_DIR="${VENV_ROOT}/.venv"

log "[38-hermes-agent] installing Hermes-Agent direct (repo=${HERMES_REPO} ref=${HERMES_REF})"

install -d -m 0755 "${VENV_ROOT}"

# Clone the agent source. Shallow + single-branch -- we only need the
# tree at HERMES_REF, not history. Tolerant of slow mirrors.
if [ ! -d "${SRC_DIR}/.git" ]; then
    git clone --depth=1 --single-branch --branch "${HERMES_REF}" \
        -c http.lowSpeedLimit=1 -c http.lowSpeedTime=30 \
        "${HERMES_REPO}" "${SRC_DIR}" \
        || { log "[38-hermes-agent] WARN: clone failed -- skipping direct install"; exit 0; }
else
    git -C "${SRC_DIR}" fetch --depth=1 origin "${HERMES_REF}" \
        && git -C "${SRC_DIR}" reset --hard FETCH_HEAD
fi

# Build the venv. python3 + pip ship in [packages.base]; uv is preferred
# when present (much faster, matches upstream's own tooling) but pip is
# the guaranteed fallback.
python3 -m venv "${VENV_DIR}"
if command -v uv >/dev/null 2>&1; then
    UV_PROJECT_ENVIRONMENT="${VENV_DIR}" uv pip install --python "${VENV_DIR}/bin/python" -e "${SRC_DIR}" \
        || "${VENV_DIR}/bin/pip" install -e "${SRC_DIR}"
else
    "${VENV_DIR}/bin/pip" install --no-input -e "${SRC_DIR}"
fi

# Stable entry-point symlink on PATH. /usr/bin/hermes already exists as
# the MiOS wrapper -- the DIRECT install exposes the real binary at a
# vendor path the wrapper can prefer when the host install is present.
install -d -m 0755 /usr/lib/mios/hermes-agent/bin
ln -sf "${VENV_DIR}/bin/hermes" /usr/lib/mios/hermes-agent/bin/hermes

log "[38-hermes-agent] Hermes-Agent installed direct at ${VENV_DIR}"
log "[38-hermes-agent] runtime: hermes-agent.service (gateway mode), backend = mios.toml [ai].endpoint"
