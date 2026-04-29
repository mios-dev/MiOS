#!/bin/bash
# MiOS Omni-Agent Bootstrap Script
# Synchronizes manifests and initializes sub-project environments.

set -euo pipefail

echo "🚀 Initializing MiOS Agent Workspace..."

# 0. Load Unified Environment
if [[ -f ".env.mios" ]]; then
    echo "📜 Loading unified environment from .env.mios..."
    # Export all variables defined in .env.mios
    set -a
    source .env.mios
    set +a
fi

# 1. Generate Manifests
if [[ -f "tools/generate-ai-manifest.py" ]]; then
    echo "📄 Generating directory manifests..."
    python3 tools/generate-ai-manifest.py
else
    echo "⚠️ Warning: tools/generate-ai-manifest.py not found."
fi

# 2. Sync Wiki Documentation
if [[ -f "tools/sync-wiki.py" ]]; then
    echo "📖 Syncing Wiki..."
    python3 tools/sync-wiki.py
else
    echo "⚠️ Warning: tools/sync-wiki.py not found."
fi

# 3. Generate Unified Knowledge Base (RAG Snapshot)
if [[ -f "tools/generate-unified-knowledge.py" ]]; then
    echo "🧠 Generating Unified Knowledge Base (RAG Snapshot)..."
    if [[ -f "tools/journal-sync.py" ]]; then
        python3 tools/journal-sync.py
    fi
    python3 tools/generate-unified-knowledge.py
else
    echo "⚠️ Warning: tools/generate-unified-knowledge.py not found."
fi

# 4. Initialize agents/research
if [[ -d "agents/research" ]]; then
    echo "🧪 Initializing agents/research (Agent Starter Pack)..."
    (cd agents/research && make install)
else
    echo "⚠️ Warning: agents/research directory not found."
fi

# 3. Persistence: Refresh environment configs and dotfiles
echo "💾 Persisting environment state..."
if [[ -f "tools/refresh-env.py" ]]; then
    python3 tools/refresh-env.py
else
    echo "⚠️ Warning: tools/refresh-env.py not found."
fi

echo "✅ Workspace initialization complete."

# 6. Seed Artifacts for Agents
echo "🌱 Seeding latest MiOS Artifacts for initialized agents..."
if [[ -f "artifacts/repo-rag-snapshot.json.gz" ]]; then
    # Shared scratchpad for cross-agent IPC
    mkdir -p .ai/foundation/shared-tmp/
    cp artifacts/repo-rag-snapshot.json.gz .ai/foundation/shared-tmp/latest-context.json.gz
    # Sub-project local context
    cp artifacts/repo-rag-snapshot.json.gz agents/research/latest-context.json.gz
    echo "✅ Context seeded to .ai/foundation/shared-tmp/ and agents/research/"
else
    echo "⚠️ Warning: artifacts/repo-rag-snapshot.json.gz not found. Skip seeding."
fi
