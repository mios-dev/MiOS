---
status: proposed
date: 2026-09-19
decision-makers: [operator]
consulted: [research: research_notes/AGY Claude Code translation server/prior_art_and_protocols.md, research_notes/Native AGY and Claude Code patterns/*]
informed: []
---
# Loop translation layer: serve both harnesses, translate the loop, refuse the permission map

## Context and Problem Statement

The request was for "an AGY/Claude Code translation server that supports both APIs". Measurement
says that component cannot be built as stated: **neither harness serves an API to translate.**
Antigravity's SDK *consumes* OpenAI-compatible endpoints (`LocalOpenAIAgentConfig.base_url`) and
exposes no `/v1` listener; Claude Code *consumes* the Anthropic Messages API via
`ANTHROPIC_BASE_URL` and exposes none. Both are clients. So the component in the middle is not a
translator between two servers — it is a **server to both harnesses and a client to both CLIs**.

In the context of running one dev-loop across two harnesses, facing the fact that three quarters
of the naive scope is already shipped by mature third parties, we decided to build a narrow **loop
translation layer** (`loopd` + `xlate`) that occupies the seams both harnesses already have, to
achieve one loop vocabulary across harnesses, accepting that we deliberately do not build a model
gateway, a delegation plugin, or a new protocol.

## Decision Drivers

- **Nothing translates the *loop*.** ACP, MCP, LiteLLM and the six `agy` bridges all model
  *turns, tools and messages*. None models a lane contract with exclusive `owned_paths`, a
  two-sided gate, a negative control that must fail *for the planted reason*, or a status that
  says "reported SUCCESS and changed nothing". That vocabulary is this repo's and it is exactly
  what has to survive a harness crossing.
- **The silent-success defect is the reason to have a middle at all.** Both CLIs return exit 0
  with an empty response over N turns. Only a component that sees the envelope *and* the worktree
  can tell `delivered` from `vacuous`. Neither harness can do that about itself.
- **A wrong permission translation is invisible and unbounded.** `command(git)` and `Bash(git:*)`
  are not the same set in either direction (§5.3 of the reference). A mapper that guesses hands an
  agent capability the operator refused, with no error.
- **Don't duplicate shipped, tested work.** Claude Code Router (MIT, 37k★) and LiteLLM already do
  Anthropic↔OpenAI/Gemini wire translation, with known-hard streaming tool-call bugs
  (litellm #39796, #17246, #20975) a bespoke rewrite would re-discover with worse coverage.
- **Don't invent a protocol that upstream may delete.** ACP is the right *shape* for
  editor↔agent transport (40+ implementations; Zed's Claude adapter Apache-2.0). If Google answers
  antigravity-cli issue #31 with `--acp`, every bespoke transport in this space becomes dead code
  and every ACP-shaped one keeps working.

## Considered Options

1. **Bespoke bidirectional API translation server** (the literal request) — serve an Anthropic
   Messages endpoint and an OpenAI endpoint, translate between them, drive both CLIs.
2. **Adopt ACP** — make each harness an ACP agent, write/reuse an ACP client as the orchestrator.
3. **Adopt an existing bridge** — fork one of the six Claude-Code→`agy` delegation plugins.
4. **Loop translation layer** — an MCP server (already exists here) plus an OpenAI-compatible
   façade, canonical `loop.v1` envelope, loop-aware status vocabulary, a permission mapper that
   *fails closed*, server-owned worktrees, plus a static plugin-format converter.

## Decision Outcome

Chosen option: **4, the loop translation layer**, because it is the only option scoped to the gap
that actually exists. It reuses the two seams both harnesses already expose rather than inventing
a third, it keeps the MCP server this repo already ships as the primary surface, and its distinctive
value — `vacuous` detection, a closed-fail permission mapper, server-owned isolation — is
precisely what options 1–3 do not and structurally cannot provide.

Option 1 is rejected as literally specified: the Anthropic-side half duplicates CCR/LiteLLM, and
"both APIs" describes two client seams, not two servers. Option 2 is rejected **as a dependency**
but adopted **as a lesson**: we take ACP's primitives as the check on our vocabulary and keep an
ACP transport as a later, swappable phase (P6) rather than a foundation, because `agy` has no
native `--acp` and every adapter today needs a separate `agy_acp_server` binary with
non-automatable OAuth. Option 3 solves delegation, not orchestration, and carries none of the gate
semantics.

### Newly measured facts this decision rests on

Probed against the installed `agy` 1.2.6 in this container. These **contradict upstream issue #31
and the pi-go write-up**, both of which state `agy` offers no programmatic orchestration — and the
session channel is not merely documented, it was exercised here across two stateful turns:

- **A stateful multi-turn session over stdio, verified.** Feeding two NDJSON `user` messages to
  one held process: turn 1 stored a number, **turn 2 recalled it correctly**, both under one
  `conversation_id`. The "print mode answers once and dies, so a headless manager cannot wait"
  constraint baked into `scripts/agy_host.sh` is therefore *one mode*, not the only one — and the
  fix for the "manager reports SUCCESS while nothing merges" failure is structural, not a prompt.
- **Input shape** `{"event":"user","message":{"role":"user","content":"…"}}` — `message` is
  top-level, not nested. **Output events** `init` / `step_update` / `result`, with **one `result`
  per turn**, not only at session end.
- **`init` is a capability-discovery surface**: `cwd`, `permission_mode`, and the real **57-tool**
  inventory. The layer can read what a session actually has instead of assuming it.
- **Correction to an earlier reading:** `duration_seconds` and `usage` are present in the
  `--output-format json` envelope too — the two framings carry the *same* payload. `error` and
  `denied_actions` are *conditional*, absent on success. And `num_turns`/`duration_seconds` are
  **cumulative across the session**, so per-turn deltas require subtraction or every budget
  double-counts.
- **Two failure asymmetries:** an *unknown* input event only warns and is ignored — a stream of
  them yields **no `result` event at all**, so absence of a terminal envelope is its own outcome
  and must map to `errored`, never success. A *malformed known* event is fatal.
- **CLI trap:** bare `-p` swallows the next token as its prompt (`agy -p --input-format …` exits 2).
  Flags first, `-p=''` last.
- **Operational prerequisite:** the credential survives a container restart but the keyring daemon
  and `DBUS_SESSION_BUS_ADDRESS` do not; without them `agy` falls back to interactive login and
  times out. `loopd` must start the keyring itself rather than inherit it.
- **`invoke_subagent` works headlessly — the repo's constraint is stale.** Three probes, all
  SUCCESS with `denied_actions` absent: inside a held session; in single-shot `agy -p=` (the
  negative control, which *refuted* the hypothesis that the held session was the enabling factor);
  and single-shot with no prior `define_subagent` (refuting "define before invoke" too). A
  `subagent` step carries each child's own `conversation_id`. A fourth probe **eliminated** the
  leading suspect for the original failure: with `settings.json` deliberately voided by an invalid
  `toolPermission` and `permission_mode` degraded to `request-review`, `invoke_subagent` still
  succeeded — it is ungated by construction, being none of the five permission actions. The cause
  remains unknown, but the constraint no longer rests on it: it was re-keyed onto **process
  lifetime**, which the probes never refuted. Consequence: `loopd` treats a child
  `conversation_id` as a first-class lane handle, and native fan-out is reachable in automation
  through a held session but not through single-shot print mode.
- **Full tool-call and subagent visibility in the stream:** `tool` steps carry `tool_name` and
  `tool_info{parameters,output}`; `subagent` steps carry `subagent_info.subagents[]`. Measured
  `step_type` set: `user_input`, `agent_response`, `tool`, `subagent`, `system_message`. The layer
  reads structured events rather than scraping prose.
- `agy remote-control {start,status,stop}` exists (a background daemon). **Not adopted** — see
  Consequences.

### Confirmation

Each phase in the reference carries its own two-sided control; the decision as a whole is enforced
by these, which fail if it is violated. **None of these gates exists yet** — each is created by the
phase that earns it (reference §9), and this table is the acceptance criterion for this ADR, not a
description of shipped checks:

| Claim | Gate that fails if violated |
|---|---|
| The canonical envelope is lossless over both dialects | `tests/test_loop_envelope.py` — recorded real envelopes (incl. the stream-json line above) normalise to `loop.v1`; a mutated field fails **by name** |
| A do-nothing lane is never reported as success | fixture lane whose worker is `true` must return `vacuous`; asserting `delivered` fails the suite |
| The permission mapper never widens silently | fixture lane whose grants map to `widens`/`none` must be **rejected at validate time**, naming the pair; acceptance fails the suite |
| The server owns isolation | a lane declaring harness-native worktree isolation while the server also isolates is rejected as a second source of truth |
| Depth is not silently flattened | a headless AGY lane declaring `max_depth > 0` is rejected at validate |
| No smuggled model gateway | A gate that inspects `loopd`'s **registered route table at import time** and fails if an Anthropic-Messages path is bound while `[surfaces].messages` is off. Explicitly NOT a source grep: renaming the handler would defeat that, which is Measuring the Wrong Property. Its own negative control plants a bound route and must be caught |

### Consequences

- **Good:** the one genuinely missing component gets built and nothing else does; both existing
  surfaces (`devloop_mcp.py`, `openai-tools.json`) are extended rather than replaced; `vacuous`
  becomes a first-class terminal status instead of a printed warning; a held NDJSON session removes
  the "manager launches and awaits, nothing merges" failure mode at its root rather than by prompt
  instruction.
- **Good:** no dependency on the Antigravity Python SDK — a closed compiled wheel (v0.1.17, six
  platform wheels, no sdist) with `max_subagent_depth` defaulting to 1. The NDJSON CLI channel
  gives the same caller-held session without pinning the layer to Python.
- **Bad:** we own a mapping table that upstream can invalidate monthly; mitigated by
  `adapters.py probe` and by failing closed rather than guessing.
- **Bad:** refusing to auto-translate permissions means some lanes that "would probably be fine"
  are rejected and need a hand-audited entry. Accepted deliberately: the alternative failure is
  silent capability widening.
- **Bad / deferred:** `agy remote-control` registers a daemon with a remote service. Undocumented
  flags, unknown failure mode, and a privacy/ToS surface. Out of scope by default; revisit only on
  an explicit operator decision.
- **Risk, stated:** if Google ships `agy --acp`, P1's transport is superseded. The envelope,
  status vocabulary, permission mapper and worktree ownership are transport-independent and
  survive; only the lane transport is swapped. That is why the transport is the *last* thing the
  design commits to and why P6 exists.

### Audited

An independent `design-audit` lane (research, read-only, run 2026-09-19) audited this ADR and its
reference against SKILL.md section 7 and returned PARTLY_CONFIRMED, naming three claims labelled
`(measured)` that were inferences, three gate promises loose enough to admit a lazy-but-passing
implementation, and one refusal enforced only in prose. Every finding I checked was correct,
including one I would have defended: the reference had asserted that `denied_actions` is *why*
`find_envelope` parses by brace balance, when the real cause -- per that function's own docstring
-- is stderr sharing the stream. An unknown JSON key breaks nothing.

All six were fixed rather than argued with; the audit's own findings file is
`.devloop/findings/DESIGN-AUDIT.md`. (It was merged as 329fe4c before this repo's history
was squashed; cite the findings file, not the SHA -- a citation that cannot be resolved is
exactly the defect this ADR's audit was looking for.) The audit states its limit: it did not
exhaustively check every `(measured)` claim, so more may remain.

## Pros and Cons of the Options

### 1. Bespoke bidirectional API translation server
- Good: matches the literal request; one process.
- Bad: the Anthropic half duplicates two mature MIT projects; inherits their hardest known bugs
  with none of their test coverage; and it still would not detect a lane that did nothing, because
  wire translation never sees the worktree.

### 2. Adopt ACP
- Good: open standard, 40+ agents, MCP-aligned JSON types, models permissions/diffs/terminals
  already; Zed's Claude Code adapter is Apache-2.0 and `jiridanek/agy-acp` is dual Apache-2.0/MIT.
- Bad: `agy` has no native `--acp` (issue #31, opened 2026-05-20, unanswered); every adapter needs
  a separate `agy_acp_server` binary with interactive OAuth that "cannot be automated"; and ACP
  still has no lane/gate/control vocabulary, so it would be transport under this layer, not a
  replacement for it.

### 3. Adopt an existing `agy` bridge plugin
- Good: zero build; several are live and maintained.
- Bad: they model *delegation* (send a task, get a review), not *orchestration*; no worktree
  ownership, no two-sided gate, no vacuous detection, no permission audit. Solves a different
  problem.

### 4. Loop translation layer *(chosen)*
- Good: scoped to the real gap; extends what this repo already ships; every claim is gated by a
  two-sided control; transport-independent.
- Bad: we maintain the mapping table and the façade; closed-fail refusals add operator friction.

## More Information

- Design detail, wire shapes, mapping tables, phasing: `skills/dev-loop/references/translation-layer.md`
- Research: `research_notes/AGY Claude Code translation server/prior_art_and_protocols.md`;
  `research_notes/Native AGY and Claude Code patterns/` (6 notes: customization system, headless
  and permissions, plugins and skills, web and apps, cross-harness interop, API and SDK)
- Upstream, with versions: `agy` 1.2.6 (probed 2026-09-19); `google-antigravity` PyPI 0.1.17
  (Apache-2.0, compiled runtime in platform wheels); Agent Client Protocol (Zed);
  google-antigravity/antigravity-cli issue #31 (`--acp` request, unanswered); MCP revision
  2026-07-28.
- Open operator questions are carried in the reference's §9 — including the two from the v8
  artifact port (`ratchet.md`'s prescribed `git reset --hard HEAD` vs the park-as-patch rule, and
  `critic.py`'s panel vs the existing `review` skill).
