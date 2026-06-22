<!-- AI-hint: Honest progress + state companion to MIOS-ROADMAP-2026-06-22.md, written after the "/goal continue roadmap" execution session (2026-06-22). Records what is ACTUALLY done + live-verified vs gated vs residual, and flags the pod-deployment landmine (Pod= on 17 containers, only 2 pods deployed). WS-G honesty reconciliation. Trust THIS + the engineering-blueprint over the triumphant MEMORY.md.
     AI-related: ./MIOS-ROADMAP-2026-06-22.md, ./concepts/temporal-recall-weighting-2026-06-22.md, ../../../lib/mios/agent-pipe/server.py, ../../../containers/systemd/, ../../../../automation/38-drift-checks.sh -->
# MiOS Roadmap — progress + honest state (2026-06-22)

Companion to `MIOS-ROADMAP-2026-06-22.md`. Every "DONE" below was **live-verified on
the running `podman-MiOS-DEV` VM**, with the verification evidence noted. "DONE" here
means *active + live-fired*, not "built + gated-OFF" (the WS-G standard).

## ✅ Done + live-verified this session

| Task | What shipped | Live evidence |
|---|---|---|
| **Fabrication fixes** (pre-roadmap interjection) | temporal recall weighting + volatile anti-stale-recall gate + current-events web-promotion + location splice | `@ what folder`→`/mnt/c/MiOS/afs`; Cobourg weather→Environment Canada; "what is new today"→`mios_sources:5` cited |
| **A5** council honesty | `/v1/cluster/health.mode` + chat `mios_mode` (via fixed usage-MW) | `single-agent (no council peers up)` → after A4: `council, council_peers_up=3` |
| **A4** hermes-worker boot | `hermes-worker.path` (PathExists on the venv) + preset | worker `inactive`→`active`; council went 0/9→3/9 (hermes, opencode, mios-daemon-agent) |
| **FED-G1** inbound auth gate | `@app.middleware` gating `/v1/*`+`/a2a`, `[security].api_require_auth` **default OFF** (degrade-open) | unauth `/v1/models`→200 (no regression); flag flips posture |
| **FED-G3** live membership reload | mtime-watch + `POST /a2a/peers/reload` (auth-gated) | watch ON (30s); authed reload OK; unauth→401 |
| **FED-G4** signed AgentCard | `securitySchemes` + Ed25519 JWS `signatures[]` (passport key) | card: `securitySchemes:['bearer']`, `signatures:1` |
| **D1** remote/edge join | template existed (A1); verified auto-join/drop via FED-G3 | `/etc` overlay remote node → `effective_up:true`, peers 3→4; removed → 3 |
| **B2** tiering page-in bump | added the missing `access_count`/`recall_hits`/`last_access`/hot bump to the **live pgvector** recall path (it lived only in the dead SurrealDB path) | after recalls, 5 rows `access_count>0` (was 0) |
| **C0** code-server `:8080→:8800` | repo was correct; deployed + surfaced the pod dependency | `:8800` bound, `:8080` freed |
| **E1** OWUI location firstboot | wired `mios-owui-apply-system-prompt` into `mios-hermes-firstboot` | in the firstboot chain (idempotent) |
| **F1** OWUI RAG embedding | engine `ollama`(→`/api/embed` 404) → `openai`(→`/v1/embeddings`) + embed `--parallel 4` | `:11450/v1/embeddings` 768-dim verified; **residual below** |
| latent bug | `_usage_completeness_mw` passed bytes to `loads_lenient(str)` → silent no-op (usage guarantee broken too) | fixed; usage + mios_mode now land |

## ⚠️ Residuals (honest — NOT fully closed)

- **F1 bulk vectorize**: the engine path is now correct, but re-vectorizing the 32-file
  collection still hits a llama-swap **concurrency-429** under OWUI's burst (distinct
  from the swap-429 already fixed by the resident group). `knowledge_search` returns
  hits only once the collection vectorizes — needs an idle/serialized re-vectorize or a
  llama-swap concurrency bump. Single embeddings + normal-turn RAG work.

## 🚨 POD-DEPLOYMENT LANDMINE (discovered this session — Gemini WS-C must read)

Gemini's pod work added `Pod=<pod>.pod` to **17 `.container` files** in the repo, but
**only `mios-webtools.pod` was deployed to the VM**. A podded `.container` whose
`.pod` is absent makes the **Quadlet generator REJECT the whole unit** → the service
silently vanishes (`Loaded: not-found`) and the container won't (re)start. This bit
**code-server** live this session: deploying its `:8800` quadlet (which now carries
`Pod=mios-devforge.pod`) without the pod took it DOWN until I deployed
`mios-devforge.pod`.

**Consequence:** redeploying ANY of the 17 podded containers (pgvector, llm-light,
adguard, forge, …) to the VM **without first deploying its `.pod`** will break it the
same way — and pgvector/llm-light are the AI plane. **WS-C C2 must deploy all 7
`.pod` files (+ `daemon-reload`) BEFORE or WITH the podded `.container` files**, never
a podded container alone. The 7 pods exist in
`usr/share/containers/systemd/*.pod`; the VM currently has only `mios-webtools.pod`
and (now) `mios-devforge.pod`.

## ⛔ Gated / not done (need operator-VM / egress / keyed peers)

- **A6** kernel Stage-2 hot-path swap — needs operator VM parity loop.
- **A3** opencode `:8633` — RESOLVED via honest exclusion (roadmap's documented
  fallback). Root cause found live: opencode's model `local/mios-opencode:latest`
  resolves fine (llama-swap alias → granite, real completion verified), but
  `opencode run --format json` returns EMPTY even so — an upstream opencode 1.17.9
  headless limitation in the non-TTY gateway (the long-standing "run hangs/returns
  zero"). opencode's own `:8633` is therefore unreachable; it was masquerading as a
  council peer by FAILING OVER to hermes (a shared backend), inflating
  `council_peers_up` to 3. Kept `enabled=false`; made `/v1/cluster/health` count only
  ENABLED, non-default, effective_up peers (+ `council_distinct_up` excludes
  failover-only) → now honest: `council_peers_up:2, council_distinct_up:1`. Future
  real fix: proxy `opencode serve` instead of spawning `run` per request.
- **F2** coderun-sandbox image — needs egress to build. **F3** Code-Mode socket.
- **FED-G5** avahi mDNS; **FED-G6/7/8/9** inbound delegation/scoping — need keyed peers.
- **FED-G2 follow-up** — `_apply_outbound_auth` at the ~4 non-council outbound dispatch
  sites (theoretical until a keyed remote peer exists; the D1 test node was keyless).
- **WS-C C1–C5** pod consolidation — Gemini's; partially in-repo, see landmine above.
- **B1** governance gates — already flipped ON earlier (memguard=log, cost=true).

## Standard going forward
"DONE" = active + live-fired. A built-but-gated-OFF or never-fired feature is
"built/gated", not done. Trust this doc + `concepts/engineering-blueprint*` over the
triumphant `MEMORY.md` framing.
