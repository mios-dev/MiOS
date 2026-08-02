#!/bin/bash
# AI-hint: Syncs AI RAG artifacts and wiki documentation from the local build environment to the MiOS-bootstrap repository to prepare the system for distribution and RAG-enabled agent deployment.
# AI-related: mios-bootstrap, mios-knowledge-graph, mios-context, mios-docs, mios-context-TIMESTAMP, mios-docs-TIMESTAMP, mios-rag, mios-llm-light, localhost:8642 (MIOS_AI_ENDPOINT, OpenAI /v1)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BOOTSTRAP_REPO="${BOOTSTRAP_REPO:-${HOME}/MiOS-bootstrap}"
MIOS_VERSION=$(cat "${REPO_ROOT}/VERSION" 2>/dev/null || echo "0.3.0")

echo "'MiOS' Artifact Logging to Bootstrap Repository"
echo "Version: ${MIOS_VERSION}"

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

ARTIFACT_DIR="${BOOTSTRAP_REPO}/ai-rag-packages/${MIOS_VERSION}"
mkdir -p "${ARTIFACT_DIR}"

echo "▶ Logging AI RAG artifacts"

if [[ -d "${REPO_ROOT}/artifacts/ai-rag" ]]; then
    rsync -av --delete \
        "${REPO_ROOT}/artifacts/ai-rag/" \
        "${ARTIFACT_DIR}/" \
        --exclude="*.tar.gz" 2>/dev/null || true
    
    cp -v "${REPO_ROOT}"/artifacts/ai-rag/*.tar.gz "${ARTIFACT_DIR}/" 2>/dev/null || true
    
    echo "[ok] AI RAG artifacts copied"
else
    echo "WARN: No AI RAG artifacts found at artifacts/ai-rag/"
fi

WIKI_DIR="${BOOTSTRAP_REPO}/wiki/${MIOS_VERSION}"
mkdir -p "${WIKI_DIR}"

echo "▶ Logging Wiki documentation"

if [[ -d "${REPO_ROOT}/specs/ai-integration" ]]; then
    rsync -av \
        "${REPO_ROOT}/specs/ai-integration/" \
        "${WIKI_DIR}/ai-integration/" 2>/dev/null || true
    echo "[ok] Wiki AI integration docs copied"
fi

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

echo "▶ Generating artifact manifest"

if command -v du >/dev/null 2>&1; then
    REPO_SIZE_BYTES=$(du -sb --exclude='.git' "${REPO_ROOT}" 2>/dev/null | awk '{print $1}')
    REPO_SIZE_HUMAN=$(du -sh --exclude='.git' "${REPO_ROOT}" 2>/dev/null | awk '{print $1}')
else
    REPO_SIZE_BYTES=0
    REPO_SIZE_HUMAN="unknown"
fi

COMPRESSED_BYTES=0
COMPRESSED_HUMAN="0 B"
NEWEST_BUNDLE=$(ls -t "${REPO_ROOT}"/artifacts/ai-rag/*.tar.gz 2>/dev/null | head -1 || true)
if [[ -n "$NEWEST_BUNDLE" && -f "$NEWEST_BUNDLE" ]]; then
    COMPRESSED_BYTES=$(stat -c%s "$NEWEST_BUNDLE" 2>/dev/null || echo 0)
    COMPRESSED_HUMAN=$(du -h "$NEWEST_BUNDLE" 2>/dev/null | awk '{print $1}')
fi

MARKDOWN_FILES=$(find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type f -name '*.md' -print 2>/dev/null | wc -l | tr -d ' ')
SHELL_SCRIPTS=$(find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o -type f \( -name '*.sh' -o -name '*.bash' \) -print 2>/dev/null | wc -l | tr -d ' ')

if [[ "$REPO_SIZE_BYTES" -gt 0 && "$COMPRESSED_BYTES" -gt 0 ]] && command -v bc >/dev/null 2>&1; then
    COMPRESSION_RATIO=$(echo "Scale=2; * 100" | bc 2>/dev/null)"%"
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
    "MiOS /v1 (OpenAI-compatible)",
    "llama.cpp (mios-llm-light)",
    "vLLM / SGLang (mios-llm-heavy)"
  ],
  "license": "Personal Property - 'MiOS' Project",
  "repository": "https://github.com/MiOS-DEV/mios"
}
MANIFEST

echo "[ok] Manifest generated: ${ARTIFACT_DIR}/manifest.json"

cat > "${ARTIFACT_DIR}/README.md" << README

**Generated:** $(date -u +%Y-%m-%d)
**Compression:** ${REPO_SIZE_HUMAN} → ${COMPRESSED_HUMAN} (${COMPRESSION_RATIO} reduction)
**Target:** OpenAI /v1-compatible runtimes -- the MiOS lanes mios-llm-light + mios-llm-heavy (llama.cpp / vLLM / SGLang)



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
   - Integration guide for the MiOS /v1 inference lanes (mios-llm-light + mios-llm-heavy; llama.cpp / vLLM / SGLang, all OpenAI /v1-compatible)
   - Quick-start commands per lane
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


Located in: \`../wiki/${MIOS_VERSION}/ai-integration/\`

- AI Integration Index
- RAG Integration Guide
- Quick Reference
- Prompts Library
- Knowledge Graph


\`\`\`bash
tar -xzf mios-context-*.tar.gz -C ~/mios-rag

export OPENAI_BASE_URL="http://localhost:8642/v1"
export OPENAI_API_KEY="\${MIOS_AI_KEY:-mios-local}"

pip install langchain langchain-community pgvector psycopg

\`\`\`


Load knowledge graph into AI:

\`\`\`bash
curl --retry 5 --retry-delay 3 --connect-timeout 20 "\${OPENAI_BASE_URL:-http://localhost:8642/v1}/chat/completions" -H "Authorization: Bearer \${OPENAI_API_KEY:-mios-local}" -H "Content-Type: application/json" -d '{
  "model": "mios-llm-light",
  "messages": [
    {"role": "system", "content": "You are grounded in the MiOS knowledge graph."},
    {"role": "user", "content": "Explain the MiOS architecture"}
  ]
}'

\`\`\`


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
echo "     ├─ INDEX.md"
echo "     ├─ README.md"
echo "     ├─ self-build.md"
echo "     ├─ security.md"
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
echo "  git add "
echo "  git commit -m \"Add 'MiOS' ${MIOS_VERSION} AI RAG artifacts\""
echo "  git push"
