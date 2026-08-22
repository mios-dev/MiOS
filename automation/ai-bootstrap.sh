#!/bin/bash
# AI-hint: Bootstraps the MiOS agent workspace by regenerating directory manifests, syncing Wiki docs, building the RAG knowledge base, and refreshing environment configs to prepare the system for agent interaction.
# AI-related: /etc/mios/profile.toml

set -euo pipefail

echo "[ai-bootstrap] Initializing 'MiOS' agent workspace"

if [[ -f ".env.mios" ]]; then
    echo "[ai-bootstrap] Loading legacy environment from .env.mios"
    set -a
    source .env.mios
    set +a
fi

if [[ -f "tools/generate-ai-manifest.py" ]]; then
    echo "[ai-bootstrap] Generating directory manifests"
    python3 tools/generate-ai-manifest.py || echo "[ai-bootstrap] WARN: manifest generation failed"
else
    echo "[ai-bootstrap] WARN: tools/generate-ai-manifest.py not found"
fi

if [[ -f "tools/sync-wiki.py" ]]; then
    echo "[ai-bootstrap] Syncing Wiki"
    python3 tools/sync-wiki.py || echo "[ai-bootstrap] WARN: wiki sync failed"
else
    echo "[ai-bootstrap] WARN: tools/sync-wiki.py not found"
fi

if [[ -f "usr/libexec/mios/mios-manual" ]]; then
    echo "[ai-bootstrap] Generating manual audit index"
    [[ -f "tools/journal-sync.py" ]] && { python3 tools/journal-sync.py || true; }
    python3 usr/libexec/mios/mios-manual audit --json > usr/share/mios/reference/audit-index.json || echo "[ai-bootstrap] WARN: manual audit index generation failed"
fi

if [[ -d "agents/research" ]]; then
    echo "[ai-bootstrap] Initializing agents/research scratchpad"
else
    echo "[ai-bootstrap] WARN: agents/research directory not found"
fi

echo "[ai-bootstrap] Refreshing environment configs and dotfiles via tools/refresh-env.py"
if [[ -f "tools/refresh-env.py" ]]; then
    python3 tools/refresh-env.py
else
    echo "[ai-bootstrap] WARN: tools/refresh-env.py not found"
fi

echo "[ai-bootstrap] Workspace initialization complete"

echo "[ai-bootstrap] Copying artifacts/repo-rag-snapshot.json.gz into .ai/foundation/shared-tmp/ and agents/research/"
if [[ -f "artifacts/repo-rag-snapshot.json.gz" ]]; then
    mkdir -p .ai/foundation/shared-tmp/
    cp artifacts/repo-rag-snapshot.json.gz .ai/foundation/shared-tmp/latest-context.json.gz
    cp artifacts/repo-rag-snapshot.json.gz agents/research/latest-context.json.gz
    echo "[ai-bootstrap] Context seeded to .ai/foundation/shared-tmp/ and agents/research/"
else
    echo "[ai-bootstrap] WARN: artifacts/repo-rag-snapshot.json.gz not found; skipping seed"
fi
