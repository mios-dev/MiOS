<!-- AI-hint: Upstream reference for pgvector, the PostgreSQL vector extension behind the mios-pgvector unified agent datastore — what it is, why MiOS exact-pins it (the one AI image that is not float-latest), how the pin flows through the SSOT projections, the extension-upgrade procedure, and the PG-major migration constraint that keeps the tag on -pg17.
     AI-related: mios-pgvector, usr/share/mios/mios.toml, usr/share/containers/systemd/mios-pgvector.container, usr/share/mios/postgres/schema-init.sql, usr/libexec/mios/mios-resolve-latest, automation/support/bringup-pgvector.sh -->

# pgvector — PostgreSQL vector search (the agent datastore)

> Used by MiOS for: the unified agent datastore. `mios-pgvector` is
> PostgreSQL + the `vector` extension holding agent memory, events, tool
> calls, sessions, skills and the `knowledge` table with HNSW vector recall —
> the persistent brain every lane and agent reads through.
> Source: `usr/share/mios/mios.toml` §[pgvector] + §[containers.mios-pgvector],
> `usr/share/mios/postgres/schema-init.sql`,
> `usr/share/doc/mios/concepts/architecture.md` §AI plane.

## Why this matters to MiOS

MiOS is one thing built two ways at once: an immutable, bootc/OCI-shaped Fedora
workstation that is *also* a local, self-hosted, agentic AI operating system.
Everything the agent half *remembers* lives in this one container. Losing an
inference lane costs a reply; corrupting the datastore costs the operator's
accumulated memory — which is why this image gets stricter version treatment
than any other AI sidecar.

## Projects

- pgvector — <https://github.com/pgvector/pgvector> (PostgreSQL License).
  Vector types + HNSW/IVFFlat indexes for PostgreSQL. Publishes git *tags*
  (`v0.8.6` style), not GitHub Releases.
- Official images — <https://hub.docker.com/r/pgvector/pgvector>. Tag scheme
  `<pgvector-version>-pg<PG-major>` (e.g. `0.8.6-pg17`, `0.8.6-pg18`) plus
  floating `pgNN` family tags.

## Versioning — floats on the `pgNN` family tag

| Surface | Value | Why |
|---|---|---|
| `mios.toml [image.sidecars].pgvector` | `docker.io/pgvector/pgvector:pg17` | **Floats** (ADR-0012): always the newest pgvector built for that PG major, resolved to a digest at build and recorded in the SBOM. No hand-pinned version to rot. Newest always satisfies `hnsw.iterative_scan` (pgvector ≥ 0.8.0), which the Quadlet `Exec=` sets unconditionally. |
| The `-pg17` suffix | a **compatibility constraint**, not a version pin | `/var/lib/mios/pgvector` holds a PG**17** cluster and a `pg18` image refuses to start on it without `pg_upgrade`/dump-restore. The PG major therefore advances only through that migration (WS-UPSTREAM T-292), never as a side effect of floating. |
| Projections | Quadlet `Image=`, `automation/lib/globals.{sh,ps1}` (`MIOS_PGVECTOR_IMAGE`), `[build.bake].core`, `usr/lib/mios/bake/plan.d/04-extra.list`, env-baseline | Never hand-edit the projections: change `[image.sidecars]` and run `tools/sync-generated.sh` (Law 8). |

There is no version-bump procedure, and that is the point: the float re-resolves
on every build. To pick up a new pgvector release, rebuild. What *does* need a
deliberate procedure is the PG major, below.

On the first start of a newer image, update the extension inside the database
(extension name is `vector`, not "pgvector"; the version column is
`pg_extension.extversion`):

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
ALTER EXTENSION vector UPDATE;
-- integrity audit: any invalid index would show here (none expected on 0.8.x minors)
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid OR NOT indisready;
```

pgvector 0.8.x minor updates require no reindex. A PG-major move (pg17→pg18)
additionally needs a dump/restore or `pg_upgrade` window and is tracked as its
own WS-UPSTREAM task — do not change the `-pgNN` suffix as part of a routine
version bump.

## CVE posture

CVE-2026-3172 (CVSS 8.1 — buffer overflow in *parallel* HNSW build, affects
0.6.0–0.8.1, fixed 0.8.2) never reached a shipped MiOS image: the ref was
already at 0.8.3 when the CVE published, and the `pg17` float now resolves to
0.8.6 or newer on every build. CVE response for this image is therefore
"rebuild so the float re-resolves", not a pin. Interim mitigation for
any future index-build CVE of the same shape:
`SET max_parallel_maintenance_workers = 0;` disables the parallel build path
without touching data. Verification record:
`usr/share/doc/mios/reference/upstream-gaps-2026-08.md` §CVE matrix.

## MiOS integration points

| Piece | Where |
|---|---|
| Quadlet | `usr/share/containers/systemd/mios-pgvector.container` — `User=826`, `Delegate=yes`, joins `mios-ai.pod` (host net), `Exec=postgres -c port=${MIOS_PORT_PGVECTOR:-8600} -c listen_addresses=127.0.0.1 -c hnsw.iterative_scan=strict_order ...` |
| Schema | `usr/share/mios/postgres/schema-init.sql` (knowledge/memory/events/tools/sessions + HNSW indexes) |
| SSOT knobs | `mios.toml [pgvector]` — db/user `mios`, `data_dir=/var/lib/mios/pgvector`, `emb_version`, HNSW scan tuning, backups |
| Bring-up check | `automation/support/bringup-pgvector.sh` (renders the Quadlet, verifies the `vector` extension) |
| Boot health | `usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh` probes pgvector; failure triggers bootc rollback |

## Cross-refs

- `usr/share/doc/mios/reference/upstream-gaps-2026-08.md` — the 2026-08 verification pass that produced the current pin.
- `usr/share/doc/mios/reference/upstream-gaps-2026-07.md` §pgvector-rag — feature gaps (hybrid recall, reranking, halfvec).
- `usr/share/doc/mios/upstream/inference-engines.md` — the lanes whose embeddings this store indexes.
- `usr/share/doc/mios/adr/0002-mios-sys-shared-base-consolidation.md` — the pin-preservation rationale referenced by the SSOT comment.
- `usr/share/doc/mios/adr/0012-float-latest-no-hand-pinned-versions.md` — why this pin is the deliberate exception to float-latest.
- `ROADMAP.md` §WS-UPSTREAM — Renovate coverage + PG-major migration tasks.
