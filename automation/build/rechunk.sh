#!/usr/bin/env bash
# AI-hint: CI OCI rechunking step for optimal Day-2 updates (CONV-14).
# Gated on MIOS_CONV_IMAGE_RECHUNK_ENABLE=true.
# automation/build/rechunk.sh

set -euo pipefail

RECHUNK_ENABLE="${MIOS_CONV_IMAGE_RECHUNK_ENABLE:-false}"

if [[ "$RECHUNK_ENABLE" != "true" ]]; then
    echo "rechunk disabled"
    exit 0
fi

# Run chunked compose
SRC_DIGEST=$(podman inspect mios-bootc:latest --format '{{.Digest}}')

podman unshare rpm-ostree experimental compose build-chunked-oci \
  --bootc --format-version=1 \
  --from="${SRC_DIGEST}" \
  --output containers-storage:mios-bootc:rechunked

# Assign AI-sidecar xattrs for fine-grained chunking
setfattr -n user.component -v ai-sidecar /usr/lib/mios/agent-pipe/ 2>/dev/null || true
setfattr -n user.component -v ai-sidecar /usr/share/mios/llamacpp/ 2>/dev/null || true
setfattr -n user.component -v llm-models /var/lib/mios/models/ 2>/dev/null || true

echo "Rechunked image created: mios-bootc:rechunked"
exit 0
