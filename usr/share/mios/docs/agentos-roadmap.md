<!-- AI-hint: Roadmap for evolving the MiOS agent stack toward the 2025-2026 AgentOS/AIOS reference architecture, identifying specific technical gaps (DAG decomposition, deliberative loops, event buses) and the phased engineering plan that resolves them; several phases have landed. Read to understand how the agent plane fits the whole MiOS system.
     AI-related: mios-agent-pipe, hermes-agent, mios-launcher, mios-pc-control, mios-windows, mios-daemon, mios-llm-light, mios-llm-heavy, mios-pgvector, mios-skills, mios-skills-miner, mios-passport, mios-text-edit, mios-powershell -->
# MiOS AgentOS Roadmap

## Purpose & place in the whole system

MiOS is one thing built two ways at once: an **immutable bootc/OCI Fedora
workstation** (the whole OS is a single container image — boot it, `bootc
upgrade` it like a `git pull`, roll it back like a Ctrl-Z) that is *also* a
**local, self-replicating, agentic AI operating system**. The build pipeline
assembles the image, the bootc lifecycle carries it forward, and the same image
that ships GNOME/Wayland, GPU-via-CDI, KVM/libvirt and a k3s+Ceph cluster path
*also* ships a full local agent stack behind one OpenAI-compatible endpoint.

This document is the architectural roadmap for the **agentic** half of that
system — how the MiOS agent stack evolves toward the 2025-2026 AIOS / AgentOS
reference architecture. It is written for engineers extending the agent plane.
Its job is to connect that plane to the rest of MiOS: a front-end request flows
into the **agent-pipe** orchestrator (`:8640`), which refines/decomposes it,
fans it out across a council/swarm, and dispatches typed tool/verb calls;
**MiOS-Hermes** (`:8642`) is the OpenAI-compatible gateway and tool-loop agent;
the **inference lanes** (`mios-llm-light` `:11450`, the heavy GPU lanes
`mios-llm-heavy`/`mios-llm-heavy-alt`) do generation and embeddings; and
**PostgreSQL + pgvector** (`mios-pgvector` `:5432`) is the unified agent memory.
MCP exposes the tool surface; A2A federates peer agents. Phases below are
ordered by operator-impact-per-line-of-code, not by formal completeness.

> **Migration note (2026-06-13):** The agent plane has moved off the early
> Ollama / SurrealDB / Qdrant stack. Inference + embeddings now run on
> `mios-llm-light` (`:11450`, llama.cpp behind the upstream `mios-llm-light` proxy);
> the unified datastore is PostgreSQL + pgvector. Ollama survives only as an
> *upstream API-compat reference* (the lanes speak the OpenAI/Ollama-compatible
> API). Several phases below are **landed** — those sections describe shipped
> code and are kept as the design-of-record; the still-open phases describe
> planned work.

## Current state

| AgentOS principle | MiOS implementation | Gap |
|---|---|---|
| Tripartite layer (App/SDK/Kernel) | OWUI -> mios-agent-pipe (:8640) -> hermes-agent (:8642) | No formal SDK boundary; mios-agent-pipe IS the SDK in practice |
| MCP-style tool execution | mios-launcher broker (CAPTURE_JSON), typed verbs, LiteCUA via mios-pc-control + mios-windows | Strongest piece in MiOS |
| Multi-frontend through one chain | OWUI shipped; Discord shipped; Slack/Telegram pending | Works (OWUI + Discord) |
| Shared cross-cutting state | PostgreSQL + pgvector: agent_memory / session / tool_call / event / skill / scratch / knowledge / kanban / agent_metric | Works |
| Local memory (per-agent) | hermes/.hermes/*.db, mios-daemon state, OWUI webui.db | Works |
| Primary inference + embeddings | mios-llm-light at :11450 (llama.cpp via mios-llm-light); serves everyday models + `nomic-embed-text` embeddings + the `mios-opencode` coder model | Live |
| Heavy GPU lanes | mios-llm-heavy (SGLang, :11441, served-name `mios-heavy`) / mios-llm-heavy-alt (vLLM) | Gated/off-by-default (VRAM) |
| Query decomposition into DAG | `decompose` router action runs nodes topologically | **landed (Phase A.1)** |
| Deliberative Collective Intelligence | single-pass critic loop, informal | **GAP B** |
| Document-mutation event bus | hermes-tail/*.json + nudges (polled) | **GAP C** (no inotify pub/sub) |
| Personal Knowledge Graph | `person` table in pgvector; flat OWUI memory | **GAP D** (no rich graph edges) |
| Sequential Pattern Mining | mios-skills miner over tool_call history | **landed (Phase C.2)** |
| Taint-aware memory + Semantic Firewall | `tainted` tagging + pre-dispatch firewall on WRITE-class verbs | **landed (Phase A.3 / B.3)** |
| Agent Passports / crypto identity | Ed25519 passports via mios-passport; signed envelopes on writes | **landed (Phase C.3)** |

Operator-observed failures the open/closed gaps addressed:
- "open notepad and type hello and save to documents" -- monolithic
  handling; Hermes tried random paths because no DAG split into
  open_app -> focus -> type -> save chain (Phase A.1)
- "Hermes claimed it launched but didn't" -- single-pass critic
  didn't FALSIFY the success claim (GAP B, still open)
- daemon polling 3 sideband JSONs at 5-min ticks vs reacting
  on-mutation (GAP C, still open)

## Phase A -- foundational gaps (commit 1-3)

### A.1 -- DAG query decomposition via orchestrator-subagent  *(landed)*

**Reference**: Anthropic's multi-agent research system pattern --
NOT DeepSieve verbatim (DeepSieve needs DeepSeek-V3-scale planner;
the local-stack decomposer is a small function-calling-tuned model).
~300 LoC in `mios-agent-pipe`, no new heavy deps.

**Shape**:
- New router action: `decompose`. Returns:
  ```
  {"action": "decompose",
   "nodes": [
     {"id": "n1", "tool": "open_app", "args": {"name": "notepad"}, "deps": []},
     {"id": "n2", "tool": "focus_window", "args": {"title": "Notepad"}, "deps": ["n1"]},
     {"id": "n3", "tool": "pc_type", "args": {"text": "hello"}, "deps": ["n2"]},
     {"id": "n4", "tool": "pc_key", "args": {"keys": "ctrl+s"}, "deps": ["n3"]}
   ]}
  ```
- agent-pipe runs nodes topologically; failures retry up to 2x
  (reflexion cap) before pruning + asking operator.
- Each node emits a pgvector `tool_call` row tagged with the DAG id
  + parent edges -- gives a full audit trail for multi-step intents.

**Decomposer model**: resolved through the lane router (`MIOS_AI_ENDPOINT`,
Law 5) to a function-calling-capable model served by `mios-llm-light`, not the
smallest micro-LLM (too small for reliable multi-hop per community reports).

### A.2 -- inotify-backed document-mutation event bus

Replace the 3 separate poll loops in mios-daemon (hermes-tail,
delegation-prefilter, log-watcher) with one inotify watcher on
`/var/lib/mios/*/` directories. Hooks emit pgvector `event` rows.
Agents (mios-daemon, agent-pipe critic, future Kanban dispatcher)
`SELECT FROM event WHERE source = X AND ts > <last_seen>`.

### A.3 -- Taint-aware memory tags  *(landed)*

When agent-pipe's broker dispatch returns a tool_call result whose
source is untrusted (e.g. web fetch, RAG document, external API
response), tag the result content with `tainted = true` before it
enters the chain's context. A pre-execution check in the
Semantic Firewall (Phase B.3) refuses high-privilege follow-up
verbs (service_restart, container_restart, open_url to non-allow-
listed domain) if any tainted content is in context.

## Phase B -- deliberation upgrade (commit 4-6)

### B.1 -- DCI 14-act vocabulary as structured output

Define the typed-acts schema (14 acts: frame/clarify/reframe,
propose/extend/spawn, ask/challenge, bridge/synthesize/recall,
ground/update, recommend). Each agent reply in deliberation MUST
emit JSON with an `act` field. Lets us tag the pgvector `event` row
with the act type + run analytics on which act fired before resolution.

### B.2 -- DCI-CF convergent flow critic (replaces single-pass)

4 personas on hermes-agent (Framer / Explorer /
Challenger / Integrator). Bounded loop: R_max=3 rounds, K_max=4
candidate finalists. Always emits a decision packet {choice,
rationale, minority_report, reopen_triggers}. Tensions preserved
as first-class objects in pgvector `event(kind="dissent")`.

Single-model role-playing works per the DCI paper (one capable model,
4 differentiated system prompts). Diversity helps but isn't required —
the personas can all be served by `mios-llm-light` via distinct prompts.

### B.3 -- Semantic Firewall pre-MCP-dispatch  *(landed)*

Small Python layer in agent-pipe. Before any WRITE-class verb
fires, check:
- Operator's original DAG (from A.1) authorized this verb
- No tainted content (from A.3) in agent context
- Action target is consistent with the DAG node's `args`
On violation: abort + emit pgvector `event(kind="firewall_block",
severity="high")` + surface to operator.

## Phase C -- long-horizon autonomy (commit 7+)

### C.1 -- Personal Knowledge Graph

The pgvector schema already seeds a `person` table for per-operator
grounding. The next step is rich graph edges: `pref`, `device`,
`app_install` rows + relationship columns/joins so the router/refine
pass can ground ambiguous terms ("my browser" -> preference ->
chromedev). PostgreSQL joins + JSONB carry the edges; semantic recall
rides the existing `vector(768)` HNSW columns.

### C.2 -- Sequential Pattern Mining over tool_call history  *(landed)*

Implemented as:

* `usr/share/mios/postgres/schema-init.sql` -- tables:
  `skill` (catalog row, param-templated body), `skill_invocation`
  (per-run audit), `event`/`tool_call` (the mined source), and the
  composition edges expressed as JSONB/relations. The miner
  subtracts already-codified runs so it doesn't re-mine its own
  skills.
* `usr/libexec/mios/mios-skills` -- stdlib-only CLI:
  `mine / list / show / run / promote / retire / delete /
  import / export / openai-tools / export-catalog`. The miner
  enumerates contiguous N-grams of (verb, args-shape) over
  session-bucketed tool_calls, counts support + unique-session
  witness, auto-promotes when confidence crosses the SSOT-driven
  `auto_promote_threshold`.
* `usr/lib/mios/agent-pipe/server.py` -- endpoints:
  `GET /skills/list`, `GET /skills/show`, `POST /skills/run`,
  `GET /skills/openai-tools`. `execute_skill()` routes every step
  through `dispatch_mios_verb()` so the Phase B.3 firewall +
  Phase A.3 taint chain + audit-row writes apply identically to
  direct verb dispatch.
* `usr/lib/systemd/system/mios-skills-miner.{service,timer}` --
  cadence-driven background miner; ExecStartPost also runs
  `mios-skills export-catalog` so offline agents see fresh
  catalog.json without polling agent-pipe HTTP.
* Cross-agent surfaces (every external agent reads from at least
  one of these):
    1. `GET /skills/openai-tools` on :8640 (live HTTP).
    2. `/var/lib/mios/skills/catalog.json` (static file the miner
       atomically refreshes; offline-safe).
    3. Direct read of the `skill` table in pgvector (any agent that
       can reach `:5432` via `mios-pg-query`).
* SSOT: `[skills]` in mios.toml -- `enable`, `min_length`,
  `max_length`, `min_support`, `window_hours`,
  `auto_promote_threshold`, `mine_interval_minutes`,
  `seed_catalog_dir`, `local_catalog_dir`. All routed through
  userenv.sh + the configurator HTML "Skills" section.

### C.3 -- Agent Passports (signed identity tokens)  *(landed)*

Implemented as:

* `usr/share/mios/postgres/schema-init.sql` -- an `agent_keypair`
  registry table + a `passport` JSONB field on
  tool_call / skill_invocation / event / agent_metric. Optional +
  flexible so legacy rows stay readable and v2-envelope additions
  (delegation chain headers) don't break the schema.
* `usr/libexec/mios/mios-passport` -- stdlib + python3-
  cryptography CLI: `provision / list / show / public-key /
  sign / verify / rotate / hash`. Idempotent provision generates
  Ed25519 keypairs at `/var/lib/mios/agent-passports/<agent>/`
  (private.key 0600 sysuser-owned, public.key 0644 world-
  readable). Registers public PEM in `agent_keypair` so a
  verifier without filesystem access still works.
* `usr/lib/mios/agent-pipe/server.py` -- `_passport_sign(table,
  fields)` + `_passport_verify(envelope, payload?)` helpers
  using the same canonical-JSON op_hash algorithm as the CLI.
  `_db_create` now defaults to `passport_sign=True`; every write
  through it carries an Ed25519 envelope. `_skill_invocation_
  open` builds its INSERT manually and explicitly attaches the
  passport.
  * `GET /passport/public-key?agent=` -- ship a public PEM to
    external integrators without filesystem access.
  * `POST /passport/verify` -- `{envelope, table?, fields?}` ->
    `{ok, reason, agent, kid, alg}`. Cross-agent verification
    over HTTP for clients that prefer the network surface.
* `usr/lib/systemd/system/mios-passport-provision.service` --
  one-shot firstboot keypair generator. Ordered Before=
  mios-agent-pipe / hermes-agent / mios-daemon so every signing
  service has its private key before it tries to write.
* SSOT: `[passport]` in mios.toml -- `enable`, `algo`,
  `key_dir`, `rotate_days`, `verify_on_read`, `agents` (CSV).
  All routed via userenv.sh + the configurator HTML "Passport"
  section.
* Signed bytes: `agent\nts\nnonce\nop_hash` -- deterministic +
  re-derivable from any language. `op_hash` is
  `sha256(table:canonical-json(fields-minus-passport))`,
  binding the signature to the exact data.

## Phase D -- post-Phase-C additive surface (commit 10+)

### D.1 -- Native text-editor + powershell_run verbs  *(landed)*

Closes the two FS-navigation gaps the 2026-05-18 research note
flagged.

* `usr/libexec/mios/mios-text-edit` -- stdlib Python CLI.
  Subcommands: `view / create / str_replace / insert`. Mirrors
  Anthropic's text_editor_* schema shape (view returns
  1-indexed line numbers; str_replace requires the old block
  to occur exactly once). Replaces the fragile
  `pc_type` + `pc_key ctrl+s` save chain.
* `usr/libexec/mios/mios-powershell` -- bash shim wrapping
  `pwsh.exe` / `powershell.exe` with `-NoProfile
  -NonInteractive -ExecutionPolicy Bypass`. Optional
  `--json` envelope, `--timeout N`, `--work-dir PATH`.
  Stages the script through /mnt/c/Users/Public/Documents/
  for native Windows file access (faster than the \\wsl
  UNC path).
* Five new dispatch verbs in agent-pipe `_build_dispatch_cmd`:
  `text_view`, `text_create`, `text_str_replace`,
  `text_insert`, `powershell_run`. Bodies pass through stdin
  + base64 so multiline / special-char content survives the
  broker socket round-trip.
* Router prompt advertises all five with verb-pick priority
  rules ("read X" -> text_view, "save X to Y" -> text_create,
  "run powershell: X" -> powershell_run).

### D.1a -- Hardening + Everything-Search resilience

Folded into D.1 per operator directive 2026-05-18 (harden the
Linux + Windows FS navigation + use Everything Search for
Windows paths).

* `mios-text-edit` path validation: `_validate_write_path()`
  refuses writes to /etc, /usr, /boot, /sys, /proc, /dev,
  /run, /lib, /lib64, /sbin, /bin, /mnt/c/Windows,
  /mnt/c/Program Files. `realpath` resolves symlinks first --
  no symlink escape. Operator override via
  `MIOS_TEXT_EDIT_WRITE_DENIED_PREFIXES` (CSV).
* Size caps: read 1 MiB, write 1 MiB, PowerShell script
  64 KiB, PowerShell output 256 KiB. All env-overridable.
* `text_view` resilience: on `not_found`, runs
  `mios-everything` for the basename and includes up to 5
  candidate paths in the error envelope so the planner can
  retry with the resolved path instead of giving up.
* `powershell_run` output truncation with explicit marker
  lines (`... [truncated N bytes; output cap M bytes]`) so
  the agent sees the elision instead of mis-counting.
* `_classify_verb_taint`: powershell_run output is always
  tainted (Windows-side execution = external state);
  text_view of any write-denied prefix is also tainted.
* `_HIGH_PRIVILEGE_VERBS` + `[security].
  firewall_high_privilege_verbs` extended to include the four
  WRITE-class verbs (text_create, text_str_replace,
  text_insert, powershell_run). Tainted sessions REFUSE
  dispatch.

`usr/share/mios/skills/write-text-file.json` -- seed
template demonstrating text_create -> text_view as the native
replacement for save-document's pc_type chain.

### D.2 -- ttyd browser pty bridge  *(landed)*

Operator directive 2026-05-18: "add ttyd to the stack so we can
access PowerShell from a local browser(s)". Two systemd-managed
ttyd instances expose pty-over-WebSocket bridges:

  * `mios-ttyd-bash.service`         :7681  ->  `ttyd ... /bin/bash`
  * `mios-ttyd-powershell.service`   :7682  ->  `ttyd ... mios-powershell --shell`

`mios-powershell --shell` (mode in the existing shim) execs
`pwsh.exe` (preferred) / `powershell.exe` interactively via WSL
interop, inheriting the ttyd pty. The browser tab sees a real
Windows PowerShell prompt over WebSocket.

Hardening:
  * Both bound to 127.0.0.1 by default.
  * `mios-ttyd-launch` refuses to bind beyond loopback without
    `auth_user` + `auth_pass` when `require_auth` is true.
  * Optional TLS termination via `ssl_cert` + `ssl_key`.

SSOT: `[ttyd]` in mios.toml + `[ports].ttyd_bash` (`:7681`) /
`.ttyd_powershell` (`:7682`) + the userenv.sh slot map +
configurator HTML "ttyd" section.

Package: `ttyd` in `packages-ttyd` of
`usr/share/doc/mios/reference/PACKAGES.md` (Fedora ships v1.7.7).

## What stays put

The MCP-style execution layer (mios-launcher broker, mios-pc-
control, mios-windows, typed verbs) is already strong; the
research validates it. No changes planned. The multi-lane inference
topology — `mios-llm-light` as the primary llama.cpp lane with
multi-model auto-swap + KV-cache paging, the gated heavy GPU lanes
behind the same `MIOS_AI_ENDPOINT` — is novel vs the reference
architecture and stays.

## Cross-cutting — how this respects the system's laws

Every phase respects the six Architectural Laws and the operator rules:
- **USR-OVER-ETC / mios.toml + html SSOT** — no hardcoded values; per-phase
  knobs go into the `[skills]`/`[passport]`/`[ttyd]`/`[security]` TOML chain →
  userenv.sh → `MIOS_*` env → the configurator HTML.
- **UNIFIED-AI-REDIRECTS (Law 5)** — every agent/lane resolves the OpenAI-compat
  endpoint from `MIOS_AI_ENDPOINT`; no vendor-hardcoded URLs or ports.
- **No hardcoded English** in agent surfaces; **no hardcoded topic/app
  deny-lists** in router/refine prompts.
- **Immutable code paths / mutable state** — code under `/usr` (bootc-immutable);
  all runtime state under `/var/lib/mios/...` declared via tmpfiles (Law 2).
- **Full offline** — no cloud calls baked in; the catalog/skills/passport
  surfaces are local files + loopback HTTP + pgvector on `:5432`.

Open questions before implementing the remaining open phases:
- Phase A.2: inotify or fanotify? inotify simpler; fanotify
  catches more cases. Default inotify unless operator wants the
  fanotify generality.
- Phase B.2 personas: 4 prompts on hermes-agent (cheaper, all on
  `mios-llm-light`) or 4 isolated model instances (heavier, true
  isolation)?
