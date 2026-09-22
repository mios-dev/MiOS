#!/usr/bin/env bash
# Provision the runnable MiOS development core without starting host services.
set -euo pipefail

readonly ROOT=/workspaces/MiOS
readonly RUST_MANIFEST="${ROOT}/src/mios-rs/Cargo.toml"
readonly TARGET_DIR=/opt/mios/target
readonly INSTALL_DIR=/opt/mios/bin
readonly AGENT_PIPE_PYTHON=/opt/mios/agent-pipe-venv/bin/python

if [[ ! -f "${RUST_MANIFEST}" ]]; then
    echo "[devcontainer:core] Missing miosd workspace manifest: ${RUST_MANIFEST}" >&2
    exit 1
fi
if [[ ! -x "${AGENT_PIPE_PYTHON}" ]]; then
    echo "[devcontainer:core] Missing agent-pipe runtime: ${AGENT_PIPE_PYTHON}" >&2
    exit 1
fi

echo "[devcontainer:core] Verifying agent-pipe runtime..."
"${AGENT_PIPE_PYTHON}" -c 'import fastapi, httpx, mcp, pydantic, uvicorn'

echo "[devcontainer:core] Initializing MiOS developer state..."
install -d -m 0755 \
    "${HOME}/.local/state/mios/agent-pipe" \
    "${HOME}/.local/state/mios/daemon" \
    "${HOME}/.local/share/mios/agent-pipe" \
    "${HOME}/.cache/mios/agent-pipe"

echo "[devcontainer:core] Building source-matched miosd..."
sudo install -d -o "${USER}" -g "${USER}" -m 0755 "${TARGET_DIR}" "${INSTALL_DIR}"
CARGO_TARGET_DIR="${TARGET_DIR}" cargo build --manifest-path "${RUST_MANIFEST}" --release --package miosd
sudo install -m 0755 "${TARGET_DIR}/release/miosd" "${INSTALL_DIR}/miosd"
sudo ln -sfn "${INSTALL_DIR}/miosd" /usr/local/bin/miosd
miosd --help >/dev/null

echo "[devcontainer:core] MiOS development core is ready."
