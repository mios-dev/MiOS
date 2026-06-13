#!/bin/bash
# AI-hint: Provisioning script to extract GGUF weights from Ollama blobs, deploy the llama-swap configuration, and start the mios-llama-swap container on port 11450 for the engine-swap live test.
# AI-related: /usr/share/mios/llamacpp/models, /usr/share/mios/llamacpp, /usr/share/mios/llamacpp/llama-swap.yaml, mios-llama-swap, mios-llama-swap.container, mios-llama-swap.service
# automation/support/bringup-llama-swap.sh
# ----------------------------------------------------------------------------
# Bring up the mios-llama-swap lane on a DEV VM (WS-10 engine-swap live test).
# Extracts the qwen3.5:4b + nomic-embed-text GGUFs from ollama's own blob store
# (the custom qwen35 model has no HF source -> reuse the exact local weights),
# deploys the config + a RENDERED quadlet (Quadlet does not expand ${VAR:-def},
# so we substitute the defaults), starts the container, verifies it serves
# :11450. Idempotent: skips a GGUF copy if already present.
#
# Usage: bash bringup-llama-swap.sh
set -euo pipefail

SRC=/mnt/c/MiOS
OLLAMA_BLOBS=/var/lib/ollama/models/blobs
MODELS=/usr/share/mios/llamacpp/models
SLOTS=/var/lib/mios/llamacpp/slots
PORT=11450
# Exact model-layer digests read from the ollama manifests (2026-06-04).
QWEN_BLOB=sha256-81fb60c7daa80fc1123380b98970b320ae233409f0f71a72ed7b9b0d62f40490
NOMIC_BLOB=sha256-970aa74c0a90ef7482477cf803618e776e173c007bf957f635f1015bfcfef0e6

echo "[lls] dirs"
sudo install -d -m 0755 "$MODELS" /usr/share/mios/llamacpp
sudo install -d -m 0777 "$SLOTS"   # uid 827 writes KV slots here (test perms)

echo "[lls] extract GGUFs from ollama blobs (no download; exact local weights)"
if [ ! -f "$MODELS/qwen3.5-4b.gguf" ]; then
    [ -f "$OLLAMA_BLOBS/$QWEN_BLOB" ] || { echo "[lls] MISSING qwen blob $QWEN_BLOB -- ABORT"; exit 1; }
    sudo cp "$OLLAMA_BLOBS/$QWEN_BLOB" "$MODELS/qwen3.5-4b.gguf"
fi
if [ ! -f "$MODELS/nomic-embed-text.gguf" ]; then
    [ -f "$OLLAMA_BLOBS/$NOMIC_BLOB" ] || { echo "[lls] MISSING nomic blob -- ABORT"; exit 1; }
    sudo cp "$OLLAMA_BLOBS/$NOMIC_BLOB" "$MODELS/nomic-embed-text.gguf"
fi
sudo chmod 0644 "$MODELS"/*.gguf
ls -lh "$MODELS"

echo "[lls] deploy config (CR-stripped)"
tr -d '\r' < "$SRC/usr/share/mios/llamacpp/llama-swap.yaml" | sudo tee /usr/share/mios/llamacpp/llama-swap.yaml >/dev/null

echo "[lls] render + deploy quadlet (substitute \${VAR:-default} -> default)"
tr -d '\r' < "$SRC/usr/share/containers/systemd/mios-llama-swap.container" \
    | sed -E 's/\$\{[A-Z_]+:-([^}]*)\}/\1/g' \
    | sudo tee /etc/containers/systemd/mios-llama-swap.container >/dev/null

echo "[lls] ready marker + daemon-reload + start"
sudo touch "$MODELS/.ready"
sudo systemctl daemon-reload
sudo systemctl start mios-llama-swap.service 2>&1 || true
sleep 8
echo "[lls] state=$(systemctl is-active mios-llama-swap.service 2>/dev/null)"
sudo systemctl --no-pager -l status mios-llama-swap.service 2>/dev/null | tail -18
echo "[lls] === recent container log ==="
sudo journalctl -u mios-llama-swap.service --no-pager 2>/dev/null | tail -25
echo "[lls] === probe :$PORT/v1/models ==="
curl -s -m 8 "http://localhost:$PORT/v1/models" 2>/dev/null | head -c 600
echo
