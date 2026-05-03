#!/bin/bash
# 'MiOS' AI/manifest bootstrap. Regenerates directory manifests, syncs the Wiki,
# rebuilds the unified knowledge base (RAG snapshot), refreshes user-space
# environment configs, and seeds shared agent context. Idempotent.

set -uo pipefail

echo "[ai-bootstrap] Initializing 'MiOS' agent workspace..."

# 0. Load unified environment (legacy .env.mios; deprecated — prefer
# /etc/mios/profile.toml for new installs).
if [[ -f ".env.mios" ]]; then
    echo "[ai-bootstrap] Loading legacy environment from .env.mios..."
    set -a
    # shellcheck disable=SC1091
    source .env.mios
    set +a
fi

# 1. Generate manifests.
if [[ -f "tools/generate-ai-manifest.py" ]]; then
    echo "[ai-bootstrap] Generating directory manifests..."
    python3 tools/generate-ai-manifest.py || echo "[ai-bootstrap] WARN: manifest generation failed (non-fatal)"
else
    echo "[ai-bootstrap] WARN: tools/generate-ai-manifest.py not found"
fi

# 2. Sync Wiki documentation.
if [[ -f "tools/sync-wiki.py" ]]; then
    echo "[ai-bootstrap] Syncing Wiki..."
    python3 tools/sync-wiki.py || echo "[ai-bootstrap] WARN: wiki sync failed (non-fatal)"
else
    echo "[ai-bootstrap] WARN: tools/sync-wiki.py not found"
fi

# 3. Generate unified knowledge base (RAG snapshot).
if [[ -f "tools/generate-unified-knowledge.py" ]]; then
    echo "[ai-bootstrap] Generating unified knowledge base (RAG snapshot)..."
    [[ -f "tools/journal-sync.py" ]] && { python3 tools/journal-sync.py || true; }
    python3 tools/generate-unified-knowledge.py || echo "[ai-bootstrap] WARN: knowledge base generation failed (non-fatal)"
else
    echo "[ai-bootstrap] WARN: tools/generate-unified-knowledge.py not found"
fi

# 4. Initialize agents/research scratchpad if present.
if [[ -d "agents/research" ]]; then
    echo "[ai-bootstrap] Initializing agents/research scratchpad..."
else
    echo "[ai-bootstrap] WARN: agents/research directory not found"
fi

# 5. Refresh environment configs and dotfiles.
echo "[ai-bootstrap] Persisting environment state..."
if [[ -f "tools/refresh-env.py" ]]; then
    python3 tools/refresh-env.py
else
    echo "[ai-bootstrap] WARN: tools/refresh-env.py not found"
fi

echo "[ai-bootstrap] Workspace initialization complete."

# 6. Seed RAG context for downstream agents.
echo "[ai-bootstrap] Seeding latest 'MiOS' context for initialized agents..."
if [[ -f "artifacts/repo-rag-snapshot.json.gz" ]]; then
    mkdir -p .ai/foundation/shared-tmp/
    cp artifacts/repo-rag-snapshot.json.gz .ai/foundation/shared-tmp/latest-context.json.gz
    cp artifacts/repo-rag-snapshot.json.gz agents/research/latest-context.json.gz
    echo "[ai-bootstrap] Context seeded to .ai/foundation/shared-tmp/ and agents/research/"
else
    echo "[ai-bootstrap] WARN: artifacts/repo-rag-snapshot.json.gz not found; skipping seed"
fi
