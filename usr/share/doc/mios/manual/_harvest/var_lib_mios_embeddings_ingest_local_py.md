<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Processes chunks.jsonl by...

!/usr/bin/env python3
AI-hint: Processes chunks.jsonl by generating embeddings via OpenAI-compatible local endpoints (llama.cpp, Ollama, vLLM) and upserting the resulting vectors into the pgvector PostgreSQL database for RAG retrieval.
AI-related: mios-kb, localhost:8080, mios-llm-light (port key `llm_light`), localhost:8000, localhost:1234, localhost:4000, localhost:5432
AI-functions: embed_batch, stable_id, vector_literal, main

<!-- mios-src:33a2d0d66191 from var/lib/mios/embeddings/ingest_local.py:1-4 -->

