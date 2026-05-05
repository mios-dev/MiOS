#!/bin/bash
# 'MiOS' Artifact Logging to MiOS-Bootstrap Repository
# Purpose: Log AI RAG and build artifacts to bootstrap repo for distribution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BOOTSTRAP_REPO="${BOOTSTRAP_REPO:-${HOME}/MiOS-bootstrap}"
MIOS_VERSION=$(cat "${REPO_ROOT}/VERSION" 2>/dev/null || echo "v0.2.0")

echo "'MiOS' Artifact Logging to Bootstrap Repository"
echo "Version: ${MIOS_VERSION}"

# Check if bootstrap repo exists
if [[ ! -d "${BOOTSTRAP_REPO}/.git" ]]; then
    echo "ERROR: mios-bootstrap repository not found at: ${BOOTSTRAP_REPO}"
    echo ""
    echo "Clone it first:"
    echo "  git clone https://github.com/MiOS-DEV/MiOS-bootstrap ${BOOTSTRAP_REPO}"
    echo ""
    echo "Or set BOOTSTRAP_REPO environment variable:"
    echo "  export BOOTSTRAP_REPO=/path/to/MiOS-bootstrap"
    exit 1
fi

echo "[ok] Bootstrap repository: ${BOOTSTRAP_REPO}"
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
    
    echo "[ok] AI RAG artifacts copied"
else
    echo "WARN: No AI RAG artifacts found at artifacts/ai-rag/"
fi

# Copy Wiki documentation
WIKI_DIR="${BOOTSTRAP_REPO}/wiki/${MIOS_VERSION}"
mkdir -p "${WIKI_DIR}"

echo "▶ Logging Wiki documentation..."

if [[ -d "${REPO_ROOT}/specs/ai-integration" ]]; then
    rsync -av \
        "${REPO_ROOT}/specs/ai-integration/" \
        "${WIKI_DIR}/ai-integration/" 2>/dev/null || true
    echo "[ok] Wiki AI integration docs copied"
fi

# Copy core documentation. After the 2026-05-05 FHS-consolidation
# pass, operator-facing docs live under usr/share/doc/mios/ and the
# agent contract lives under usr/share/mios/ai/. Root-level
# SECURITY.md is now a 5-line GitHub Security-tab redirector; the
# canonical full content is at usr/share/doc/mios/guides/security.md
# -- pull from there so the wiki bundle ships the full posture, not
# the stub. Same reasoning for guides/self-build.md.
for doc in \
    usr/share/mios/ai/INDEX.md \
    README.md \
    usr/share/doc/mios/guides/self-build.md \
    usr/share/doc/mios/guides/security.md \
    llms.txt
do
    if [[ -f "${REPO_ROOT}/${doc}" ]]; then
        cp -v "${REPO_ROOT}/${doc}" "${WIKI_DIR}/" 2>/dev/null || true
    fi
done

echo "[ok] Core documentation copied"

# Generate artifact manifest. Compute repo metrics from the actual file
# tree at run time -- the previous version of this script hard-coded
# stats (928 MB, 153 markdown files) that drifted away from reality on
# every commit.
echo "▶ Generating artifact manifest..."

# Repo size: 'du -sh' on the working copy minus the .git directory so we
# count source-of-truth content, not git metadata. Falls back to a literal
# 'unknown' if du isn't available (defensive; du is in coreutils).
if command -v du >/dev/null 2>&1; then
    REPO_SIZE_BYTES=$(du -sb --exclude='.git' "${REPO_ROOT}" 2>/dev/null | awk '{print $1}')
    REPO_SIZE_HUMAN=$(du -sh --exclude='.git' "${REPO_ROOT}" 2>/dev/null | awk '{print $1}')
else
    REPO_SIZE_BYTES=0
    REPO_SIZE_HUMAN="unknown"
fi

# Compressed-context size: pick the newest tar.gz in artifacts/ai-rag if
# present, otherwise leave 0. Avoids hard-coding a specific bundle name.
COMPRESSED_BYTES=0
COMPRESSED_HUMAN="0 B"
NEWEST_BUNDLE=$(ls -t "${REPO_ROOT}"/artifacts/ai-rag/*.tar.gz 2>/dev/null | head -1 || true)
if [[ -n "$NEWEST_BUNDLE" && -f "$NEWEST_BUNDLE" ]]; then
    COMPRESSED_BYTES=$(stat -c%s "$NEWEST_BUNDLE" 2>/dev/null || echo 0)
    COMPRESSED_HUMAN=$(du -h "$NEWEST_BUNDLE" 2>/dev/null | awk '{print $1}')
fi

# File counts: walk the tree once each. -prune the .git dir so we don't
# double-count every fixture on disk.
MARKDOWN_FILES=$(find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type f -name '*.md' -print 2>/dev/null | wc -l | tr -d ' ')
SHELL_SCRIPTS=$(find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type f \( -name '*.sh' -o -name '*.bash' \) -print 2>/dev/null | wc -l | tr -d ' ')

# Compression ratio. Use bc when available for the percentage; otherwise
# fall back to integer-arithmetic two-decimal approximation.
if [[ "$REPO_SIZE_BYTES" -gt 0 && "$COMPRESSED_BYTES" -gt 0 ]] && command -v bc >/dev/null 2>&1; then
    COMPRESSION_RATIO=$(echo "scale=2; (1 - ${COMPRESSED_BYTES}/${REPO_SIZE_BYTES}) * 100" | bc 2>/dev/null)"%"
elif [[ "$REPO_SIZE_BYTES" -gt 0 && "$COMPRESSED_BYTES" -gt 0 ]]; then
    COMPRESSION_RATIO="$(( 100 - (COMPRESSED_BYTES * 100 / REPO_SIZE_BYTES) ))%"
else
    COMPRESSION_RATIO="n/a"
fi

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
      "self_build": "../wiki/${MIOS_VERSION}/self-build.md",
      "security": "../wiki/${MIOS_VERSION}/security.md",
      "llms_txt": "../wiki/${MIOS_VERSION}/llms.txt"
    }
  },
  "stats": {
    "original_repo_size": "${REPO_SIZE_HUMAN}",
    "original_repo_size_bytes": ${REPO_SIZE_BYTES},
    "compressed_context_size": "${COMPRESSED_HUMAN}",
    "compressed_context_size_bytes": ${COMPRESSED_BYTES},
    "compression_ratio": "${COMPRESSION_RATIO}",
    "markdown_files": ${MARKDOWN_FILES},
    "shell_scripts": ${SHELL_SCRIPTS}
  },
  "foss_ai_apis": [
    "Ollama",
    "llama.cpp",
    "LocalAI",
    "vLLM"
  ],
  "license": "Personal Property - 'MiOS' Project",
  "repository": "https://github.com/MiOS-DEV/mios"
}
MANIFEST

echo "[ok] Manifest generated: ${ARTIFACT_DIR}/manifest.json"

# Create README for bootstrap artifacts
cat > "${ARTIFACT_DIR}/README.md" << README
# 'MiOS' ${MIOS_VERSION} - AI RAG Artifacts

**Generated:** $(date -u +%Y-%m-%d)
**Compression:** ${REPO_SIZE_HUMAN} → ${COMPRESSED_HUMAN} (${COMPRESSION_RATIO} reduction)
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
   - Integration guide for Ollama, llama.cpp, LocalAI, vLLM
   - Quick-start commands per runtime
   - RAG configuration notes

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
    {"role": "user", "content": "Explain 'MiOS' architecture"}
  ]
}'
\`\`\`

## Distribution

These artifacts enable:
- FOSS AI agent initialization with full 'MiOS' context
- Offline RAG deployment (no cloud AI required)
- Reproducible AI-assisted development
- Knowledge preservation across versions

---

**Repository:** https://github.com/MiOS-DEV/mios  
**Bootstrap:** https://github.com/MiOS-DEV/MiOS-bootstrap  
**License:** Personal Property - 'MiOS' Project
README

echo "[ok] README generated: ${ARTIFACT_DIR}/README.md"

# Summary
echo ""
echo "[ OK ] Artifact logging complete"
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
echo "     ├─ INDEX.md          (from usr/share/mios/ai/INDEX.md)"
echo "     ├─ README.md         (from README.md)"
echo "     ├─ self-build.md     (from usr/share/doc/mios/guides/self-build.md)"
echo "     ├─ security.md       (from usr/share/doc/mios/guides/security.md)"
echo "     ├─ llms.txt          (from llms.txt)"
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
echo "  git commit -m \"Add 'MiOS' ${MIOS_VERSION} AI RAG artifacts\""
echo "  git push"
