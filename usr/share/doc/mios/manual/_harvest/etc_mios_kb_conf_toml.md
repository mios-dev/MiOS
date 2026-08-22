<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures the MiOS Knowledge Base (KB) by defining LLM endpoints, model identifiers, embedding dimensions, chunking strategies, and vector store connection parameters for the local RAG pipeline.
AI-related: mios-kb, mios-dev, localhost:8642, localhost:11450, localhost:1234, localhost:4000
MiOS KB local config — overrides for downstream consumers
Day-0 defaults target the MiOS Gateway Agent endpoint at http://localhost:8642/v1
(LAW 5: UNIFIED-AI-REDIRECTS). Override per environment.

<!-- mios-src:7145e62eabe5 from etc/mios/kb.conf.toml:1-5 -->

### Examples for other local OpenAI-API-compatible runtimes...

Examples for other local OpenAI-API-compatible runtimes:
  LLM-Light:          base_url = "http://localhost:11450/v1"
  vLLM:               base_url = "http://localhost:8000/v1"
  LM Studio:          base_url = "http://localhost:1234/v1"
  mios-gateway-agent: base_url = "http://localhost:8642/v1"
  LiteLLM proxy:      base_url = "http://localhost:4000/v1"

<!-- mios-src:7036a2325287 from etc/mios/kb.conf.toml:8-13 -->
