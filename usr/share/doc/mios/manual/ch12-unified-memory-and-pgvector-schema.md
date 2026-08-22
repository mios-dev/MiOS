<!-- AI-hint: Chapter 12: Unified Memory and pgvector Schema. Details pgvector database container setup, connection pools, and permissions. Explains cosine-similarity searches utilizing vector retrieval. Covers background archival workers and semantic consolidation. -->

# Chapter 12: Unified Memory and pgvector Schema

> Part IV: Detailed Inference & Execution Layers of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Unified Memory and pgvector Schema** under MiOS.

### <a name="12_postgresql_integration"></a>12.PostgreSQL Integration: PostgreSQL Integration

> Path Reference: `/usr/share/doc/mios/manual.md#12_postgresql_integration`

#### Overview

MiOS integrates PostgreSQL inside rootless Podman to serve as the unified agent datastore.

## Settings
- **Service**: `mios-pgvector.service` running on port 5432.
- **User Mapping**: Maps host UID 826 to container database root.
- **Connection**: Supports secure loopback socket connections for local services.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="12_semantic_knowledge_recall"></a>12.Semantic Knowledge Recall: Semantic Knowledge Recall

> Path Reference: `/usr/share/doc/mios/manual.md#12_semantic_knowledge_recall`

#### Overview

Memory and knowledge tables are queried using semantic vector searches.

## Query Pipeline
- **Embedding**: Prompt vectors are generated using the `nomic-embed-text` lane.
- **SQL Query**: Searches the `knowledge` table using pgvector's HNSW index operators:
  ```sql
  SELECT content FROM knowledge ORDER BY embedding <=> $1 LIMIT 5;
  ```
- **Injection**: Retrieved content is injected into agent context to guide response generation.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="12_epistemic_memory_pruning"></a>12.Epistemic Memory Pruning: Epistemic Memory Pruning

> Path Reference: `/usr/share/doc/mios/manual.md#12_epistemic_memory_pruning`

#### Overview

To maintain search performance, memory indexes are optimized via background pruning.

## Methods
- **Consolidation**: Consolidates multiple redundant logs into single semantic entries.
- **Archiving**: Moves historical logs to offline JSON archives.
- **Index Cleanup**: Runs `VACUUM ANALYZE` on memory tables to rebuild HNSW graphs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
