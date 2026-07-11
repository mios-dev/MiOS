#!/usr/bin/env bash
# AI-hint: Automatically generates Quadlet configuration files (.pod, .container, .network) from the mios.toml SSOT at image build time.
# AI-related: tools/generate-pod-quadlets.py, usr/share/mios/mios.toml, usr/share/containers/systemd/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# DO NOT source userenv/common.sh here. generate-pod-quadlets.py resolves
# ${VAR:-default} via os.environ.get(VAR, default), so the generator's output is
# only DETERMINISTIC in a bare env (fallbacks). It MUST match the committed tree
# and `generate-pod-quadlets.py --check` (drift-gate check 13), both of which run
# bare -- sourcing userenv here bakes env-resolved values (e.g. --max-model-len
# 262144) that differ from the bare --check (16384) and FAIL the build at
# 38-drift-checks (STALE Quadlets). Runtime [ai.vllm]/[ai.sglang] config reaches
# the container at DEPLOY time via 15-render-quadlets / systemd EnvironmentFile
# expansion from install.env, NOT by baking at generate time. (Reverts c3d300c;
# the 256k lane is gated-off by default and unaffected on the install path.)
GEN_SCRIPT="${ROOT}/tools/generate-pod-quadlets.py"
TOML_FILE="${ROOT}/usr/share/mios/mios.toml"
OUT_DIR="${ROOT}/usr/share/containers/systemd"

echo "[14-generate-quadlets] Generating Quadlets from ${TOML_FILE} to ${OUT_DIR}..."

if [[ ! -f "$GEN_SCRIPT" ]]; then
    echo "[14-generate-quadlets] ERROR: generate-pod-quadlets.py not found at $GEN_SCRIPT" >&2
    exit 1
fi

# During OCI build, ROOT points to /tmp/build, but we want the generated Quadlets
# to end up in the system's /usr/share/containers/systemd directory.
# If /usr/share/containers/systemd is writable, we write directly to the target system.
# Otherwise, we fallback to writing in the build tree's usr/share/containers/systemd.
TARGET_DIR="/usr/share/containers/systemd"
if [[ -w "$TARGET_DIR" ]]; then
    OUT_DIR="$TARGET_DIR"
fi

MIOS_ROOT="$ROOT" MIOS_TOML="$TOML_FILE" MIOS_POD_OUT="$OUT_DIR" python3 "$GEN_SCRIPT"

echo "[14-generate-quadlets] Done."
