# The loop translation layer — design

Companion to ADR `docs/decisions/0001-loop-translation-layer-*.md` (status: proposed). The ADR
carries the decision and the rejected alternatives; this file carries the design.

Everything marked **(measured)** was probed against the tools installed in this container. Version
stamps are in §10. Nothing here is inferred from a vendor blog.

---

## 1. The reframe

"Translate AGY's API to Claude Code's API" is unbuildable as stated, because **neither harness
serves an API that a translator could sit in front of**. Scope of the evidence, stated honestly
after an audit flagged this as an overclaim: what was measured is that neither CLI exposes a
documented listener -- no `/v1` route, and no serve verb in `agy --help` other than `mic-serve`.
What was NOT measured is whether `agy remote-control`'s daemon or any undocumented flag serves
something; that daemon registers with a remote service and was deliberately left unprobed (8.4).
The design does not depend on the stronger claim: it needs only that there is no *documented,
local, OpenAI- or Anthropic-shaped* endpoint to translate, which is what the table shows.

| Harness | What it serves | What it consumes |
|---|---|---|
| Antigravity (`agy`, SDK) | nothing — no `/v1/chat/completions`, `/v1/embeddings`, `/v1/models`; the only `serve` verb in `agy --help` is `mic-serve` | OpenAI-compatible endpoints via `LocalOpenAIAgentConfig.base_url` ("any external OpenAI-compatible completions API"), MCP servers |
| Claude Code | nothing | Anthropic Messages API via `ANTHROPIC_BASE_URL`, MCP servers |

Both are clients. The component in the middle is therefore **a server to both harnesses and a
client to both CLIs** — the inversion is the whole design. It occupies seams that already exist
and invents no protocol.

### Seam inventory (all first-party, all measured)

| Seam | Harness | Direction | Used by this design |
|---|---|---|---|
| MCP stdio / streamable HTTP | both | harness calls out | **yes — primary surface** |
| `LocalOpenAIAgentConfig.base_url` | AGY | AGY calls out | **yes — the only way AGY consumes a backend** |
| `ANTHROPIC_BASE_URL` | Claude Code | Claude calls out | deferred (§6.3) — CCR/LiteLLM's job |
| `--input-format stream-json` / `--output-format stream-json` NDJSON over stdio | `agy` | **caller drives** | **yes — lane transport (P1)** |
| `claude -p --output-format stream-json` | Claude Code | **caller drives** | **yes — same shape** |
| plugin tree `.claude-plugin/plugin.json` | Claude Code | harness loads in | `xlate` target |
| `.agents/` customization tree, `agy plugin import` | AGY | harness loads in | `xlate` target (import is one-way and lossy) |
| `agy remote-control {start,status,stop}` | `agy` | caller drives a daemon | **no — out of scope, §8.4** |

---

## 2. Scope refusals — what this layer does NOT build

Three quarters of the naive scope is shipped, tested, and maintained by other people. Building it
again is duplication with worse coverage.

| Naive component | Already solved by | Verdict |
|---|---|---|
| Model-wire translation (Anthropic Messages ↔ OpenAI/Gemini) | Claude Code Router (MIT, 37k★); LiteLLM | **Do not build.** Documented, mature, and their open streaming tool-call bugs (litellm #39796, #17246, #20975) are exactly what a rewrite re-discovers. |
| "Claude Code delegates a task to `agy`" | ≥6 community plugins (`iicmaster/antigravity-plugins`, `yuting0624/antigravity-for-claude-code`, …) | **Do not build.** Fork one if delegation is what you want. |
| Agentic transport fidelity: streaming, permission prompts, diffs, terminals, session resume | ACP (Agent Client Protocol) — 40+ agents; Zed's Claude adapter Apache-2.0; `jiridanek/agy-acp` | **Adopt the lesson, defer the dependency** (§8.5, P6). |
| A2A / AGNTCY ACP / IBM ACP | — | **Wrong layer or absorbed.** A2A is cross-organisational networked delegation with Agent Cards and payments; semantically wrong for two local CLIs. The other two folded into A2A. |

**What nobody has built:** a translator for the *loop*. ACP models an editor driving one agent
turn by turn. It has no notion of a lane contract with exclusive `owned_paths`, a two-sided gate, a
negative control that must fail *for the planted reason*, an idempotence assertion, or a status
meaning "reported SUCCESS and changed nothing". That vocabulary is `SKILL.md` §6–§7's, and it is
exactly what must survive a harness crossing.

---

## 3. Components

### 3.1 `loopd` — the loop daemon (runtime)

One process. Serves three dialects of one loop; drives both CLIs as subprocesses.

### 3.2 `xlate` — the static format converter

`.claude-plugin/` ↔ AGY `.agents/` customization tree. Pure transform, no runtime. Google ships
`agy plugin import` (two importers over a `common.Stager`: `StageAgents, StageCommands, StageHooks,
StageMCPServers, StageSkills`) but it is **one-way and lossy**, and the staged symbol list contains
no counterpart for Claude's `settings.json` permission model. That last point is a *proxy*: the
absence of a `StagePermissions`-shaped symbol is suggestive, not a functional test that permissions
cannot be carried. Treat it as unverified until an import is run end to end and the resulting
`settings.json` inspected. There is no export verb. `xlate` closes the return
path and handles the permission gap the only safe way: **by refusing** (§5.3).

---

## 4. Process model

Constraints in tension: the Antigravity SDK is Python-only and its runtime ships as a **closed
compiled binary** inside six platform wheels (no sdist), with `max_subagent_depth` defaulting to
**1**. MiOS's standing directive is Rust static binaries.

Resolution:

- **`loopd` core drives CLIs, not SDKs.** No `google-antigravity` dependency, no
  `claude-agent-sdk` dependency. The NDJSON stdio channel gives the same caller-held session
  without pinning the layer to Python or to a closed wheel.
- **Language:** P0–P3 land as Python in this repo (its existing language, alongside
  `adapters.py`/`devloop_mcp.py`). The Rust-static-binary directive applies when/if `loopd` moves
  into MiOS `tools/native/`; the ports, the schema and the mapping table are the portable parts and
  the HTTP/stdio plumbing is the throwaway part. Stated plainly rather than pretended.
- **Lane execution:** one subprocess per lane, **stdin held open**:
  - AGY lane — `agy --input-format stream-json --output-format stream-json --json-schema <report.schema.json> --print-timeout 0 -p=''` (flag order is load-bearing — see §5.1a)
  - Claude lane — `claude -p --output-format stream-json --json-schema <report.schema.json>`

  This replaces today's shell-out-and-die model in `adapters.py`. It is the root fix for the
  observed "manager reports SUCCESS while nothing merges": today `agy_host.sh` compensates with a
  prompt instruction (run `devloop.sh` synchronously in the foreground) because print mode answers
  once and exits, killing backgrounded children. A held session removes the reason for that
  instruction instead of restating it.
- **Concurrency:** one `loopd`, N lane subprocesses, **one shared credential** in the keyring —
  so the keyring must be up before fan-out or every lane re-auths and burns its budget hanging.
  Measured: the credential file survives a container restart but the daemon and
  `DBUS_SESSION_BUS_ADDRESS` do not, so `loopd` runs `scripts/env/agy-keyring.sh` and loads
  `~/.config/agy-cloud/keyring.env` itself at startup rather than inheriting a shell that
  happens to have it.

---

## 5. The four translations, and the one refusal

### 5.1 Envelope normalisation

Measured end to end against `agy` 1.2.6 and `claude -p`. **The two AGY framings carry the same
payload**: `--output-format json` emits the result object bare; `--output-format stream-json` wraps
that identical object as `{"event":"result","result":{…}}`. There is one AGY shape, two framings.

```
agy --output-format json          # success, measured verbatim
  {"conversation_id":"da9f0586-…","status":"SUCCESS","response":"PROBE_OK\n",
   "duration_seconds":2.657665837,"num_turns":1,
   "usage":{"input_tokens":12569,"output_tokens":38,"thinking_tokens":34,
            "cache_read_tokens":0,"total_tokens":12607}}

agy --output-format stream-json   # same object, wrapped per line
  {"event":"result","result":{ …identical keys… }}

claude -p --output-format json
  {result, num_turns, permission_denials[], …}
```

**Conditional keys.** `error` and `denied_actions` are *absent on success*, not null. A consumer
that reads `env["denied_actions"]` unconditionally raises; one that reads `env.get("status")` and
trusts it is worse (§5.2). Measured success key set, exactly:
`['conversation_id','duration_seconds','num_turns','response','status','usage']`.

**Cumulative counters.** In a multi-turn session `num_turns` and `duration_seconds` are
**cumulative across the session**, not per-turn: successive result events measured 1 → 2 turns and
1.20s → 2.29s. `loop.v1.turns` and `duration_s` therefore mean *cumulative at this result*, and a
per-turn delta requires subtracting the previous result. Getting this wrong silently double-counts
every budget.

| `loop.v1` | from AGY (either framing) | from Claude json |
|---|---|---|
| `text` | `response` | `result` |
| `turns` | `num_turns` *(cumulative)* | `num_turns` |
| `denials` | `denied_actions[]` *(absent when empty)* | `permission_denials[]` |
| `usage` | `usage{input,output,thinking,cache_read,total}` | *(harness-specific; normalise or omit)* |
| `duration_s` | `duration_seconds` *(cumulative)* | *(caller wall-clock)* |
| `error` | `error` *(absent on success)* | *(absent)* |
| `status` | **not** `status` — see §5.2 | **not** the exit code |

Two things this table must never do: trust the harness's own `status` field, and trust exit 0.
`denied_actions` is **undocumented but real** (measured). A separate point, previously and wrongly
stated here as its consequence: `adapters.py.find_envelope()` locates the envelope by brace balance
rather than `json.loads` because anything sharing the stream breaks a whole-text parse -- agy prints
its auto-denial notice to stderr, so a caller merging the streams gets prose wrapped around the JSON
(see the function's own docstring). An unknown KEY would not break `json.loads` at all; unknown
*text* would. The two facts are unrelated.

### 5.1a The AGY session protocol (measured end to end)

This is the transport P1 is built on. It was verified by a stateful two-turn session, not inferred
from `--help`: turn 1 stored a number, turn 2 recalled it correctly, both under one
`conversation_id` in one process.

**Invocation.** Flags first, prompt attached to the flag:

```sh
agy --input-format stream-json --output-format stream-json --print-timeout 0 -p=''
```

*CLI trap (measured):* bare `-p` swallows the **next token** as its prompt —
`agy -p --input-format stream-json` fails with *"-p took \"--input-format\" as its prompt"*, exit 2.
Always `-p='…'` or `-p=''`.

**Input**, one NDJSON object per line on stdin, stdin held open:

```json
{"event":"user","message":{"role":"user","content":"…"}}
```

The `message` field is **top-level**, not nested under `user`. Discovered by probe; the error that
names it is *"stream input \"user\" message is missing the \"message\" field"*.

**Output events** (`{"event":"<t>","<t>":{…}}`):

| event | Payload | Use |
|---|---|---|
| `init` | `conversation_id`, `cwd`, `tools[]` (**57** measured), `permission_mode` | **capability discovery** — read the real tool inventory and effective permission mode at session start instead of assuming them |
| `step_update` | `step_index`, `state` (`ACTIVE`/`DONE`), `step_type`, `text_delta`, per-step `duration_seconds`/`usage`; **tool** steps add `tool_name` + `tool_info{parameters,output}`; **subagent** steps add `subagent_info.subagents[]{type_name,role,initial_prompt,conversation_id}` | incremental streaming **with full tool-call and subagent visibility** — everything the layer needs for observability, without scraping prose. `step_type` is the same vocabulary AGY's hook matchers use |
| `result` | the §5.1 object | **one per turn**, not only at session end |

**`step_type` vocabulary, measured:** `user_input`, `agent_response`, `tool`, `subagent`,
`system_message`. A `subagent` step carries each child's own `conversation_id`, which is the
handle `loopd` uses to attribute a child's work to a lane.

**Two failure asymmetries the layer must encode:**

- An **unknown** input event is a *warning*, ignored: `warning: ignoring unsupported stream input
  message event "…"`. A stream of only-unknown events produced **no `result` event at all** — so
  *absence of a terminal envelope* is its own outcome and must map to `errored`, never to success.
  This is the §7 Skip-as-Pass shape at the protocol layer.
- A **malformed known** event is *fatal*: it emits an ERROR result and aborts the stream.

**Operational prerequisite (measured).** The credential persists in the keyring file across
container restarts, but the daemon and `DBUS_SESSION_BUS_ADDRESS` do not. Without them `agy` falls
back to interactive login and times out. Every invocation needs
`bash scripts/env/agy-keyring.sh` once, then `. ~/.config/agy-cloud/keyring.env` in the calling
shell. `loopd` must do this itself rather than inherit it, or a fan-out silently degrades into N
auth prompts.

### 5.2 Status vocabulary — representing "reported SUCCESS but did nothing"

The reason to have a middle at all. Both harnesses return exit 0 with an empty response over N
turns, and `{"status":"SUCCESS","response":"","num_turns":1,"denied_actions":[…]}` is a shape that
was observed live. Only a component that sees **both the envelope and the worktree** can tell the
difference. Neither harness can do that about itself; neither can a wire gateway.

| `loop.v1.status` | Decided from evidence, never from the harness's word |
|---|---|
| `delivered` | envelope ok **and** worktree diff non-empty **and** both controls ran |
| `refused` | `denials` non-empty — the harness declined work |
| `vacuous` | envelope claims success, `denials` empty, **diff empty** — the silent-failure case |
| `gate_failed` | positive control failed, **or** negative control passed (failed to fail), **or** failed for the wrong reason |
| `control_invalid` | negative control did not restore the tree, or the baseline was already broken — `SKILL.md` §6's *"a broken control does not weaken your proof; it inverts it"*; exit 2 today |
| `errored` | non-zero exit, or `error` set |
| `timed_out` | wall-clock exceeded. **Never** collapsed into success (§7 Timeout-as-Pass) |

`vacuous` is the point. Today `adapters.py denials` prints a warning; in `loop.v1` it is a
first-class terminal status the orchestrator must handle and that cannot be mistaken for
`delivered`.

### 5.3 Permission mapping — the layer must **refuse** to auto-translate

Measured asymmetry. AGY's permission grammar has exactly five live actions — `read_file`,
`write_file`, `command`, `url`, `mcp` (plus deprecated `unsandboxed`). Everything else
(`edit_file`, `list_dir`, `grep_search`, `run_command`, `invoke_subagent`, …) is rejected as
"unknown action" **into the log only**. `command(x)` prefix-matches **the first token only**.
`read_file(*)` is universal; `read_file(/repo/**)` is *accepted and matches nothing*. Claude Code
uses a different algebra entirely (`Bash(git:*)`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, …).

**First, a distinction the grammar hides.** AGY's permission *actions* are not its tool *names*.
The `init` event lists **57 tools** — `run_command`, `view_file`, `write_to_file`,
`replace_file_content`, `grep_search`, `find_by_name`, `list_dir`, `invoke_subagent`,
`define_subagent`, `list_permissions`, … — while `settings.json` accepts exactly five actions
(`read_file`, `write_file`, `command`, `url`, `mcp`). That is precisely why `list_dir` is rejected
as an action while being a perfectly real tool: many tools collapse onto one action. Any mapper
built from the tool list instead of the action list is wrong in both directions.

There is no total function between them:

| Pair | Why it is not an equivalence |
|---|---|
| `command(git)` → `Bash(git:*)` | AGY's rule also matches `git-anything`; and `cd x && git push` is matched by `command(cd)`, **not** `command(git)`. Wider in one direction, blind in another. |
| `Bash(git:*)` → `command(git)` | Claude's rule does not grant `cd`. The working AGY equivalent needs `command(cd)` too — which grants **every** command after `&&`. |
| `Read` scoped to a path → `read_file(<path>)` | AGY has no path globbing. The honest translation of a scoped Claude read is the **universal** `read_file(*)`: a silent widening. |
| anything → `invoke_subagent` | Not an action name at all. Accepted into the log, enforced nowhere. |

**Design rule: the mapper is partial and fails closed.** `loopd` ships a declared, hand-audited
table with a verdict per pair — `exact | widens | narrows | none`. A lane whose requested grants map
to `widens` or `none` is **rejected at validate time with the offending pair named**, never
silently translated. Rationale: a wrong mapping does not crash. It hands an agent a capability the
operator refused, invisibly. That is the worst failure mode in the design and the only one where
refusing beats guessing.

One more measured trap the mapper must encode: `toolPermission` takes exactly
`always-proceed | request-review | strict`, and **an unrecognised value voids the entire settings
file** — silently discarding `permissions.allow`, `trustedWorkspaces` and
`allowNonWorkspaceAccess`. A mapper that emits a plausible-but-invalid value disables every grant
it just wrote. `xlate` must validate the enum against the binary's accepted set, not against a doc.

### 5.4 Subagent depth and fan-out asymmetry

| Context | Depth | Fan-out |
|---|---|---|
| Claude Code | nesting depth 3 (plugin-shipped agents) | 20 concurrent subagents |
| AGY interactive | `invoke_subagent`, `workspace: branch`, ≤ 10 | native |
| AGY headless `-p` **and** held stream-json | `invoke_subagent` **works** (measured, 1.2.6) | **native fan-out is reachable headlessly** |
| AGY Python SDK | `max_subagent_depth` default **1** | flat delegation |

**Correction, with its controls.** An earlier live observation recorded `invoke_subagent` failing
under headless `agy -p`, and both `agy_host.sh` and `harness-adapters.md` are built on it. Three
probes refute it — each one an attempt to falsify the previous conclusion, and each one succeeding
at refuting *me* rather than the tool:

| # | Probe | Result |
|---|---|---|
| a | held stream-json session: `define_subagent` then `invoke_subagent` | SUCCESS — `subagent` step emitted, child `conversation_id`, `manage_subagents` lists 1 active |
| b | **negative control** — identical prompt in single-shot `agy -p=` | SUCCESS, so the held session is *not* the enabling factor (hypothesis refuted) |
| c | single-shot, `invoke_subagent` with **no** prior `define_subagent` | SUCCESS, so "define before invoke" is *not* the rule either (hypothesis refuted) |

All three: `status: SUCCESS`, `denied_actions` absent. The honest conclusion is narrow — in 1.2.6
under `permission_mode: always-proceed`, `invoke_subagent` works headlessly, and the repo's
constraint is stale. **The cause of the original failure remains unexplained.** The leading
candidate, unproven, is that the settings file was voided at the time by an invalid
`toolPermission` value (§5.3), which discards `permissions.allow` wholesale and silently. Recorded
as an open item rather than asserted.

Design consequence: AGY native fan-out is available to a headless manager, so `agy_host.sh`'s
mode-dependent rule forbidding `invoke_subagent` under `--headless` is over-restrictive and the
native topology AGENTS.md prescribes is reachable in automation. `loopd` should therefore treat a
subagent's child `conversation_id` as a first-class lane handle.

`loopd` normalises by declaring `max_depth` in the lane contract and **refusing** a lane whose
declared depth exceeds what the target harness *and mode* can serve — rather than letting it
silently flatten. A headless AGY lane with `max_depth > 0` is rejected at validate, pointing at the
interactive path or at `devloop.sh` dispatch. This promotes `agy_host.sh`'s current mode-dependent
`$DISPATCH_RULE` from prompt text into a validated contract field, where it can be tested.

---

## 6. Interfaces

### 6.1 MCP — primary surface

Extends the nine tools `devloop_mcp.py` already serves (`validate_lanes`, `run_lanes`, `gate`,
`probe`, `tasks_next`, `task_set`, `ledger`, `report`, `scaffold`). Stateless-by-call stays; the
session handle is explicit:

| Tool | In | Out |
|---|---|---|
| `lane_open` | `{lane_path, worktree}` | `{session_id}` — starts a held NDJSON session |
| `lane_send` | `{session_id, message}` | `loop.v1` envelope for that turn |
| `lane_close` | `{session_id}` | final `loop.v1` envelope; prunes the worktree |
| `xlate` | `{src, src_format, dst_format, dry_run}` | `{written[], refusals[]}` |

Both harnesses consume MCP natively, so this surface needs no translation at all — which is why it
is primary.

### 6.2 OpenAI-compatible `/v1` — the surface AGY can consume as a backend

- `GET /v1/models` → one id per lane role: `dev-loop/orchestrator`, `dev-loop/lane-worker`,
  `dev-loop/auditor`, `dev-loop/researcher`, `dev-loop/triage`.
- `POST /v1/chat/completions` → runs a loop turn. Tool calls surface as OpenAI function calls from
  the existing `assets/openai-tools.json`. `stream: true` supported (SSE).
- AGY points `LocalOpenAIAgentConfig.base_url` here and a **lane appears to AGY as a model**. This
  is the only direction AGY natively supports, which is what makes the façade worth building at all.
- Auth: bearer token read from a 0600 file. **Never an env var** — Law 11 shape
  (`SECRETS-NEVER-IN-ENV`), and Law 10 forbids it in `install.env` regardless.

### 6.3 Anthropic Messages `/v1/messages` — deferred

The seam `ANTHROPIC_BASE_URL` occupies. Only needed for "Claude Code's own loop runs on a Gemini
model", which is Claude Code Router's and LiteLLM's job. Ship only if the operator prefers one
process over two, and gate it behind `[surfaces].messages` so `validate.sh` can assert it is absent
by default (a smuggled model gateway is scope creep with a known bug surface).

---

## 7. Worktree isolation is the server's, exclusively

`agy` 1.2.6 has **no worktree flag** — `--add-dir` adds a directory to the workspace, it does not
branch (measured). Claude Code has native `isolation: worktree`.

Therefore **`loopd` owns isolation for every lane in every harness**: it creates the worktree,
passes it as cwd / `--add-dir`, runs both controls in it, and prunes it. A harness's native
worktree support is an optimisation used only when the server is *not* already isolating — never a
second source of truth.

Rationale: two isolation owners means two answers to "where is this lane's diff", and the entire
`vacuous` detector (§5.2) depends on there being exactly one.

---

## 8. Deliberate non-adoptions

1. **`google-antigravity` SDK** — closed compiled runtime, no sdist, `max_subagent_depth` 1, pins
   the layer to Python. The NDJSON CLI channel gives the same caller-held session.
2. **`claude-agent-sdk`** — purpose-built for one vendor; hosting another vendor's agent is an open
   upstream issue. We drive the CLI.
3. **A2A / AGNTCY ACP / IBM ACP** — wrong layer, or absorbed into A2A.
4. **`agy remote-control`** — a real daemon (`start|status|stop`, measured) but undocumented flags,
   unknown failure mode, and it registers with a remote service: a privacy and ToS surface. Out of
   scope by default; explicit operator decision only.
5. **ACP as a foundation** — right *shape*, wrong *time*. `agy` has no native `--acp`
   (antigravity-cli issue #31, opened 2026-05-20, assigned, unanswered, no milestone); every
   adapter today needs a separate `agy_acp_server` binary with interactive OAuth that cannot be
   automated. Kept as P6, a swappable transport. The envelope, status vocabulary, permission mapper
   and worktree ownership are all transport-independent and survive the swap — which is why
   transport is the last thing this design commits to.

---

## 9. Phasing — each phase independently verifiable, two-sided

| Phase | Deliverable | Positive control | Negative control (must fail, by name) |
|---|---|---|---|
| **P0** | `loop.v1` JSON Schema + the AGY/Claude mapping table | recorded real envelopes (incl. the stream-json result line in §5.1) normalise correctly | a mutated field fails naming **that field**, not a generic parse error |
| **P1** | Held NDJSON sessions replace shell-out-and-die | a two-turn lane where turn 2 depends on turn 1's state completes | the same lane through a single-shot adapter must fail **at turn 2, with turn 1 having succeeded and the failure naming the lost state**. A crash before turn 1 (missing import, absent credential) does NOT satisfy this control and fails the suite as inconclusive |
| **P2** | `vacuous` wired to diff-emptiness | a lane that edits a file returns `delivered` | a lane whose worker is `true` returns `vacuous` — asserting `delivered` fails the suite |
| **P3** | Permission mapper, failing closed | a lane whose grants map `exact` validates | a fixture lane mapping `widens`/`none` is **rejected**, naming the pair; acceptance fails the suite |
| **P4** | `/v1` façade | an AGY lane configured via `LocalOpenAIAgentConfig` completes a turn through `loopd` | with no backing lane the façade errors **while the same request against a live lane succeeds in the same test run** -- an unconditional error for every request fails the control, since it cannot distinguish absence from breakage |
| **P5** | `xlate` | round-trip a plugin; structure preserved | the permission block is **refused**, not translated; a silent translation fails the suite |
| **P6** | *(optional)* ACP transport | same lane passes over ACP | envelope/status/permissions unchanged across transports |

Sequencing note: P0–P2 deliver the whole value of the middle (one vocabulary, silent-failure
detection) and depend on nothing external. P3 is the safety phase. P4 onward is reach.

---

## 10. Provenance

All version-stamped; probed in this container unless marked otherwise.

- `agy` **1.2.6** — `--help` surface; `remote-control` subcommand; absence of any worktree flag;
  absence of a serve verb other than `mic-serve`; the permission grammar (5 live actions,
  first-token prefix match, no path globbing) and its distinction from the 57-tool inventory;
  the `toolPermission` enum and its file-voiding behaviour; `invoke_subagent` failing under `-p`;
  `denied_actions` in the envelope.
- `agy` **1.2.6 session protocol** — verified by a stateful two-turn NDJSON session (turn 1
  stored a value, turn 2 recalled it, one `conversation_id`, one process): the `user`/`message`
  input shape, `init`/`step_update`/`result` output events, one `result` per turn, cumulative
  `num_turns`/`duration_seconds`, conditional `error`/`denied_actions` keys, warning-vs-fatal
  asymmetry on bad input, the `-p` token-swallowing trap, and the keyring/DBUS prerequisite.
- `google-antigravity` PyPI **0.1.17**, Apache-2.0, `requires_python >=3.10`, six platform wheels,
  no sdist; `LocalOpenAIAgentConfig`; `max_subagent_depth` default 1. *(docs + package metadata)*
- Claude Code — plugin auto-discovery, declaration merge/replace semantics, depth 3 / 20
  concurrent subagents, `permission_denials` envelope key.
- MCP revision **2026-07-28** (the version `devloop_mcp.py` already negotiates).
- Prior art and licences: `research_notes/AGY Claude Code translation server/prior_art_and_protocols.md`.
- Round-1 notes: `research_notes/Native AGY and Claude Code patterns/` (6 files).

**Two upstream sources are contradicted by measurement.** antigravity-cli issue #31 and the pi-go
write-up both state `agy` has only three modes and offers no programmatic orchestration. The
installed binary has a working bidirectional NDJSON session channel — not merely documented in
`--help`, but exercised here across two stateful turns. Design against the binary.

---

## 11. Open questions for the operator

Carried forward, unanswered:

1. **`ratchet.md` prescribes `git reset --hard HEAD`** (v8 artifact port). That is on the
   confirm-before list and destroys uncommitted lane work. Proposal: park the diff as a patch per
   `SKILL.md` §11 instead. Confirm the substitution?
2. **`critic.py`'s maker-checker panel vs the existing `review` skill** — merge the panel into
   `review`, or keep them as separate stages? They overlap on DRY/KISS/SRP/security.

New, raised by this design:

3. **`agy remote-control`** — out of scope by default (§8.4). Confirm, or investigate?
4. ~~AGY auth lapsed in this container.~~ **Resolved — no re-login was needed.** The credential
   had persisted; only the keyring daemon and `DBUS_SESSION_BUS_ADDRESS` were missing after a
   container restart. `scripts/env/agy-keyring.sh` plus sourcing `~/.config/agy-cloud/keyring.env`
   restored it, and P1's transport was then verified end to end (§5.1a). Standing requirement,
   not a question: `loopd` must do this itself at startup.
5. **Partly settled.** The leading candidate for the original `invoke_subagent` failure — a
   settings file voided by an invalid `toolPermission` — was tested and **eliminated**: with the
   file voided and `permission_mode` degraded to `request-review`, `invoke_subagent` still
   succeeded. It is ungated by construction (not one of the five permission actions), so no
   permission state explains the failure. **The cause is still unknown**, but the *rule* no longer
   depends on knowing it: the constraint was re-keyed onto process lifetime, which the original
   comment had argued correctly all along and which the probes never refuted — every subagent they
   invoked finished inside its dispatching turn. `--session` (held stream-json, `agy_session.py`)
   permits native lanes because the process outlives a turn; `--headless` still does not.
   Controls: `tests/test_agy_dispatch_rule.py`.
6. **Build vs adopt on transport** — this design takes ACP's lesson but not its dependency. Want
   `jiridanek/agy-acp` evaluated as an alternative lane transport at P6, or is the NDJSON channel
   sufficient?
