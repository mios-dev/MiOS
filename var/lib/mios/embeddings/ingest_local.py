#!/usr/bin/env python3
# AI-hint: Processes chunks.jsonl by generating embeddings via OpenAI-compatible local endpoints (LocalAI, Ollama, vLLM) and upserting the resulting vectors into the pgvector PostgreSQL database for RAG retrieval.
# AI-related: mios-kb, localhost:8080, localhost:11450, localhost:8000, localhost:1234, localhost:4000, localhost:5432
# AI-functions: embed_batch, stable_id, vector_literal, main
"""
ingest_local.py — Embed chunks.jsonl against any OpenAI-API-compatible
/v1/embeddings endpoint (LAW 5) and upsert into pgvector.

Day-0 compatible. Works against:
  - MiOS LocalAI         (http://localhost:8080/v1)  ← canonical (LAW 5)
  - Ollama               (http://localhost:11434/v1)
  - vLLM                 (http://localhost:8000/v1)
  - LM Studio            (http://localhost:1234/v1)
  - llama.cpp server     (http://localhost:8080/v1)
  - LiteLLM proxy        (http://localhost:4000/v1)

Env vars (matches MiOS LAW 5: UNIFIED-AI-REDIRECTS):
  MIOS_AI_ENDPOINT    — default http://localhost:8080/v1
  MIOS_AI_KEY         — default empty (LocalAI accepts empty key)
  MIOS_AI_EMBED_MODEL — default nomic-embed-text (canonical mios.toml [ai].embed_model)

pgvector:
  MIOS_PG_HOST         — default localhost
  MIOS_PORT_PGVECTOR   — default 5432
  MIOS_PG_USER         — default mios
  MIOS_PG_PASS         — default mios
  MIOS_PG_DB           — default mios
  MIOS_SYS_ENV_TABLE   — default mios_kb (collection name with hyphens -> underscores)

Usage:
  pip install psycopg httpx
  python3 ingest_local.py [path/to/chunks.jsonl]

Default path: ./chunks.jsonl (sibling of this script when shipped under
/var/lib/mios/embeddings/).
"""
from __future__ import annotations
import json, os, sys, hashlib, time
from pathlib import Path

try:
    import httpx
except ImportError:
    sys.exit("pip install httpx psycopg")

try:
    import psycopg
except ImportError:
    sys.exit("pip install psycopg")


def embed_batch(client: httpx.Client, endpoint: str, key: str, model: str,
                texts: list[str]) -> list[list[float]]:
    """Call POST {endpoint}/embeddings with a batch and return vectors."""
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {"model": model, "input": texts}
    # Optional `dimensions` parameter — set MIOS_AI_EMBED_DIMS to enable.
    # Many local runtimes silently ignore it; nomic-embed-text default is 768-dim.
    dims = os.environ.get("MIOS_AI_EMBED_DIMS")
    if dims:
        body["dimensions"] = int(dims)
    r = client.post(f"{endpoint}/embeddings", headers=headers, json=body, timeout=120.0)
    r.raise_for_status()
    return [d["embedding"] for d in r.json()["data"]]


def stable_id(chunk_id: str) -> int:
    """Deterministic 64-bit id from the chunk's string id."""
    return int(hashlib.sha1(chunk_id.encode()).hexdigest()[:16], 16)


def vector_literal(vec) -> str:
    """Format a float sequence as a pgvector text literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(float(x)) for x in (vec or [])) + "]"


def main(chunks_path: str = "chunks.jsonl") -> int:
    endpoint = os.environ.get("MIOS_AI_ENDPOINT", "http://localhost:8080/v1").rstrip("/")
    key      = os.environ.get("MIOS_AI_KEY", "")
    model    = os.environ.get("MIOS_AI_EMBED_MODEL", "nomic-embed-text")
    
    # pgvector config
    pg_host = os.environ.get("MIOS_PG_HOST", "localhost")
    pg_port = int(os.environ.get("MIOS_PORT_PGVECTOR", "5432") or 5432)
    pg_user = os.environ.get("MIOS_PG_USER", "mios")
    pg_pass = os.environ.get("MIOS_PG_PASS", "mios")
    pg_db   = os.environ.get("MIOS_PG_DB", "mios")
    
    collection = os.environ.get("MIOS_KB_COLLECTION", "mios-kb")
    table_name = collection.replace("-", "_")

    path = Path(chunks_path)
    if not path.exists():
        path = Path(__file__).resolve().parent / "chunks.jsonl"
    if not path.exists():
        sys.exit(f"chunks.jsonl not found at {chunks_path} or alongside this script")

    chunks = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(chunks)} chunks from {path}")
    print(f"Embedding via {endpoint} (model={model})")

    # 1. Embed in batches of 32
    all_vectors: list[list[float]] = []
    with httpx.Client() as client:
        BATCH = 32
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i:i + BATCH]
            texts = [c["text"] for c in batch]
            t0 = time.time()
            vectors = embed_batch(client, endpoint, key, model, texts)
            print(f"  batch {i // BATCH + 1}/{(len(chunks) + BATCH - 1) // BATCH} "
                  f"({len(vectors)} vectors, dim={len(vectors[0])}) in {time.time() - t0:.1f}s")
            all_vectors.extend(vectors)

    dim = len(all_vectors[0])
    print(f"All vectors embedded (dim={dim})")

    # 2. Upsert to pgvector
    dsn = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    print(f"Connecting to pgvector at {pg_host}:{pg_port} (db={pg_db}, table={table_name})...")
    
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Enable vector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create schema
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id bigint PRIMARY KEY,
                    chunk_id text,
                    content text,
                    metadata jsonb,
                    emb vector({dim})
                );
            """)
            
            # Create HNSW index
            try:
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS {table_name}_emb_hnsw 
                    ON {table_name} USING hnsw (emb vector_cosine_ops);
                """)
            except Exception:
                pass  # Optional index
                
            print(f"Table {table_name} created/verified.")
            
            # Truncate and upsert
            cur.execute(f"TRUNCATE TABLE {table_name};")
            
            # Batch inserts
            print("Upserting vectors...")
            for c, v in zip(chunks, all_vectors):
                cid = c["id"]
                content = c["text"]
                metadata = c.get("metadata", {})
                vec_str = vector_literal(v)
                
                cur.execute(f"""
                    INSERT INTO {table_name} (id, chunk_id, content, metadata, emb)
                    VALUES (%s, %s, %s, %s, %s::vector);
                """, (stable_id(cid), cid, content, json.dumps(metadata), vec_str))
                
            print(f"Upserted {len(chunks)} points into pgvector table {table_name}")

            # 3. Sanity probe
            sample_query = "What is the kargs.d format in MiOS?"
            qv = embed_batch(httpx.Client(), endpoint, key, model, [sample_query])[0]
            qv_str = vector_literal(qv)
            
            cur.execute(f"""
                SELECT chunk_id, content, 1 - (emb <=> %s::vector) AS score
                FROM {table_name}
                ORDER BY emb <=> %s::vector
                LIMIT 3;
            """, (qv_str, qv_str))
            
            hits = cur.fetchall()
            print(f"\nSanity probe — top 3 hits for '{sample_query}':")
            for h in hits:
                cid = h[0]
                snippet = h[1][:120].replace("\n", " ")
                score = float(h[2])
                print(f"  {score:.3f}  {cid}  {snippet}…")
                
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "chunks.jsonl"))
