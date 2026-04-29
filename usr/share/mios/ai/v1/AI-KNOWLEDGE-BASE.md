# 🌐 MiOS AI Integration & Knowledge Base

## Overview
MiOS provides a standardized, OpenAI-compatible AI interface for local inference and Retrieval-Augmented Generation (RAG). All AI interactions within MiOS MUST adhere to the OpenAI API specification.

## Standardized API Interface
MiOS hosts an OpenAI-compatible local inference proxy at `http://localhost:8080/v1`. This endpoint provides a unified interface for chat completions, embeddings, and model discovery.

### Endpoints
| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/chat/completions` | POST | Primary chat interface |
| `/v1/embeddings` | POST | Vector embeddings for RAG |
| `/v1/models` | GET | Model discovery |
| `/v1/mcp` | FS/HTTP | Model Context Protocol registry |

## RAG Architecture
MiOS uses a Retrieval-Augmented Generation (RAG) system to ground AI agents in the local system context.

### Knowledge Ingestion
Knowledge is ingested from the project's standardized documentation (e.g., `INDEX.md`, `PACKAGES.md`) and compressed artifacts.

### Configuration
Standardized RAG configuration is defined in `usr/share/mios/ai/v1/ai-context.json`.

## AI Agent Initialization
Agents are initialized with a standard system prompt that enforces MiOS immutable laws and architectural constraints.

### System Prompt
```markdown
You are an expert in MiOS, an immutable, bootc-based Linux distribution.
All operations must adhere to OpenAI API standards.
Immutable Laws:
1. USR-OVER-ETC: Static config in /usr/lib/, not /etc/.
2. NO-MKDIR-IN-VAR: Use tmpfiles.d for /var directories.
3. BOOTC-CONTAINER-LINT: Mandatory final validation.
```

## Quick Start (OpenAI Standard)

### 1. Model Discovery
```bash
curl http://localhost:8080/v1/models
```

### 2. Chat Completions
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mi-os-7b",
    "messages": [{"role": "user", "content": "Explain MiOS laws"}]
  }'
```

### 3. Generate Embeddings
```bash
curl http://localhost:8080/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mi-os-7b",
    "input": "USR-OVER-ETC"
  }'
```

