<!-- AI-hint: Chapter 26: Unified Knowledge Base Ingestion. Explains document indexing and embedding tasks. Maps ingestion pipeline and database tables layout. Covers re-indexing databases and recall optimizations. -->

# Chapter 26: Unified Knowledge Base Ingestion

> Part VI: Storage, Network & Web Planes of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Unified Knowledge Base Ingestion** under MiOS.

### <a name="26_document_parsing_and_embedding"></a>26.Document Parsing and Embedding: Document Parsing and Embedding

> Path Reference: `/usr/share/doc/mios/manual.md#26_document_parsing_and_embedding`

#### Overview

Ingested documents are parsed and vectorized to build the knowledge base.

## Flow
- **Parser**: Converts PDFs, text, and code files.
- **Embedding**: Generates vectors using the light embedding lane.
- **Utility**: Run [generate-unified-knowledge.py](tools/generate-unified-knowledge.py).

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="26_ingest_pipeline_schema"></a>26.Ingest Pipeline Schema: Ingest Pipeline Schema

> Path Reference: `/usr/share/doc/mios/manual.md#26_ingest_pipeline_schema`

#### Overview

The ingest pipeline maps content to Postgres database tables.

## Structure
- **Tables**: Mapped in `usr/share/mios/postgres/schema-init.sql`.
- **Columns**: Stores content, source reference, and vectors.
- **Constraints**: Enforces unique sources to prevent duplicate index entries.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="26_semantic_indexing_maintenance"></a>26.Semantic Indexing Maintenance: Semantic Indexing Maintenance

> Path Reference: `/usr/share/doc/mios/manual.md#26_semantic_indexing_maintenance`

#### Overview

Maintaining vector indexes keeps similarity query times fast.

## Operations
- **Indexing**: Uses HNSW graphs for semantic retrieval.
- **Pruning**: Consolidates duplicate and stale data.
- **Reindexing**: Rebuilds database indexes after import tasks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
