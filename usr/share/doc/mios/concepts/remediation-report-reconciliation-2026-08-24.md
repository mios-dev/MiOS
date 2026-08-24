<!-- AI-hint: Reconciles an external "MiOS remediation roadmap" report against the shipped tree: its subjects are name collisions, its four phases already ship here; the audit found two real gaps -- the unwired computer-use approval gate and chain-verify coverage blindness. -->

# External remediation report -- reconciliation & findings (2026-08-24)

An externally generated research report ("Architectural Analysis and
Remediation Roadmap for MiOS (MyOS) Enterprise AI Substrates") was submitted
for action against this tree. Per Law 15 (DOUBLE-REPO-TRIPLE-CHECK) it was
reconciled against the shipped code before anything was adopted. The verdict,
in one line: **the report analyzes other systems that share the MiOS name, and
every remediation it proposes already exists here in a more specific form** --
but auditing its four themes against the code surfaced **two real gaps**,
recorded below with an ordered plan.

## Identity: none of the report's subjects is this repository

The report's own disambiguation table lists five "MiOS" systems. None is this
tree (the immutable bootc/OCI Fedora workstation + local agentic AI plane):

| Report subject | Verdict | Evidence in-tree |
|---|---|---|
| "Bespoke Mentis MIOS" -- a governed enterprise AIOS with "8 cognitive + 5 execution layers" | Not this system | No such layer stack exists anywhere in the tree; the architecture here is SSOT -> projections -> gates (`ROADMAP.md` thesis, `[laws]` in `usr/share/mios/mios.toml`) |
| Holo1.5 / "Surfer-H" vision-agent substrate | Name collision | `automation/67-bake-surfer.sh` builds **zen-browser's `surfer`** -- a Firefox-based browser build tool producing the MiOS Webshell. It is unrelated to any "Surfer-H" agent. Grounding here is AT-SPI-first with an SSOT-selected vision fallback (`[computer_use].grounding_model`) |
| Vera / openLuup home automation (Luup engine, Lua) | Not this system | No Luup, no Lua runtime, no HTTP-device plugin surface |
| Zebra Aurora / Xilinx Kria "MIOS" images (FPGA MIO pins) | Not this system | No machine-vision firmware, no PMU/FPGA surface |
| Miyoo CFW / educational higher-half kernels | Not this system | This is a Fedora bootc image, not a hand-rolled kernel |

The report also arrived with lost glyphs where its benchmark numbers should be
(object-replacement characters), so its quantitative claims were unverifiable
on their face. Its four *themates* -- grounding-vs-dispatch safety, execution
isolation, visual context growth, audit latency -- are legitimate computer-use
engineering concerns, so each was audited against the code rather than
dismissed. That audit is the rest of this document.

## Phase-by-phase reconciliation

### Report Phase 1 -- "bind spatial predictions to accessibility nodes; fail closed" -> SHIPPED (and stronger)

The report proposes resolving VLM (x,y) predictions to accessibility-tree
nodes *after* vision. MiOS orders it the stronger way around: **structural
first, vision fallback** (`usr/libexec/mios/mios-pc-vision` is AT-SPI-first;
see `usr/share/doc/mios/concepts/computer-use-federation.md`). On top of that,
the WS-8 loop in `usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py` already
implements the report's exact intervention and more:

* `_execute_click_hierarchy` -- scales model coordinates, hit-tests them
  against the live element list, and prefers a **structural**
  `click_element`-by-name dispatch; the raw coordinate click is only the
  fallback.
* `resolve_verb` refuses unknown action/platform pairs (fail-closed `None`,
  never a guessed verb).
* Every act is followed by a fresh screenshot + SHA-256 observation digest;
  no-change acts count toward a stall guard, and three failed click retries
  raise a hard `HITL escalation` abort.
* Post-action verification is SSOT-gated and consumed:
  `[computer_use].verify_after_act` is read by
  `usr/libexec/mios/mios-computer-use`.
* Unit coverage exists: `usr/lib/mios/agent-pipe/test_mios_cua.py`,
  `usr/lib/mios/agent-pipe/test_mios_cua_hierarchy.py`.

**Adopted from the report: nothing new.** The residual gap found while
verifying this phase is the approval-gate wiring -- see Finding 1.

### Report Phase 2 -- "microVM sandboxes via Podman Quadlets" -> SHIPPED where policy allows it

MiOS already ships a layered execution boundary for model-generated code:

* `usr/libexec/mios/mios-sandbox-exec` -- per-call bubblewrap jail,
  `level=enforce` by default, **refuses to run unsandboxed** when bwrap or the
  T-230 seccomp filter (`usr/libexec/mios/mios-seccomp-filter`) is unavailable.
* `usr/share/containers/systemd/users/mios-coderun-sandbox@.container` --
  per-session rootless Quadlet with Landlock PID-1, `Network=none`,
  `ReadOnly=true`, `DropCapability=ALL`, seccomp, snapshot/revert via
  `usr/libexec/mios/mios-coderun-session`
  (`usr/share/doc/mios/concepts/coderun-sandbox.md`).
* WS-A13 per-dispatch confinement tiers
  (`usr/lib/mios/agent-pipe/mios_pipe/access/sandbox.py`): read -> none,
  write -> workspace, interactive -> strict; the resolved posture is attached
  to every dispatch result.
* The report's literal microVM idea is already tracked as T-032 "Hermetic MCP
  Sandboxing (microVM per tool)" in `TASKS.md`, vendor-gated off at
  `[security.mcp_sandbox].enable`.

What the report gets **wrong** for this tree: it proposes isolating the *agent
runtime* in VMs. That contradicts the recorded operator directive (quoted in
`coderun-sandbox.md`): MiOS agents install to the host root by design; the
sandbox boundary is for **code**, not for the agents. Rejected as policy, not
as a gap.

### Report Phase 3 -- "compress visual context; fine-tune the VLM" -> NOT APPLICABLE structurally

The premise (dense vision tokens accumulating over long workflows) does not
match the shipped loop: each `cua.py` iteration sends **one** freshly captured,
pre-scaled screenshot (`usr/libexec/mios/mios-smart-resize`) to the VLM and
keeps only a text trace (`CuaTrace`: action/verb/ok/changed). Images never
accumulate in session history. Text-side growth is already budgeted elsewhere:
`[memory]` compaction (`compaction_interval`, `tool_result_ttl_turns`,
`compaction_threshold_pct`), `[aci]` head-tail truncation with an
anti-fabrication marker, and `usr/lib/mios/agent-pipe/mios_pipe/context/compact.py`
with its sibling `ctxpack.py`. Fine-tuning a grounding model is out of scope
for this repo -- the grounding model is an SSOT *selection*
(`[computer_use].grounding_model`), not something this tree trains. Rejected.

### Report Phase 4 -- "non-blocking SHA-256 evidence streaming" -> SHIPPED, with one real gap

The report proposes building an asynchronous SHA-256 audit chain. It exists:
SEC-03 in `usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py` is a
tamper-evident hash chain over the `event` and `session` streams --
`sha256(prev_hash || canonical_core)` links, an in-memory chain head seeded
once at startup (deliberately **no per-insert SELECT**, which is the report's
latency concern solved by design), stamping at the persist chokepoint, and a
`/v1/audit/chain/verify` walk. Unit coverage:
`usr/lib/mios/agent-pipe/test_mios_audit.py`.

One deliberate design difference must not be "remediated": the report demands
fail-closed evidence ("100% completeness"); MiOS chains **degrade-open** --
a stamp failure logs the event unchained rather than blocking the plane,
consistent with the degrade-open posture Law 12 applies at firstboot. The
right fix for the honesty cost of that choice is Finding 2.

## Finding 1 -- the computer-use approval gate is promised on five surfaces and wired on none

`[computer_use].require_approval = true` ships in the vendor SSOT and is
described as gating write-class desktop ops (click/type/key) by:

1. the key's own SSOT comment (`usr/share/mios/mios.toml`),
2. the model-facing verb description -- `[verbs.cu_click].desc` says
   "Write-class, approval-gated",
3. the configurator UI toggle (`usr/share/mios/configurator/mios.html`,
   field `computer_use.require_approval`),
4. `usr/share/doc/mios/concepts/computer-use-federation.md` (Security section),
5. the node-server prose in `usr/libexec/mios/mios-computer-use-server`.

**No code reads the key.** A tree-wide search (python, shell, and the
extensionless `usr/libexec/mios/` executors) finds no consumer; the only
non-prose matches are OpenAI Responses-API MCP manifest fields that happen to
share the name. What actually gates verb dispatch is the WS-6 HITL gate
(`usr/lib/mios/agent-pipe/mios_pipe/access/hitl.py` and its `hitlflow.py`
sibling), and there the Linux desktop write verbs fall through twice:

* **Scope:** the gate applies to `_HIGH_PRIVILEGE_VERBS` = the curated set in
  `usr/lib/mios/agent-pipe/server.py` UNION
  `[security].firewall_high_privilege_verbs`. Both lists contain the
  Windows-host twins (`pc_click`, `pc_type`, `pc_key`) but **neither contains
  `cu_click`, `cu_type`, `cu_key`, or `cu_key_combo`** -- the verbs whose own
  descriptions say "approval-gated".
* **Mode:** vendor `[hitl].mode = "log"` observes without blocking, so even
  in-scope verbs never wait for approval unless an overlay sets `gate`.

The `HITL escalation` raise in `cua.py` is a hard abort after failed retries,
not an approval round-trip -- the pending-approval store and
`POST /v1/hitl/approve` flow in `hitlflow.py` exist and are the natural hook.

Exposure today is bounded by vendor defaults -- `[dispatch].cua_enable` is
off (the loop needs a GPU VLM) and the node server binds loopback -- but an
operator who flips the lane on via the configurator reasonably believes a
blocking gate exists, because the UI says so. This is the same defect class
as commit `014cb70` ("the memory guard was off while the SSOT said log"): an
SSOT security key that nothing reads, with the fallback as the operative
value.

## Finding 2 -- chain verification cannot see unchained rows

`/v1/audit/chain/verify` reads `WHERE chain_hash IS NOT NULL` and walks only
the chained subset. Degrade-open stamping means rows written before the seed
completes (or after a stamp failure) are legitimately unchained -- and
invisible to the verifier, so `ok: true` can mask partial coverage. The
degrade-open choice is right; the blindness is not: the verify response should
also report total-vs-chained row counts so coverage loss is observable.

## Plan (ordered by leverage; write-path changes are operator-live-test per the binding rule in `oscontrol-envgrounding-gaps-2026-06-20.md`)

1. **Wire or retire `[computer_use].require_approval`** -- decide once,
   Law 9 style (one canonical gate, not two keys claiming the same gate):
   * (a) minimal, `014cb70`-shaped: add the four `cu_*` write verbs to
     `[security].firewall_high_privilege_verbs` so they enter the existing
     HITL scope (today's `log` mode then observes them -- no behaviour break;
     `gate` mode blocks-until-approved), **and**
   * (b) give the key real semantics -- when true, treat the desktop
     write-verb set as `gate`-mode regardless of the global `[hitl].mode`
     (read at the same dispatch chokepoint) -- **or** retire the key and
     re-point all five promise surfaces at `[hitl]`.
   * Done-When: a negative test proves a `cu_click` dispatch blocks (or is
     honestly documented as log-only on every surface), in the pattern of
     `test_mios_cua.py`.
2. **Surface chain coverage** -- extend `chain_verify_logic` to include total
   and unchained row counts per table. Done-When: a unit in
   `test_mios_audit.py` shows an unchained row changing the reported coverage
   while `ok` stays truthful.
3. **Reconcile the promise surfaces** -- whichever way item 1 lands, update
   the five surfaces listed in Finding 1 so SSOT, verb catalog, configurator,
   concept doc, and server prose agree. Done-When: a grep for
   `require_approval` finds only surfaces that describe the shipped
   behaviour.
4. **Deploy-time posture flips (no code)** -- the report's "remediation
   roadmap" reduces, for this tree, to enabling what is already built when
   each deployment can carry it: `[security.mcp_sandbox].enable`,
   `[security.egress].mode`, `[dispatch].cua_enable` (needs the GPU VLM),
   `[hitl].mode = "gate"` where a human is present, and replacing the
   `[security.sigstore]` accept-everything policy with real
   `allowed_identities` once signing identities are provisioned.

## Not adopted from the report, and why

* The five-execution/eight-cognitive layer stack -- describes a different
  product; nothing to map.
* Swapping grounding to a specific external VLM family -- the grounding model
  is an SSOT selection with a shipped default and a documented heavy-lane
  upgrade path; adopting a vendor family is an operator model choice, not an
  architecture change (and the report's largest variant is
  non-commercially licensed).
* Agent-runtime microVMs -- contradicts the recorded agents-on-host operator
  directive; the sandbox boundary is for code.
* A GRPO fine-tuning pipeline -- out of scope for an OS tree that bakes and
  selects weights (Law 12) rather than training them.
* "100% audit chain completeness" as a hard guarantee -- contradicts the
  deliberate degrade-open design; adopted instead as Finding 2's coverage
  *metric*.
* The 12-month phase plan -- the work it schedules is either already shipped
  (above) or enumerated as the four ordered items here.
