#!/usr/bin/env bash
# Provision the runnable MiOS development core without starting host services.
set -euo pipefail

readonly ROOT=/workspaces/MiOS
readonly RUST_MANIFEST="${ROOT}/src/mios-rs/Cargo.toml"
readonly INSTALL_DIR=/opt/mios/bin
readonly AGENT_PIPE_PYTHON=/usr/lib/mios/agents/.venv/bin/python

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

echo "[devcontainer:core] Building upstream native workspaces..."
(cd "${ROOT}/src/mios-rs" && cargo build --release)
(cd "${ROOT}/tools/native" && cargo build --release --workspace --exclude mios-wallpaperd)
sudo install -d -m 0755 "${INSTALL_DIR}"
for binary in \
    "${ROOT}"/src/mios-rs/target/release/mios-* \
    "${ROOT}"/tools/native/target/release/mios-* \
    "${ROOT}"/tools/native/target/release/generate-names-registry; do
    [[ -x "${binary}" ]] || continue
    sudo install -m 0755 "${binary}" "${INSTALL_DIR}/$(basename "${binary}")"
done
sudo ln -sfn "${INSTALL_DIR}/miosd" /usr/local/bin/miosd
miosd --help >/dev/null

echo "[devcontainer:core] MiOS development core is ready."
