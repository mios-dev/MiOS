<!-- AI-hint: Roadmap for evolving the MiOS agent stack toward the 2025-2026 AgentOS architecture, identifying specific technical gaps (DAG decomposition, deliberative loops, event buses) and the phased engineering plan to resolve them.
     AI-related: mios-agent-pipe, mios-launcher, mios-pc-control, mios-windows, mios-daemon, mios-ollama-cpu, mios-igpu-server, mios-reasoner-cpu, mios-skills, mios-skills-miner -->
# MiOS AgentOS Roadmap

Architectural roadmap for evolving the MiOS agent stack toward the
2025-2026 AIOS / AgentOS reference architecture. Phases ordered by
operator-impact-per-line-of-code, not by formal completeness.

## Current state (pre-roadmap)

| AgentOS principle | MiOS implementation | Gap |
|---|---|---|
| Tripartite layer (App/SDK/Kernel) | OWUI -> mios-agent-pipe (:8640) -> hermes-agent (:8642) | No formal SDK boundary; mios-agent-pipe IS the SDK in practice |
| MCP-style tool execution | mios-launcher broker (CAPTURE_JSON), typed verbs, LiteCUA via mios-pc-control + mios-windows | Strongest piece in MiOS |
| Multi-frontend through one chain | OWUI shipped; Discord/Slack/Telegram pending Step 4/5 | OWUI works; Discord pending |
| Shared cross-cutting state | SurrealDB: agent / session / tool_call / event / kanban_shadow / scratch / agent_metric | Works |
| Local memory (per-agent) | hermes/.hermes/*.db, mios-daemon/state.json, OWUI webui.db | Works |
| CPU light-lane | mios-ollama-cpu at :11435 for micro-LLMs | Live on CPU (ROCm never worked in WSL2 -- kernel doesn't expose /dev/kfd); real AMD iGPU runs natively on the Windows host (mios-igpu-server.ps1, served as mios-reasoner-cpu) |
| Query decomposition into DAG | router emits ONE action; no DAG | **GAP A** |
| Deliberative Collective Intelligence | single-pass critic loop, informal | **GAP B** |
| Document-mutation event bus | hermes-tail/*.json + nudges (polled) | **GAP C** (no inotify pub/sub) |
| Personal Knowledge Graph | flat OWUI memory only | **GAP D** |
| Sequential Pattern Mining | none | **GAP E** |
| Taint-aware memory + Semantic Firewall | none | **GAP F** |
| Agent Passports / crypto identity | sysuser uids only | **GAP G** |

Operator-observed failures these gaps caused:
- "open notepad and type hello and save to documents" -- monolithic
  handling; Hermes tried random paths because no DAG split into
  open_app -> focus -> type -> save chain (GAP A)
- "Hermes claimed it launched but didn't" -- single-pass critic
  didn't FALSIFY the success claim (GAP B)
- daemon polling 3 sideband JSONs at 5-min ticks vs reacting
  on-mutation (GAP C)

## Phase A -- foundational gaps (commit 1-3)

### A.1 -- DAG query decomposition via orchestrator-subagent

**Reference**: Anthropic's multi-agent research system pattern --
NOT DeepSieve verbatim (DeepSieve needs DeepSeek-V3-scale planner;
operator-stack tops out at qwen2.5-coder:7b for the decomposer).
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
- Each node emits a SurrealDB tool_call row tagged with the DAG id
  + parent edges -- gives a full audit trail for multi-step intents.

**Decomposer model**: qwen2.5-coder:7b (function-calling-tuned),
not qwen3:1.7b (too small for reliable multi-hop per community
reports).

### A.2 -- inotify-backed document-mutation event bus

Replace the 3 separate poll loops in mios-daemon (hermes-tail,
delegation-prefilter, log-watcher) with one inotify watcher on
`/var/lib/mios/*/` directories. Hooks emit SurrealDB.event rows.
Agents (mios-daemon, agent-pipe critic, future Kanban dispatcher)
SELECT FROM event WHERE source = X AND ts > <last_seen>.

### A.3 -- Taint-aware memory tags

When agent-pipe's broker dispatch returns a tool_call result whose
source is untrusted (e.g. web fetch, RAG document, external API
response), tag the result content with `tainted = true` before it
enters the chain's context. A small pre-execution check in the
Semantic Firewall (Phase B.3) refuses high-privilege follow-up
verbs (service_restart, container_restart, open_url to non-allow-
listed domain) if any tainted content is in context.

## Phase B -- deliberation upgrade (commit 4-6)

### B.1 -- DCI 14-act vocabulary as structured output

Define the typed-acts schema (14 acts: frame/clarify/reframe,
propose/extend/spawn, ask/challenge, bridge/synthesize/recall,
ground/update, recommend). Each agent reply in deliberation MUST
emit JSON with an `act` field. Lets us tag SurrealDB.event with
the act type + run analytics on which act fired before resolution.

### B.2 -- DCI-CF convergent flow critic (replaces single-pass)

4 personas on hermes-agent + one ollama model (Framer / Explorer /
Challenger / Integrator). Bounded loop: R_max=3 rounds, K_max=4
candidate finalists. Always emits a decision packet {choice,
rationale, minority_report, reopen_triggers}. Tensions preserved
as first-class objects in SurrealDB.event(kind="dissent").

Single-model role-playing works per the DCI paper (Gemini 2.5
Flash, 4 differentiated system prompts). Diversity helps but isn't
required.

### B.3 -- Semantic Firewall pre-MCP-dispatch

Small Python layer in agent-pipe. Before any WRITE-class verb
fires, check:
- Operator's original DAG (from A.1) authorized this verb
- No tainted content (from A.3) in agent context
- Action target is consistent with the DAG node's `args`
On violation: abort + emit SurrealDB.event(kind="firewall_block",
severity="high") + surface to operator.

## Phase C -- long-horizon autonomy (commit 7+)

### C.1 -- Personal Knowledge Graph in SurrealDB graph mode

SurrealDB is multi-model -- native graph support. New tables:
`person`, `pref`, `device`, `app_install`, with RELATE edges. Per-
operator graph queried by router/refine to ground ambiguous terms
("my browser" -> RELATE preference -> chromedev).

### C.2 -- Sequential Pattern Mining over tool_call history  *(landed)*

Implemented as:

* `usr/share/mios/surrealdb/schema-init.surql` -- new tables:
  `skill` (catalog row, param-templated body), `skill_invocation`
  (per-run audit), `emitted` (RELATE skill_invocation -> tool_call,
  used by the miner to subtract codified runs), `includes`
  (RELATE skill -> skill, sub-skill composition).
* `usr/libexec/mios/mios-skills` -- stdlib-only CLI:
  `mine / list / show / run / promote / retire / delete /
  import / export / openai-tools / export-catalog`. The miner
  enumerates contiguous N-grams of (verb, args-shape) over
  session-bucketed tool_calls, counts support + unique-session
  witness, auto-promotes when confidence crosses the SSOT-driven
  `auto_promote_threshold`.
* `usr/lib/mios/agent-pipe/server.py` -- new endpoints:
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
    3. Direct SurrealDB read on the `skill` table (any agent that
       can talk to :8000).
* SSOT: `[skills]` in mios.toml -- `enable`, `min_length`,
  `max_length`, `min_support`, `window_hours`,
  `auto_promote_threshold`, `mine_interval_minutes`,
  `seed_catalog_dir`, `local_catalog_dir`. All routed through
  userenv.sh + the configurator HTML "Skills" section.

### C.3 -- Agent Passports (signed identity tokens)  *(landed)*

Implemented as:

* `usr/share/mios/surrealdb/schema-init.surql` -- new
  `agent_keypair` registry table + `passport` (option<object>
  FLEXIBLE) field on tool_call / skill_invocation / event /
  agent_metric. Optional + FLEXIBLE so legacy rows stay readable
  and v2-envelope additions (delegation chain headers) don't
  break the schema.
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
  open` builds its CREATE manually and explicitly attaches the
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

`usr/share/mios/skills/write-text-file.json` -- new seed
template demonstrating text_create -> text_view as the native
replacement for save-document's pc_type chain.

### D.2 -- ttyd browser pty bridge  *(landed)*

Operator directive 2026-05-18: "add ttyd to the stack so we can
access PowerShell from a local browser(s)". Two systemd-managed
ttyd instances expose pty-over-WebSocket bridges:

  * `mios-ttyd-bash.service`         :7681  ->  `ttyd ... /bin/bash`
  * `mios-ttyd-powershell.service`   :7682  ->  `ttyd ... mios-powershell --shell`

`mios-powershell --shell` (new mode in the existing shim) execs
`pwsh.exe` (preferred) / `powershell.exe` interactively via WSL
interop, inheriting the ttyd pty. The browser tab sees a real
Windows PowerShell prompt over WebSocket.

Hardening:
  * Both bound to 127.0.0.1 by default.
  * `mios-ttyd-launch` refuses to bind beyond loopback without
    `auth_user` + `auth_pass` when `require_auth` is true.
  * Optional TLS termination via `ssl_cert` + `ssl_key`.

SSOT: `[ttyd]` in mios.toml + `[ports].ttyd_bash` /
`.ttyd_powershell` + the userenv.sh slot map +
configurator HTML "ttyd" section.

Package: `ttyd` in `packages-ttyd` of usr/share/mios/PACKAGES.md
(Fedora 44 ships v1.7.7).

## What stays put

The MCP-style execution layer (mios-launcher broker, mios-pc-
control, mios-windows, typed verbs) is already strong; the
research validates it. No changes planned. The dual-ollama lane
(iGPU micro-LLMs / dGPU big models) is novel vs the reference
architecture and stays.

## Cross-cutting

Every phase respects the existing operator rules:
- mios.toml + html SSOT (no hardcoded values; per-phase knobs go
  into the TOML chain)
- no hardcoded English in agent surfaces
- bootc-immutable code paths; mutable state under /var
- full offline; no cloud calls baked in

Open questions before implementation:
- Phase A.1 decomposer model: confirm qwen2.5-coder:7b vs trying
  Hermes-3-8B (more tool-tuned)
- Phase A.2: inotify or fanotify? inotify simpler; fanotify
  catches more cases. Default inotify unless operator wants the
  fanotify generality.
- Phase B.2 personas: 4 prompts on hermes-agent (cheaper) or 4
  separate ollama instances (heavier, true isolation)?
