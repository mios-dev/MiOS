#!/bin/bash
# 37-ollama-prep: Embed default LLM models during build
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

# This script is intended for local builds to "bake in" the default coding model.
# It installs a temporary ollama binary, pulls the model, and cleans up.

# Only run if not already present (idempotency)
if [ -d "/var/lib/ollama/models" ] && [ "$(ls -A /var/lib/ollama/models)" ]; then
    log "Default models already present, skipping."
    exit 0
fi

log "Downloading default models: qwen2.5-coder:7b + nomic-embed-text..."

# Install temporary ollama binary from GitHub releases (.tar.zst archive)
# Standalone binary is no longer provided.
OLLAMA_URL="https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst"
log "URL: $OLLAMA_URL"
scurl -L "$OLLAMA_URL" -o /tmp/ollama.tar.zst

# Extract archive to /usr (contains bin/ollama)
# Requires zstd to be installed in the build environment
if ! command -v zstd &>/dev/null; then
    log "ERROR: zstd not found. Installing explicitly..."
    $DNF_BIN "${DNF_SETOPT[@]}" install -y zstd
fi

diag "Extracting Ollama archive..."
# Create a temporary directory for extraction
mkdir -p /tmp/ollama-extract
tar --zstd -xvf /tmp/ollama.tar.zst -C /tmp/ollama-extract

# Find the binary and move it to /usr/bin/ollama
OLLAMA_BIN=$(find /tmp/ollama-extract -type f -name "ollama" | head -n 1)
if [[ -z "$OLLAMA_BIN" ]]; then
    log "ERROR: ollama binary not found in archive."
    diag "Archive contents:"
    tar --zstd -tvf /tmp/ollama.tar.zst
    exit 1
fi

mv "$OLLAMA_BIN" /usr/bin/ollama
chmod +x /usr/bin/ollama
rm -rf /tmp/ollama-extract

# Validation
if ! command -v ollama &>/dev/null; then
    log "ERROR: ollama binary not found in PATH."
    exit 1
fi

if ! file /usr/bin/ollama | grep -q "ELF"; then
    log "ERROR: /usr/bin/ollama is not a valid ELF binary."
    exit 1
fi

# Start ollama serve in background
# We bake models into /usr/share to ensure they are captured by bootc/composefs
# and then link them into /var/lib/ollama at runtime.
BAKE_PATH="/usr/share/ollama/models"
mkdir -p "$BAKE_PATH"
export OLLAMA_MODELS="$BAKE_PATH"

/usr/bin/ollama serve &
OLLAMA_PID=$!

# Wait for server to be ready
log "Waiting for Ollama server to start..."
MAX_RETRIES=15
COUNT=0
while ! scurl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        log "ERROR: Ollama server failed to start."
        kill $OLLAMA_PID
        exit 1
    fi
done

# Pull inference model (8GB-tier default) and embedding model
/usr/bin/ollama pull qwen2.5-coder:7b
/usr/bin/ollama pull nomic-embed-text

# Shutdown server
kill $OLLAMA_PID
wait $OLLAMA_PID || true

# Cleanup
rm -f /tmp/ollama.tar.zst
# Keep the binary in /usr/bin: ollama is listed under packages-ai in
# usr/share/mios/PACKAGES.md and is treated as a permanent image
# component, not a build-time scratch tool.

echo "[37-ollama-prep] Model embedded successfully."
