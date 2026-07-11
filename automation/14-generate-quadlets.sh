#!/usr/bin/env bash
# AI-hint: Automatically generates Quadlet configuration files (.pod, .container, .network) from the mios.toml SSOT at image build time.
# AI-related: tools/generate-pod-quadlets.py, usr/share/mios/mios.toml, usr/share/containers/systemd/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source lib/common.sh -> tools/lib/userenv.sh so the generator sees the
# resolved MIOS_* env. generate-pod-quadlets.py resolves ${VAR:-default} via
# os.environ.get(VAR, default): WITHOUT these exports it bakes the FALLBACK
# (e.g. --max-model-len 16384, --kv-cache-dtype auto, --gpu-memory-utilization
# 0.45) and silently drops the entire [ai.vllm]/[ai.sglang] SSOT config -- the
# 256k / fp8-KV heavy lane never reaches the built artifact. common.sh's
# userenv source silently no-ops if the resolver is absent, so sourcing it here
# is strictly additive: best case the configured serve-flags bake in, worst
# case (no resolver) behaviour is identical to before. Mirrors 15-render-quadlets.
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

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
