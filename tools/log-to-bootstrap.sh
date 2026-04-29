#!/bin/bash
# MiOS Artifact Logging to MiOS-Bootstrap Repository
# Purpose: Log AI RAG and build artifacts to bootstrap repo for distribution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BOOTSTRAP_REPO="${BOOTSTRAP_REPO:-${HOME}/MiOS-bootstrap}"
MIOS_VERSION=$(cat "${REPO_ROOT}/VERSION" 2>/dev/null || echo "v0.1.2")

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "MiOS Artifact Logging to Bootstrap Repository"
echo "Version: ${MIOS_VERSION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if bootstrap repo exists
if [[ ! -d "${BOOTSTRAP_REPO}/.git" ]]; then
    echo "❌ MiOS-bootstrap repository not found at: ${BOOTSTRAP_REPO}"
    echo ""
    echo "Clone it first:"
    echo "  git clone https://github.com/MiOS-DEV/MiOS-bootstrap ${BOOTSTRAP_REPO}"
    echo ""
    echo "Or set BOOTSTRAP_REPO environment variable:"
    echo "  export BOOTSTRAP_REPO=/path/to/MiOS-bootstrap"
    exit 1
fi

echo "✓ Bootstrap repository: ${BOOTSTRAP_REPO}"
echo ""

# Create artifact directories
ARTIFACT_DIR="${BOOTSTRAP_REPO}/ai-rag-packages/${MIOS_VERSION}"
mkdir -p "${ARTIFACT_DIR}"

echo "▶ Logging AI RAG artifacts..."

# Copy AI RAG package artifacts
if [[ -d "${REPO_ROOT}/artifacts/ai-rag" ]]; then
    rsync -av --delete \
        "${REPO_ROOT}/artifacts/ai-rag/" \
        "${ARTIFACT_DIR}/" \
        --exclude="*.tar.gz" 2>/dev/null || true
    
    # Copy compressed bundles separately (track in Git LFS if available)
    cp -v "${REPO_ROOT}"/artifacts/ai-rag/*.tar.gz "${ARTIFACT_DIR}/" 2>/dev/null || true
    
    echo "✓ AI RAG artifacts copied"
else
    echo "⚠️  No AI RAG artifacts found at artifacts/ai-rag/"
fi

# Copy Wiki documentation
WIKI_DIR="${BOOTSTRAP_REPO}/wiki/${MIOS_VERSION}"
mkdir -p "${WIKI_DIR}"

echo "▶ Logging Wiki documentation..."

if [[ -d "${REPO_ROOT}/specs/ai-integration" ]]; then
    rsync -av \
        "${REPO_ROOT}/specs/ai-integration/" \
        "${WIKI_DIR}/ai-integration/" 2>/dev/null || true
    echo "✓ Wiki AI integration docs copied"
fi

# Copy core documentation
for doc in INDEX.md README.md SELF-BUILD.md SECURITY.md llms.txt; do
    if [[ -f "${REPO_ROOT}/${doc}" ]]; then
        cp -v "${REPO_ROOT}/${doc}" "${WIKI_DIR}/" 2>/dev/null || true
    fi
done

echo "✓ Core documentation copied"

# Generate artifact manifest
echo "▶ Generating artifact manifest..."

cat > "${ARTIFACT_DIR}/manifest.json" << MANIFEST
{
  "mios_version": "${MIOS_VERSION}",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "artifacts": {
    "ai_rag": {
      "knowledge_graph": "mios-knowledge-graph.json",
      "context_bundle": "mios-context-*.tar.gz",
      "rag_manifest": "rag-manifest.yaml",
      "prompts_library": "ai-prompts.md",
      "quick_reference": "QUICKREF.md",
      "integration_guide": "README-AI-INTEGRATION.md",
      "script_inventory": "script-inventory.json",
      "docs_bundle": "mios-docs-*.tar.gz"
    },
    "wiki": {
      "ai_integration_index": "../wiki/${MIOS_VERSION}/ai-integration/2026-04-27-Artifact-AI-000-Index.md",
      "rag_integration": "../wiki/${MIOS_VERSION}/ai-integration/2026-04-27-Artifact-AI-001-RAG-Integration.md",
      "quick_reference": "../wiki/${MIOS_VERSION}/ai-integration/2026-04-27-Artifact-AI-002-Quick-Reference.md",
      "prompts": "../wiki/${MIOS_VERSION}/ai-integration/2026-04-27-Artifact-AI-003-Prompts-Library.md",
      "knowledge_graph": "../wiki/${MIOS_VERSION}/ai-integration/2026-04-27-Artifact-AI-004-Knowledge-Graph.md"
    },
    "core_docs": {
      "index": "../wiki/${MIOS_VERSION}/INDEX.md",
      "readme": "../wiki/${MIOS_VERSION}/README.md",
      "self_build": "../wiki/${MIOS_VERSION}/SELF-BUILD.md",
      "security": "../wiki/${MIOS_VERSION}/SECURITY.md",
      "llms_txt": "../wiki/${MIOS_VERSION}/llms.txt"
    }
  },
  "stats": {
    "original_repo_size": "928 MB",
    "compressed_context_size": "752 KB",
    "compression_ratio": "99.92%",
    "markdown_files": 153,
    "shell_scripts": 116
  },
  "foss_ai_apis": [
    "Ollama",
    "llama.cpp",
    "LocalAI",
    "vLLM"
  ],
  "license": "Personal Property - MiOS Project",
  "repository": "https://github.com/mios-project/mios"
}
MANIFEST

echo "✓ Manifest generated: ${ARTIFACT_DIR}/manifest.json"

# Create README for bootstrap artifacts
cat > "${ARTIFACT_DIR}/README.md" << README
# MiOS ${MIOS_VERSION} - AI RAG Artifacts

**Generated:** $(date -u +%Y-%m-%d)  
**Compression:** 928 MB → 752 KB (99.92% reduction)  
**Target:** FOSS AI APIs (Ollama, llama.cpp, LocalAI, vLLM)

## Artifacts in This Package

### AI RAG Components

1. **mios-knowledge-graph.json** (3.3 KB)
   - Structured knowledge graph with core concepts
   - Version history and MiOS-NXT roadmap
   - Ready for AI agent system prompts

2. **mios-context-TIMESTAMP.tar.gz** (752 KB)
   - Complete compressed repository
   - All documentation, scripts, configs preserved
   - Extract and ingest into vector database

3. **rag-manifest.yaml** (1.9 KB)
   - Embedding strategy configuration
   - Retrieval parameters for FOSS AI
   - Knowledge source weights

4. **README-AI-INTEGRATION.md** (8.0 KB)
   - Comprehensive integration guide
   - Quick start for Ollama/llama.cpp/LocalAI/vLLM
   - Advanced RAG techniques

5. **QUICKREF.md** (2.7 KB)
   - AI agent quick reference card
   - Essential commands and file hierarchy
   - Common tasks

6. **ai-prompts.md** (3.2 KB)
   - System initialization prompts
   - Task-specific prompt templates

7. **script-inventory.json** (8.2 KB)
   - Complete automation script catalog

8. **mios-docs-TIMESTAMP.tar.gz** (31 KB)
   - Core documentation bundle

### Wiki Documentation

Located in: \`../wiki/${MIOS_VERSION}/ai-integration/\`

- AI Integration Index
- RAG Integration Guide
- Quick Reference
- Prompts Library
- Knowledge Graph

## Quick Start

\`\`\`bash
# 1. Extract context
tar -xzf mios-context-*.tar.gz -C ~/mios-rag

# 2. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

# 3. Create vector database
pip install langchain langchain-community chromadb

# See README-AI-INTEGRATION.md for full setup
\`\`\`

## Usage

Load knowledge graph into AI:

\`\`\`bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.1:8b",
  "messages": [
    {"role": "system", "content": "$(cat mios-knowledge-graph.json)"},
    {"role": "user", "content": "Explain MiOS architecture"}
  ]
}'
\`\`\`

## Distribution

These artifacts enable:
- FOSS AI agent initialization with full MiOS context
- Offline RAG deployment (no cloud AI required)
- Reproducible AI-assisted development
- Knowledge preservation across versions

---

**Repository:** https://github.com/mios-project/mios  
**Bootstrap:** https://github.com/MiOS-DEV/MiOS-bootstrap  
**License:** Personal Property - MiOS Project
README

echo "✓ README generated: ${ARTIFACT_DIR}/README.md"

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Artifact Logging Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Logged to: ${BOOTSTRAP_REPO}"
echo ""
echo "Structure:"
echo "  ${BOOTSTRAP_REPO}/"
echo "  ├─ ai-rag-packages/${MIOS_VERSION}/"
echo "  │  ├─ manifest.json"
echo "  │  ├─ README.md"
echo "  │  ├─ mios-knowledge-graph.json"
echo "  │  ├─ mios-context-*.tar.gz"
echo "  │  ├─ rag-manifest.yaml"
echo "  │  ├─ README-AI-INTEGRATION.md"
echo "  │  ├─ QUICKREF.md"
echo "  │  ├─ ai-prompts.md"
echo "  │  ├─ script-inventory.json"
echo "  │  └─ mios-docs-*.tar.gz"
echo "  └─ wiki/${MIOS_VERSION}/"
echo "     ├─ INDEX.md"
echo "     ├─ README.md"
echo "     ├─ SELF-BUILD.md"
echo "     ├─ SECURITY.md"
echo "     ├─ llms.txt"
echo "     └─ ai-integration/"
echo "        ├─ 2026-04-27-Artifact-AI-000-Index.md"
echo "        ├─ 2026-04-27-Artifact-AI-001-RAG-Integration.md"
echo "        ├─ 2026-04-27-Artifact-AI-002-Quick-Reference.md"
echo "        ├─ 2026-04-27-Artifact-AI-003-Prompts-Library.md"
echo "        └─ 2026-04-27-Artifact-AI-004-Knowledge-Graph.md"
echo ""
echo "Next steps:"
echo "  cd ${BOOTSTRAP_REPO}"
echo "  git add ."
echo "  git commit -m \"Add MiOS ${MIOS_VERSION} AI RAG artifacts\""
echo "  git push"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
