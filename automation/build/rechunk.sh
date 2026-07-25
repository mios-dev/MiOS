#!/usr/bin/env bash
# AI-hint: CI OCI rechunking step for optimal Day-2 updates (CONV-14).
# Gated on MIOS_CONV_IMAGE_RECHUNK_ENABLE=true.
# AI-related: usr/share/mios/mios.toml, automation/98-drift-checks.sh
# automation/build/rechunk.sh

set -euo pipefail

RECHUNK_ENABLE="${MIOS_CONVERGE_IMAGE_RECHUNK_ENABLE:-false}"

if [[ "$RECHUNK_ENABLE" != "true" ]]; then
    echo "rechunk disabled"
    exit 0
fi

ROOT="${MIOS_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
MIOS_TOML="${MIOS_TOML:-$ROOT/usr/share/mios/mios.toml}"

# Resolve rechunk_max_layers from SSOT [build].rechunk_max_layers
RECHUNK_MAX_LAYERS=$(python3 -c "
import tomllib
with open('$MIOS_TOML', 'rb') as f:
    cfg = tomllib.load(f)
print(cfg.get('build', {}).get('rechunk_max_layers', 67))
" 2>/dev/null || echo 67)

# Resolve target image name from SSOT
TARGET_IMAGE="${MIOS_IMAGE_NAME:-$(python3 -c "
import tomllib
with open('$MIOS_TOML', 'rb') as f:
    cfg = tomllib.load(f)
print(cfg.get('image', {}).get('local_tag', 'localhost/mios:latest'))
" 2>/dev/null || echo 'localhost/mios:latest')}"

# Run chunked compose
SRC_DIGEST=$(podman inspect "${TARGET_IMAGE}" --format '{{.Digest}}' 2>/dev/null || echo "")

if [[ -n "$SRC_DIGEST" ]]; then
    podman unshare rpm-ostree experimental compose build-chunked-oci \
      --bootc --format-version=1 \
      --max-layers="${RECHUNK_MAX_LAYERS}" \
      --from="${SRC_DIGEST}" \
      --output "containers-storage:${TARGET_IMAGE}-rechunked"
fi

# Assign AI-sidecar xattrs for fine-grained chunking
setfattr -n user.component -v ai-sidecar /usr/lib/mios/agent-pipe/ 2>/dev/null || true
setfattr -n user.component -v ai-sidecar /usr/share/mios/llamacpp/ 2>/dev/null || true
setfattr -n user.component -v llm-models /var/lib/mios/models/ 2>/dev/null || true

echo "Rechunked image created: ${TARGET_IMAGE}-rechunked"
exit 0
