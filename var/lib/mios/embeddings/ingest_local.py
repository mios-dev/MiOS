#!/usr/bin/env python3
"""
ingest_local.py — Embed chunks.jsonl against any OpenAI-compatible
/v1/embeddings endpoint and upsert into Qdrant.

Day-0 compatible. Works against:
  - MiOS LocalAI         (http://localhost:8080/v1)  ← canonical (LAW 5)
  - Ollama               (http://localhost:11434/v1)
  - vLLM                 (http://localhost:8000/v1)
  - LM Studio            (http://localhost:1234/v1)
  - llama.cpp server     (http://localhost:8080/v1)
  - LiteLLM proxy        (http://localhost:4000/v1)
  - OpenAI cloud         (https://api.openai.com/v1)
  - Azure OpenAI         (your resource URL)

Env vars (matches MiOS LAW 5: UNIFIED-AI-REDIRECTS):
  MIOS_AI_ENDPOINT   — default http://localhost:8080/v1
  MIOS_AI_KEY        — default empty (LocalAI accepts empty key)
  MIOS_AI_EMBED_MODEL — default text-embedding-3-large (or your local equivalent)

Qdrant:
  QDRANT_URL         — default http://localhost:6333
  QDRANT_COLLECTION  — default mios-kb

Usage:
  pip install qdrant-client httpx
  podman run -d --name qdrant -p 6333:6333 -p 6334:6334 \\
    -v $PWD/qdrant_data:/qdrant/storage:Z docker.io/qdrant/qdrant:latest
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
    sys.exit("pip install httpx qdrant-client")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError:
    sys.exit("pip install qdrant-client")


def embed_batch(client: httpx.Client, endpoint: str, key: str, model: str,
                texts: list[str]) -> list[list[float]]:
    """Call POST {endpoint}/embeddings with a batch and return vectors."""
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {"model": model, "input": texts}
    # text-embedding-3-* support a `dimensions` parameter; many local
    # runtimes ignore it. Pass it for cloud, omit for local — detected
    # by endpoint host.
    if "api.openai.com" in endpoint or "azure" in endpoint:
        body["dimensions"] = 1536
    r = client.post(f"{endpoint}/embeddings", headers=headers, json=body, timeout=120.0)
    r.raise_for_status()
    return [d["embedding"] for d in r.json()["data"]]


def stable_id(chunk_id: str) -> int:
    """Deterministic 64-bit id from the chunk's string id (Qdrant requires int or UUID)."""
    return int(hashlib.sha1(chunk_id.encode()).hexdigest()[:16], 16)


def main(chunks_path: str = "chunks.jsonl") -> int:
    endpoint = os.environ.get("MIOS_AI_ENDPOINT", "http://localhost:8080/v1").rstrip("/")
    key      = os.environ.get("MIOS_AI_KEY", "")
    model    = os.environ.get("MIOS_AI_EMBED_MODEL", "text-embedding-3-large")
    qdrant_url        = os.environ.get("QDRANT_URL", "http://localhost:6333")
    qdrant_collection = os.environ.get("QDRANT_COLLECTION", "mios-kb")

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

    # 2. Upsert to Qdrant
    qdrant = QdrantClient(url=qdrant_url)
    existing = [c.name for c in qdrant.get_collections().collections]
    if qdrant_collection not in existing:
        qdrant.create_collection(
            collection_name=qdrant_collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        print(f"Created Qdrant collection: {qdrant_collection}")

    points = [
        PointStruct(
            id=stable_id(c["id"]),
            vector=v,
            payload={**c.get("metadata", {}), "chunk_id": c["id"], "text": c["text"]},
        )
        for c, v in zip(chunks, all_vectors)
    ]
    qdrant.upsert(collection_name=qdrant_collection, points=points, wait=True)
    print(f"Upserted {len(points)} points into {qdrant_collection}")

    # 3. Sanity probe
    sample_query = "What is the kargs.d format in MiOS?"
    qv = embed_batch(httpx.Client(), endpoint, key, model, [sample_query])[0]
    hits = qdrant.search(collection_name=qdrant_collection, query_vector=qv, limit=3)
    print(f"\nSanity probe — top 3 hits for '{sample_query}':")
    for h in hits:
        cid = h.payload.get("chunk_id", "?")
        snippet = h.payload.get("text", "")[:120].replace("\n", " ")
        print(f"  {h.score:.3f}  {cid}  {snippet}…")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "chunks.jsonl"))
