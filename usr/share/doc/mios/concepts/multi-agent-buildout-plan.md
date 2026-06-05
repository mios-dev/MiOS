# Multi-Agent Concurrent Buildout Plan (remaining AIOS workstreams)

> 2026-06-04. Plan to fan out the remaining workstreams across concurrent agents.
> Companion to `aios-implementation-plan.md`. Runnable as a Workflow (script
> below) — opt-in, operator-launched.

## 1. What can actually be parallelized

Agents run in the SAME repo-editing environment I do — they can write code +
scaffolding, but they **cannot** deploy, bake GGUFs, touch GPU VRAM, build an
image, or boot-test. So concurrency accelerates the **scaffolding/code** half;
the **live** half stays operator-gated.

| Workstream | Agent-parallelizable (scaffolding) | Operator-gated (live) |
|---|---|---|
| WS-2 Code Mode | coderun verb + tool-as-local-API shim + tests | the coderun container running |
| WS-4 computer-use P0 | doc-gen CLI tools + recipes + OWUI tool file | LibreOffice/Pandoc in image + OWUI pipe deploy |
| WS-7 UKI/fapolicyd | fapolicyd policy + UKI build step **(gated, NON-enforcing)** | image build + boot/rollback test |
| WS-8 kv_fork spike | `kv_fork` on `_kv_paging` + a unit test | vLLM/VRAM lanes |
| WS-10 GGUF/llama-swap | **done** (38-llamacpp-prep.sh, quadlet, config) | GGUF bake + live tune |

## 2. The hard part — avoiding concurrent-edit conflicts

WS-2/4/7/8 all touch the SAME shared files (`mios.toml`, `sysusers.d/50-mios-
services.conf`, `tools/lib/userenv.sh`, `automation/15-render-quadlets.sh`,
`server.py`). N agents editing those at once = corruption (we already saw a
stray-edit corrupt `server.py`'s tail this session).

**Design — builders never touch shared files; a synthesis stage does, serially:**

- **Build (parallel, 4 agents):** each agent creates ONLY its workstream's NEW
  files (distinct paths → zero conflict) and **returns** the edits it needs to
  shared files as structured `shared_edits` (it does NOT apply them). Pre-assigned
  uids/ports in the prompts prevent identity collisions.
- **Synthesize (sequential, 1 agent):** applies every `shared_edit` to the shared
  files in order, resolves any uid/port overlap, keeps each feature DEFAULT-OFF/
  gated, then runs `py_compile` + `tomllib` + `bash -n` and reports.
- **Verify (parallel, 1 per workstream):** adversarial review — parses/compiles,
  follows MiOS conventions (Law 1/3/6, SSOT), is gated/degrade-open, and (WS-7)
  is **NOT boot-enforcing**.

No git worktrees needed: new files are conflict-free by path; shared edits are
serialized through synthesis.

## 3. Safety boundaries (non-negotiable, baked into the prompts)

- Everything ships **default-off / gated** (the operator flips on after live
  verify) — same as every workstream this session.
- **WS-7 fapolicyd ships in PERMISSIVE/observe mode only; UKI as a build step,
  not enabled.** No agent enables boot-enforcement (bricks boot).
- Builders create new files + return deltas; only synthesis edits shared files.
- Nothing is deployed/pushed/launched — operator owns the live steps.

## 4. The Workflow (runnable; operator-launched)

```js
export const meta = {
  name: 'mios-aios-buildout',
  description: 'Concurrently scaffold WS-2/4/7/8, synthesize shared-file edits, adversarially verify',
  phases: [
    { title: 'Build',      detail: 'one agent per workstream; new files + returned shared-edit deltas' },
    { title: 'Synthesize', detail: 'apply shared-file edits serially + py_compile/tomllib/bash -n' },
    { title: 'Verify',     detail: 'adversarial review per workstream (gated/degrade-open/convention)' },
  ],
}

const DELTA = { type: 'object', additionalProperties: false, properties: {
  workstream: { type: 'string' },
  new_files:  { type: 'array', items: { type: 'string' } },
  shared_edits: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
    file: { type: 'string' }, find: { type: 'string' }, insert_after: { type: 'string' }, reason: { type: 'string' },
  }, required: ['file', 'find', 'insert_after'] } },
  summary: { type: 'string' }, risks: { type: 'string' },
}, required: ['workstream', 'new_files', 'shared_edits', 'summary'] }

const RULES = `MiOS conventions: SSOT in mios.toml (no literals in code); quadlets follow Law 1/3/6 (User=/Delegate=yes, bound-images); new constants flow mios.toml -> userenv.sh -> MIOS_* -> 15-render allow-list. Sibling-module + unit-test pattern (mios_sched/mios_evict/mios_hitl/mios_aci/mios_pg). Ship DEFAULT-OFF/GATED + degrade-open. CREATE ONLY NEW FILES; for any edit to a SHARED file (mios.toml, sysusers.d/50-mios-services.conf, tools/lib/userenv.sh, automation/15-render-quadlets.sh, usr/lib/mios/agent-pipe/server.py) RETURN it in shared_edits (do NOT edit those files). Validate your new files (py_compile / bash -n). Repo root C:\\MiOS.`

const WS = [
  { label: 'WS-2 Code Mode', prompt: `Scaffold WS-2 Code Mode (concepts/aios-implementation-plan.md Appendix B). Add a coderun verb (mios.toml [verbs.coderun] -> mios-coderun CLI that runs code in the rootless coderun-sandbox) + an _exec_tool_calls branch (returned as a server.py shared_edit) + expose the verb/MCP surface as a local API inside the sandbox. New files: usr/libexec/mios/mios-coderun + any helper + a unit test. uid if needed: 828. ${RULES}` },
  { label: 'WS-4 computer-use P0', prompt: `Scaffold WS-4 computer-use P0. Doc-gen skills via LibreOffice/Pandoc (pptx/docx/xlsx/pdf) as new usr/libexec/mios/ CLI tools + mios.toml [verbs.*]/recipes, and register the existing pc_*/vision/control verbs as ONE OWUI Native tool file (openwebui/tools/). Do NOT vendor BSL Wide-Moat. New files only; SSOT + packages as shared_edits. uid if needed: 829. ${RULES}` },
  { label: 'WS-7 UKI/fapolicyd (GATED)', prompt: `Scaffold WS-7 UKI + fapolicyd. fapolicyd execution-whitelist policy + a verity-rooted UKI build step + kargs.d, with a carve-out for sandboxed agent codegen. CRITICAL: ship fapolicyd in PERMISSIVE/observe mode ONLY and the UKI as a build step that is NOT enabled (enforce-mode or a mis-signed UKI BRICKS BOOT). New files only; any pipeline wiring as shared_edits, gated off. ${RULES}` },
  { label: 'WS-8 kv_fork spike', prompt: `Scaffold WS-8 kv_fork. Add kv_fork to the llama.cpp KV layer (extends _kv_paging, server.py ~2301): copy a conversation's saved slot to a new conversation (parallel cognitive paths) via /slots save->restore-into-new-filename. Provide the pure helper + a standalone unit test (sibling-module style). server.py changes as shared_edits. ${RULES}` },
]

phase('Build')
const builds = (await parallel(WS.map(w => () =>
  agent(w.prompt, { label: w.label, phase: 'Build', schema: DELTA })))).filter(Boolean)

phase('Synthesize')
const synth = await agent(
  `Apply these shared-file edits to the MiOS repo at C:\\MiOS IN ORDER using Edit, ` +
  `resolving uid/port collisions and keeping every feature DEFAULT-OFF/gated ` +
  `(WS-7 fapolicyd must stay PERMISSIVE, never enforce). Then run: py_compile on ` +
  `server.py, tomllib on mios.toml, bash -n on any edited .sh. Report pass/fail + ` +
  `what you applied.\n` + JSON.stringify(builds.map(b => ({ ws: b.workstream, edits: b.shared_edits })), null, 2),
  { label: 'synthesize', phase: 'Synthesize' })

phase('Verify')
const VERDICT = { type: 'object', additionalProperties: false, properties: {
  workstream: { type: 'string' }, ok: { type: 'boolean' }, issues: { type: 'array', items: { type: 'string' } },
}, required: ['workstream', 'ok'] }
const verdicts = (await parallel(builds.map(b => () =>
  agent(`Adversarially review the ${b.workstream} scaffolding (new files: ${(b.new_files||[]).join(', ')}). ` +
        `Confirm it parses/compiles, follows MiOS conventions, is DEFAULT-OFF/gated + degrade-open, and ` +
        `(if WS-7) is NOT boot-enforcing. Return {workstream, ok, issues}.`,
        { label: 'verify:' + b.workstream, phase: 'Verify', schema: VERDICT })))).filter(Boolean)

return { builds, synth, verdicts }
```

## 5. Launch + after

Launch via the Workflow tool (the operator opts in). Expect ~6 agents (4 build +
1 synth + ~4 verify). After it returns: review the synth pass/fail + the
verdicts, then deploy + live-verify per `aios-implementation-plan.md`. Each
workstream stays gated until the operator flips it on. The live/hardware halves
(coderun container, doc-gen binaries, image build/boot test, GGUF bake) remain
operator steps — agents prepared the code, not the environment.

---

## Run results — wf_ae152dd9-510 (2026-06-04): 4/4 scaffolded; 2 landed, 2 need a pass

9 agents, ~917k tokens, ~19.5 min. **Independently re-validated** (not just the
workflow's self-check): `server.py` py_compile OK, `mios.toml` parses, ALL unit
suites pass — **199 checks** incl new **codemode 70/70** + **kvfork 34/34**.
Everything default-off/gated → the live system is unaffected. The synthesis stage
applied all shared-file edits cleanly (no repeat of the earlier corruption).

- **WS-2 Code Mode — LANDED.** `mios_codemode.py` + `mios-coderun-codemode` +
  `mios-codemode-api.py` + test (70/70); `[verbs.code_mode]` + `[code_mode]`
  (enable=false) + a degrade-CLOSED `_exec_tool_calls` branch. **Post-run fix:**
  added the missing `mios-coderun-codemode` shim-link.
- **WS-8 kv_fork — LANDED.** `mios_kvfork.py` + test (34/34) + `kv_fork()`
  (default-off). **Post-run fix:** dropped the dead `clamp_branches` import.
- **WS-7 UKI/fapolicyd — SCAFFOLDED, default-off/observe (SAFE), NOT enforce-
  ready.** Verifier-confirmed not boot-enforcing. Enforce-promotion blocked on:
  inverted fapolicyd carve-out rule syntax (would brick at enforce), a FALSE
  `permissive` kernel-karg safety claim (inert), a rootflags merge collision, and
  a carve-out design review — all inert under the default; operator's image-build
  + boot-test pass.
- **WS-4 computer-use — SCAFFOLDED, ok=false (needs a fix pass).** docgen CLI +
  OWUI tool + `[verbs.docgen_*]` + `[packages.docgen]`; test 17/17. **Post-run
  fix:** added the `mios-docgen` shim-link (blocker #1). Remaining: broker 45s
  capture-timeout vs LibreOffice ~60s cold start; `docgen_build` content-contract
  mismatch (OWUI `--stdin` text vs verb `--content-file` path); `owui/` vs
  `openwebui/` tools-dir divergence.

Post-run fixes re-validated (py_compile OK, codemode 70/70, kvfork 34/34). The
conflict-free design held: builders wrote only new files; the synthesizer applied
shared-file deltas serially.

### WS-4 fix pass (2026-06-04) — functional blockers resolved
- **Shim-links** added for `mios-docgen` + `mios-coderun-codemode` (else broker
  `bash -lc` → exit 127).
- **Broker timeout**: `mios-launcher-daemon` CAPTURE/CAPTURE_JSON `timeout=45`
  → configurable `MIOS_LAUNCHER_CAPTURE_TIMEOUT_S` (default **120**), covering
  LibreOffice cold-start (~60s). A hung verb is still bounded.
- **Content contract unified**: `mios-docgen` gained `--content TEXT`; the
  `[verbs.docgen_build]` cmd is now `--content {content}` (the dispatch
  `shlex.quote`s it, and the broker closes stdin, so inline text is the correct
  transport for the verb path). `--content-file`/`--stdin` retained for the OWUI
  tool + large content. Both surfaces now mean "content = text."
- Validated: py_compile OK, docgen test 17/17, TOML OK. Still default-off
  (`docgen_enable=false`). DEFERRED (non-blocking): `owui/` vs `openwebui/`
  tools-dir consolidation; `cu_*` subcommand verification against
  `mios-computer-use`. OPERATOR-GATED: LibreOffice/Pandoc in the image + the OWUI
  tool deploy; WS-4 P1/P2 still ahead.
