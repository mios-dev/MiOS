# Memory Tiering Guide (WS-CONV-11)

This guide documents the three-tier converged memory architecture deployed to optimize WAL write amplification, database size, and edge I/O footprint.

## The Three-Tier Memory Model

MiOS uses a hierarchical memory system to balance fast session context, long-term semantic retrieval, and low-cost historical archiving.

### Tier 0: In-Process sqlite-vec Scratchpad (Session Memory)
- **Engine**: In-process SQLite utilizing the `sqlite-vec` vector extension.
- **Storage**: Node-local tmpfs at `/run/user/<uid>/` or `/tmp`.
- **Lifespan**: Created at the start of a gateway worker conversation session, populated with intermediate tool-call results, and destroyed at the end of the session.
- **Purpose**: Prevents high-write-amplification WAL database hits on intermediate thinking loops.

### Tier 1: pgvector (Durable Memory)
- **Engine**: PostgreSQL with `pgvector` extension.
- **Storage**: Persistent block storage.
- **Lifespan**: Durable long-term memory.
- **Purpose**: Serves as the primary semantic retrieval store for end-of-session synthesis, preference mapping, and historical context injection.

### Tier 2: zstd Cold Archive (Historical Archiving)
- **Engine**: Compressed JSONL archives.
- **Storage**: Node-local directory (defaulting to `/var/lib/mios/history/`).
- **Lifespan**: Expired knowledge table rows are exported, compressed, and deleted from pgvector during periodic eviction sweeps.
- **Purpose**: Extremely high-density historical audit trail storage with near-zero active VRAM/memory footprint.

---

## Configuration

Memory tiering options are managed in `mios.toml` under `[converge.memory]`:

```toml
[converge.memory]
sqlite_vec_enable = true
scratchpad_dir = "/run/user/827"
cold_evict_enable = true
cold_storage_dir = "/var/lib/mios/history"
cold_retention_days = 90
cold_zstd_level = 3
```

---

## Querying Tier 2 Cold Archives

Since cold archives are compressed using standard `zstd` compression and format each database row as a JSON line, they can be searched, filtered, and queried using command-line tools like `zstd` and `jq`:

### 1. View all rows in an archive
```bash
zstd -d -c /var/lib/mios/history/YYYY/MM-DD/some-uuid.jsonl.zst
```

### 2. Search for a specific question/answer
```bash
zstd -d -c /var/lib/mios/history/**/*.jsonl.zst | jq 'select(.q | contains("preference"))'
```

### 3. Count total archived rows
```bash
zstd -d -c /var/lib/mios/history/**/*.jsonl.zst | wc -l
```
