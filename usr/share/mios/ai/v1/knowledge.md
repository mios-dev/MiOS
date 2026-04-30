# MiOS AI Integration — Knowledge Specification

## 1. Interface Standards
MiOS implements a standardized, OpenAI-compatible AI surface for system management and local inference. All AI operations MUST adhere to the OpenAI API specification.

## 2. API Surface (OpenAI Native)
System interactions occur via a local OpenAI-compatible proxy at `http://localhost:8080/v1`.

### Endpoints
| Path | Method | Function |
|---|---|---|
| `/v1/chat/completions` | POST | Primary system interaction |
| `/v1/embeddings` | POST | Semantic vector generation |
| `/v1/models` | GET | Hardware and model discovery |
| `/v1/mcp` | FS/HTTP | Model Context Protocol hub |

## 3. Architecture
System context is provided via Retrieval-Augmented Generation (RAG) grounded in the immutable system layer.

### Knowledge Sources
- **System SSOT**: `INDEX.md`
- **Deployment**: `ARCHITECTURE.md`
- **Security**: `ENGINEERING.md`

### Runtime Configuration
Contextual variables and operational boundaries are defined in `/usr/share/mios/ai/v1/context.json`.

## 4. Operational Directives (Agents)
Agents are initialized with the specification in `/usr/share/mios/ai/v1/system.md`.

### Core Invariants
1. **USR-OVER-ETC**: All static logic resides in the immutable `/usr` partition.
2. **STATELÉSS-VAR**: Persistence is declared via `tmpfiles.d`.
3. **BOOTC-LIFECYCLE**: Updates occur via atomic OCI image switches.

## 5. Technical Interaction (Examples)

### Model Discovery
```bash
curl http://localhost:8080/v1/models
```

### System Instruction
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mi-os-7b",
    "messages": [{"role": "user", "content": "Query USR-OVER-ETC status"}]
  }'
```
