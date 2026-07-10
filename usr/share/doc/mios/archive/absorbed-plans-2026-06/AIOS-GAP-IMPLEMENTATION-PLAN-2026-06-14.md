<!-- Generated 2026-06-14 by a repo-grounded multi-agent research pass over AIOS-GAP-ANALYSIS-2026-06-14.md + its kernel-space addendum. 11 gap plans + synthesis. Companion to the two analysis docs. -->
# MiOS → True AIOS: Consolidated Build Roadmap (2026-06-14)

## 1. Orientation

MiOS is a **structurally complete but capability-shallow AIOS**: per `C:\MiOS\AIOS-GAP-ANALYSIS-2026-06-14.md` it already ships an analogue of every AIOS kernel service — priority scheduler (`mios_sched.py`), KV/context paging (llama.cpp `/slots`), tiered pgvector memory, MCP+A2A interop, unprivileged-Quadlet isolation, offline fine-tuning. What the 11 plans add is not new kernel services but **depth, enforcement, and frontier capability** on top of substrate that is, in nearly every case, 70–80% built and inert. The recurring shape across all 11 gaps is identical: the plumbing exists, but one load-bearing link is missing — the vision GGUF is never baked (G1), the HITL gate ships in `log` not `gate` mode (G2), `run_template` is captured but never scored (G3), the WS-7 build lib is dead code never wired into `build.sh` (G11), the Code Mode host socket is never served (G7). This roadmap therefore optimizes for **capability-unlock-per-edit**: most "critical" items are a handful of `mios.toml` keys, a config flip, and one or two new tools — not greenfield subsystems.

---

## 2. Dependency Graph

```
                          ┌─────────────────────────────────────────────┐
   WAVE 1 (Tier 1)        │                                             │
                          ▼                                             │
   G2-step1 ─── flip HITL to gate ────────────┐                        │
   (mios.toml only, S)                          │                        │
                                                │                        │
   G3 ── reliability gate (pass@k/TH50) ───────┼──► unblocks ──► G5 ────┘
   builds mios-eval-run + replay scorer         │   (self-improve
        │                                        │    CONSUMES the gate)
        └── shared scorer mios-eval-run ─────────┘
                                                 │
   G1 ── grounding VLM (bake Holo1.5) ──────────┤ (independent; rides
        (perception→action→verify loop)         │  existing cu_* + verify)
                                                 │
   ─────────────────────────────────────────────┼───────────────────────
   WAVE 2 (Tier 2)                               │
                                                 ▼
   G2-rest ── out-of-process arbiter + ──────► underpins ──► G4
              eBPF/LSM (Tetragon)                              (isolation
        │  shares taint plane + dangerous-verb set            ladder:
        ▼                                                      promote-not-
   G4 ── per-action isolation ladder ◄── shares sandbox ──► G7  refuse on taint)
        (bwrap→container→gVisor→microVM)        substrate
                                                 │
   G5 ── closed self-improvement loop ◄── REQUIRES G3 (held-out gate)
                                                 │
   G6 ── agent-self-edit memory verbs (independent; pgvector only)
   ─────────────────────────────────────────────┼───────────────────────
   WAVE 3 (Tier 3)                               │
                                                 ▼
   G7 ── Code Mode host broker ◄── shares sandbox + session-keying with G4/G9
   G8 ── universal tool_choice (independent; in-process agent-pipe change)
   G9 ── persistent PTY/shell ◄── shares sandbox-exec + ACI + session-keying
   G10 ── A2A topology/discovery (independent; A2A council gated on G2 taint)
   G11 ── integrity chain (UKI/MOK/fapolicyd) (independent; bare-metal target)
```

**Hard edges (build-order-binding):**
- **G3 → G5.** `mios-self-improve` (G5) cannot promote a change without the held-out verdict. `mios-eval-run` is built *once* in G3 and consumed by G5. Build G3 first.
- **G2 → G4.** The isolation ladder's "promote-not-refuse" decision must be consistent with the firewall policy engine G2 makes authoritative; both read the same `_HIGH_PRIVILEGE_VERBS` / dangerous-verb set.

**Soft edges (de-risk but not blocking):** G2/G4 share the taint plane; G4/G7/G9 share the sandbox substrate and `_orch_ctx_var` session-keying; G10 council fan-out should wait for G2's taint firewall before federating untrusted peers; G6 recall is gated on the pg-primary cutover already done per memory.

---

## 3. Sequenced Build Plan — 3 Waves

### WAVE 1 — Tier 1 (critical/high, plumbing exists)

Order within wave: **G2-step1 (hours) → G3 → G1.** G2-step1 is a config flip shipped same-day; G3 builds the shared scorer that G5 needs in Wave 2; G1 is the headline capability but is the longest single item.

---

#### G2-step1 — Flip HITL to `gate` for the dangerous-verb scope `[S — ship this week]`
- **Current state (1 line):** `[hitl] mode="log"` in `C:\MiOS\usr\share\mios\mios.toml:1350-1353` — the fully-built gate (`mios_hitl.py` + `server.py:11507-11646`, wired into dispatch at `server.py:14540`) never blocks.
- **First PRs/files:** `C:\MiOS\usr\share\mios\mios.toml` only — set `mode="gate"`, `verbs="powershell_run,winget_install,winget_upgrade,winget_uninstall,flatpak_install,flatpak_upgrade,flatpak_uninstall,service_restart,container_restart,pc_type,pc_key,pc_click"`, and flip `[security].provenance_taint=true` (line 497) to close the lethal trifecta. No Python change — `server.py` already reads `HITL_MODE`/`HITL_SCOPE`.
- **New components:** none (config only).
- **Tech choice:** reuse the shipped `mios_hitl.py` + `/v1/hitl/approve` passport-signed gate.
- **Effort:** S.
- **Verification:** dispatch `powershell_run` via the pipe → returns `hitl_pending`, a `pending_action` row appears at `GET /v1/hitl/pending`; `POST /v1/hitl/approve` lets the retry pass.

---

#### G3 — Replay-based reliability gate (pass@k / pass^k / TH50 / AUC) `[L]`
- **Current state (1 line):** `run_template` is captured observe-only (`schema-init.sql:174-185`, `server.py:_capture_run_template:12619`) and `execute_skill` (`server.py:9892`) is already a 1:1 DAG replayer — but nothing scores replays or gates promotion.
- **First PRs/files:**
  1. `C:\MiOS\usr\share\mios\postgres\schema-init.sql` — add `reliability_case` (frozen held-out suite) + `reliability_run` (scored verdicts) tables.
  2. `C:\MiOS\usr\lib\mios\agent-pipe\mios_reliability.py` — pure scorer (sibling-module pattern alongside `mios_hitl.py`) + `test_mios_reliability.py`.
  3. `C:\MiOS\usr\libexec\mios\mios-reliability` — `curate`/`gate`/`list` CLI (stdlib + `mios-db --pg`, mirrors `mios-skills`).
  4. `C:\MiOS\usr\lib\mios\agent-pipe\server.py` — `POST /v1/reliability/replay` + `GET /v1/reliability/runs`, replaying through the existing `execute_skill` / `_execute_dag_bounded` dispatch path (zero new attack surface).
  5. Gate-wiring: `C:\MiOS\usr\libexec\mios\mios-skills` (replace the single-window success-rate check at `:408-418`) and `C:\MiOS\usr\libexec\mios\mios-finetune` (A/B before adoption).
- **New components:** `[reliability]` mios.toml section + configurator card; the two tables; the CLI; the scorer module + 2 endpoints; `mios-reliability.{service,timer}` (copy `mios-skills-miner`); tmpfiles for `/var/lib/mios/reliability`.
- **Tech choice:** pass@k + pass^k + Task-Horizon@50% + reliability-AUC (arXiv:2603.29231) over `node_count` horizon buckets; held-out frozen suite + flip-centered regression gate (DGM, arXiv:2505.22954). Reuse the existing replay engine — **no new executor.**
- **Effort:** L.
- **Verification:** unit-test the pass@k vs pass^k math + side-effect refusal; inject a deliberately-broken skill body → promotion BLOCKED (`verdict='block'`); stop agent-pipe → `mios-skills` degrades-open to the old gate (never errors). `dry_run=true` first (observe before enforce).
- **Critical safety:** `replay_dangerous=false` default — side-effecting DAGs are never replayed live (honors the no-live-launch posture).

---

#### G1 — Grounding VLM on the perception path `[L]`
- **Current state (1 line):** the entire perception→action→verify chain is built and INERT because the vision GGUF is absent from `[llamacpp].bake_models` (`mios.toml:3656`); `mios-pc-vision`, `mios-computer-use._ground`, the `qwen3-vl:4b` slot in `mios-llm-light.yaml:124-147`, and `mios-verify-launch` all exist.
- **First PRs/files:**
  1. `C:\MiOS\usr\share\mios\mios.toml` — append Holo1.5-7B GGUF + mmproj to `[llamacpp].bake_models` (dest names must match `mios-llm-light.yaml:141-142`); set `[ai].vision_grounding_model="qwen3-vl:4b"`, `chat_vision_model`, `chat_vision_endpoint="http://localhost:11450/v1"`, plus `vision_grounding_enable=false` gate and `[computer_use].verify_after_act`.
  2. `C:\MiOS\usr\lib\mios\agent-pipe\server.py:19378-19380` — fix the 3 mis-wired chat-vision lines (default `VISION_MODEL`/`VISION_ENDPOINT` point at retired ollama `:11434`).
  3. `C:\MiOS\usr\libexec\mios\mios-cu-verify` — new visual Definition-of-Done tool (screen analogue of `mios-verify-launch`).
  4. `C:\MiOS\usr\libexec\mios\mios-computer-use` — add `cu_act` (ground→click→verify) subcommand + register `[verbs.cu_verify]`/`[verbs.cu_act]`.
- **New components:** `mios-cu-verify`; `cu_verify`/`cu_act` verbs (three-projection MCP/OpenAI/A2A); new `[ai]`/`[computer_use]` keys; configurator fields; Holo1.5 bake entry (no new image — bakes into existing bound `mios-llm-light` seed).
- **Tech choice:** H Company **Holo1.5-7B** GGUF (mradermacher Q4_K_M ~4.7GB + mmproj-Q8_0 ~1GB) — ScreenSpot-Pro 57.94 vs 29.0 for Qwen2.5-VL-7B; qwen2vl base arch is mature on mainline llama.cpp (avoids the qwen35 fork trap). AT-SPI-first grounding stays the deterministic fast path; VLM only on canvas/Electron misses.
- **Effort:** L.
- **Verification:** `curl :11450/v1/chat/completions model=qwen3-vl:4b` with a base64 screenshot returns coordinate JSON; `mios-pc-vision /tmp/screen.png "the OK button"` returns `{x,y,confidence>0.5}`; `mios-cu-verify "<criterion>"` returns `{ok:false}` honestly (no fabrication) when the lane is down.
- **Dependency note:** operator must bake the GGUF (classifier blocks assistant HF fetch); exact mradermacher filenames need bake-time re-verification.

---

### WAVE 2 — Tier 2 (high-value, more design)

Order within wave: **G2-rest → G4** (G4's promote decision depends on G2's authoritative policy engine); **G5** lands once G3 is proven; **G6** is independent and can run in parallel.

---

#### G2-rest — Out-of-process policy arbiter + eBPF/LSM enforcement (Tetragon) `[L]`
- **Current state (1 line):** the semantic firewall is a Python branch *inside* agent-pipe (`server.py:10881-11066`, `_dispatch_mios_verb_inner:14501`) — a compromised orchestrator can reason around its own allowlist; no kernel enforcement plane exists.
- **First PRs/files:**
  1. `C:\MiOS\usr\libexec\mios\mios-policy-arbiter` + `.service` — loopback-unix-socket FastAPI service running as `mios-enforcer` (UID 829, **a different user than the agent**), re-deriving the taint/scope decision from the same `mios.toml` SSOT + pgvector — authoritative and unevadable.
  2. `C:\MiOS\usr\lib\mios\agent-pipe\mios_policy_client.py` + `server.py` — call the arbiter before the in-process firewall (defense-in-depth); degrade-CLOSED for dangerous scope.
  3. `C:\MiOS\usr\share\containers\systemd\mios-enforcer.container` — Tetragon (documented Law-6 privileged exception, added to `99-postcheck.sh` allowlist alongside mios-ceph/k3s/forgejo-runner).
  4. `C:\MiOS\usr\libexec\mios\mios-enforcer-render` + firstboot — compiles `mios.toml [security.policy]` → Tetragon TracingPolicy YAML; `mios-enforcer-shipper` writes `enforcer_kill`/`enforcer_deny` rows back to the `event`/`tool_call` tables.
- **New components:** `[security.enforcer]` + `[security.policy]` SSOT sections; `mios-enforcer` sysuser (UID 829); the arbiter/render/shipper/firstboot units; seed TracingPolicies (`policies.d/*.yaml.tmpl`: exfil-block tcp_connect, exec-guard execve/LSM, cgroup-scoped to mios-ai + mios-codemode only).
- **Tech choice:** **Cilium Tetragon v1.4** (Apache-2.0, in-kernel SIGKILL/connect-deny, <1% overhead) — the only FOSS option with enforcement; runs standalone (file-based TracingPolicies, no K8s). The arbiter is the intent layer (eBPF can't see intent); Tetragon verifies side-effects.
- **Effort:** L.
- **Verification:** kill `mios-policy-arbiter` → dangerous verb refused (degrade-CLOSED) while read verb runs; in observe mode a tainted process's disallowed `execve`/outbound connect emits a Tetragon Post event + shipper row; flip to enforce → process SIGKILLed.
- **Caveat:** WSL2 dev VM lacks the BPF/LSM surface — unit stays `ConditionVirtualization`-gated OFF; arbiter + HITL gate still work everywhere. Enforcement is a bare-metal capability.

---

#### G4 — Per-action isolation tier ladder `[L]`
- **Current state (1 line):** tiers 1-2 (bwrap `mios-sandbox-exec`, rootless podman `mios-coderun-sandbox@.container`) are built; gVisor/microVM absent; the taint plane only REFUSES, never promotes to a stronger tier.
- **First PRs/files:**
  1. `C:\MiOS\usr\share\mios\mios.toml` — `[isolation]` table (ladder, taint→tier map, `taint_min_tier`, `default_code_tier`, `health_gate`); `[packages.isolation_tiers]`.
  2. `C:\MiOS\usr\lib\mios\agent-pipe\mios_isolation.py` + tests — pure tier-selection/promotion (sibling-module).
  3. `C:\MiOS\usr\lib\mios\agent-pipe\server.py:14516` — replace binary REFUSE-on-taint with `resolve_effective_tier()` → run in promoted tier, emit `firewall_promote` (degrade-CLOSED to `firewall_block` if floor tier unavailable).
  4. `C:\MiOS\usr\share\containers\containers.conf.d\20-mios-isolation-runtimes.conf` — register `runsc` + `krun`.
  5. `C:\MiOS\usr\libexec\mios\mios-coderun-tier` — tier-aware exec launcher.
- **New components:** the `[isolation]` table; `mios_isolation.py`; two USER-scope Quadlet templates (gVisor `--runtime=runsc`, microVM `--runtime=krun` + `ConditionPathExists=/dev/kvm`); `mios-coderun-tier`; `automation/38-isolation-tiers.sh` (gated build hook).
- **Tech choice:** **gVisor runsc** (tier 3) + **libkrun via crun's `krun` mode** (tier 4) — crun is already in `[packages.containers]`; both register as plain OCI runtimes reusing the hardened sandbox verbatim. ConditionPathExists=/dev/kvm makes tier 4 self-inert on WSL2.
- **Effort:** L.
- **Verification:** taint a session (external `open_url`) → dispatch a high-priv verb → `event` row shows `firewall_promote {from_tier,to_tier}` and the verb ran inside the promoted tier; with `enable=false` behavior is byte-identical to today. microVM Quadlet inert on WSL2 (no /dev/kvm).

---

#### G5 — Closed self-improvement loop (DGM-style) `[L]` — **requires G3**
- **Current state (1 line):** every piece exists EXCEPT the orchestrating loop — propose (`mios-skill-clone`/`mios-tool-clone`/`mios-skills mine`/`mios-finetune`), held-out suite (`C:\MiOS\var\lib\mios\evals\dataset.jsonl`), atomic rollback (`build-mios.yml`→`mios-bootc-switch.path`→`bootc switch`) are all built and disconnected.
- **First PRs/files:**
  1. `C:\MiOS\usr\libexec\mios\mios-eval-run` — SSOT-aware reusable scorer wrapping `mios-knowledge.local-runner.py` (the **shared G3/G5 scorer**; runner confirmed endpoint-driven and Law-5-compliant).
  2. `C:\MiOS\usr\libexec\mios\mios-self-improve` — the missing orchestrator: `baseline` | `cycle` (propose → validate-on-held-out → decide → record → promote-on-win).
  3. `C:\MiOS\usr\share\mios\postgres\schema-init.sql` — `improvement_proposal` table (the DGM evolutionary archive: proposal + measured delta + `parent_id` lineage + `applied`/`image_ref`).
  4. `[self_improve]` mios.toml section (`enable=false`, `auto_apply_image=false` by default) + configurator card + userenv slots; `mios-self-improve.{service,timer}` (copy `mios-skills-miner`).
- **New components:** the archive table; `mios-eval-run`; `mios-self-improve`; the routing/behavioral held-out sub-suite (`routing.eval.json` + `routing.dataset.jsonl`); `GET /v1/self_improve/proposals`.
- **Tech choice:** DGM propose/validate/archive (arXiv:2505.22954) realized safely on MiOS's immutable substrate — promote only on a measured win, image-level promotions ride the existing Forge→bootc-switch loop (zero new privilege), reverted by `bootc rollback`.
- **Effort:** L.
- **Verification:** `mios-self-improve baseline` records a baseline row; seed a better + a worse prompt variant → better gets `won=true` + promoted, worse archived `won=false` + NOT applied; `enable=false` → timer fires and no-ops.

---

#### G6 — Agent-self-editing memory verbs (Letta/MemGPT tiers) `[M]`
- **Current state (1 line):** four self-edit verbs (`remember`/`recall`/`memory_update`/`memory_forget`) + the `knowledge` table's `tier`/`pinned` columns already ship (`schema-init.sql:20-46`), but `agent_memory` has no tier/pin and tier promotion is system-only (`server.py:9028-9040`) — the agent can't curate its own context.
- **First PRs/files:**
  1. `C:\MiOS\usr\share\mios\postgres\schema-init.sql` — idempotent ALTERs adding `tier`/`pinned`/`pin_reason` to `agent_memory` + a new `persona_block` table (Letta block model).
  2. `C:\MiOS\usr\libexec\mios\mios-remember` — add `promote`/`demote`/`pin`/`unpin`/`persona-get`/`persona-set`/`archive` subcommands.
  3. `C:\MiOS\usr\share\mios\mios.toml` — register `[verbs.memory_promote]` etc. (pure cmd-template, **zero new dispatch code** — auto-projects to MCP/OpenAI/A2A).
  4. `C:\MiOS\usr\lib\mios\agent-pipe\server.py:8870` — wire core-tier always-include + persona-block read into prompt assembly (tool-sourced, never `pre_llm_call` auto-prepend — honors the no-context-injection rule).
- **New components:** 9 new SSOT verbs; `persona_block` table; `agent_memory` columns; `[knowledge]` tunables (`core_inject_max`, `persona_block_enable`, etc.).
- **Tech choice:** Letta/MemGPT block model (editable labeled blocks + core/recall/archival semantics) as API shape only — no Letta runtime dependency; reuse pgvector + nomic-embed + the cmd-template SSOT.
- **Effort:** M.
- **Verification:** `mios-remember add` then `promote --tier core` → `tier` flips, `pinned=true`; `persona-set`/`persona-get` round-trips honoring `char_limit`; `mios-mcp-server tools/list` auto-includes the new verbs.

---

### WAVE 3 — Tier 3 (finish what's started)

All four are independent; order by quick-win value: **G8 → G7 → G9 → G10 → G11.**

---

#### G8 — Universal `tool_choice` enforcement on the llama.cpp lane `[M]`
- **Current state (1 line):** `tool_choice="required"` is downgraded to `"auto"` on every llama.cpp lane (`server.py:22627-22637`, `:22998-23007`) because of a legacy iGPU b9305 quirk — so the agent narrates instead of acting; the rescue parser exists for secondaries only.
- **First PRs/files:** `C:\MiOS\usr\lib\mios\agent-pipe\server.py` — add `_shape_tool_choice()` (single chokepoint near `:2384`) translating `required` → `{"type":"any"}` (or `{"type":"tool","name":...}` for named); replace the two inline downgrade blocks; wire the existing `_rescue_tool_calls` (`:3630`) + retry into the PRIMARY path (`_finalize:22290`, `_stream_backend_inner:22405`). `mios.toml [dispatch]` — `tool_choice_mode`, `tool_choice_force_retry`, `auto_force_tool`.
- **New components:** `_shape_tool_choice` helper; 3 `[dispatch]` keys + configurator inputs; `mios-toolchoice-probe`. **No new container** (in-process change).
- **Tech choice:** llama.cpp native `{"type":"any"}` grammar-forced shape (confirmed absent today via grep) — the offline FOSS equivalent of `tool_choice=required`; pair with the existing `lane_tool_cap` to dodge the GBNF-many-optional-params 500 (Issue #20867) with degrade-open auto-retry.
- **Effort:** M.
- **Verification:** unit `_shape_tool_choice('required', llamacpp_ep)=={'type':'any'}` and `('auto')` for the legacy `:11436` hint; live probe returns structured `tool_calls[]` not narrated content; E2E action prompt fires the verb with no `💤` on the llama.cpp node.

---

#### G7 — Wire Code Mode through the sandbox `[M]`
- **Current state (1 line):** ~70% built but the host-side socket broker is absent — every `mios_tools` call inside the jail raises `tool socket unavailable` (`mios-codemode-api.py` shim exists, `mios-coderun-sandbox@.container` already bind-mounts the socket, but nothing serves the host side and the image is never baked).
- **First PRs/files:** `C:\MiOS\usr\libexec\mios\mios-codemode-broker` (unix-socket→`/v1/dispatch` relay, reusing all existing gates like `mios-mcp-server` does); `mios-codemode-broker@.{service,socket}` (socket-activation pre-creates the file before podman bind-mounts it — fixes the missing-source-becomes-a-directory trap); `C:\MiOS\etc\mios\containers\coderun-sandbox\Dockerfile` (COPY shim→`mios_tools.py` on PYTHONPATH + set `MIOS_CODEMODE_SOCKET`); `automation/54-bake-coderun-sandbox.sh` (build + bake the image); extend the bound-images binder in `08-system-files-overlay.sh:176` to walk the `users/` subdir (closes the Law-3 hole).
- **New components:** the broker + templated units; the bake script; `[code_mode]` additions (`allowed_verbs`, `socket_dir`, `broker_idle_ttl_s`); bound-images binder extension + matching `99-postcheck` Law-3 validator update.
- **Tech choice:** Code-execution-as-tool-orchestration (Anthropic/Cloudflare Code Mode, 85-98% token reduction); unix-domain-socket RPC (the only sanctioned egress from a `Network=none` jail); `podman build` at image-build time + bound-images symlink (vs runtime build = immutability violation).
- **Effort:** M.
- **Verification:** offline unit binds a temp AF_UNIX socket + asserts a round-trip dispatch envelope + non-allowlisted-verb rejection; operator-run on DEV: `import mios_tools; mios_tools.system_status()` inside the jail returns `ok=true, sandboxed=true`.

---

#### G9 — Persistent PTY / stateful shell substrate `[M]`
- **Current state (1 line):** every shell/code call is isolated — cwd/env/history discarded between turns; tmux + ttyd + `mios-sandbox-exec` + `mios_aci.py` + session-keying all exist but no long-lived shell process the agent can write to across calls.
- **First PRs/files:** `C:\MiOS\usr\lib\mios\agent-pipe\mios_pty.py` + tests (pure session-id + tmux-argv + marker-sentinel/nonce protocol, sibling-module); `C:\MiOS\usr\libexec\mios\mios-shell-session` (tmux-backed bash per chat, confined in the existing bwrap jail at `--level baseline`); `mios-shell-session-gc.{service,timer}` (idle reaper); register `[verbs.shell_session]` (model_name `run_in_shell`) + `[shell_session]` config block.
- **New components:** `mios_pty.py`; `mios-shell-session`; the GC reaper units; the verb + config block; tmpfiles for `/var/lib/mios/shell-sessions`. **No new container** (reuses bwrap; reuses UID 828).
- **Tech choice:** **tmux** (already packaged) as the multiplexer per OpenHands' production TmuxBashSession pattern; marker-sentinel + **per-command nonce** for completion/exit-code/cwd capture (hardened against output spoofing); output bounded by the existing `mios_aci.normalize_output` (the gap's literal "build on the ACI normalizer" clause).
- **Effort:** M.
- **Verification:** `exec --session t1 'cd /tmp && export FOO=bar'` then `exec --session t1 'echo $PWD $FOO'` returns `/tmp bar` — proving cwd+env persistence across calls; a 5MB log returns ACI-elided (head+tail+marker).

---

#### G10 — A2A federation topology + agent-card discovery `[M]`
- **Current state (1 line):** publish + consume + registry + discovery tools are largely built (`server.py:16895-17310`), but the SSOT→env bridge is broken (0 a2a matches in `userenv.sh`), peers are probed once at startup, and there's no topology endpoint/configurator/JWS signing.
- **First PRs/files:** `C:\MiOS\tools\lib\userenv.sh` — add the 9 `MIOS_A2A_*` slots + reconcile the `nodes`/`discover_cidr` vs `DISCOVER_URLS`/`DISCOVER_PORT` name mismatch; `C:\MiOS\usr\lib\mios\agent-pipe\server.py` — refactor `_a2a_client_startup` into a periodic `_a2a_refresh_peers()` background loop + add `GET /v1/cluster/topology`; `mios.html` — `[a2a]` federation card; harden `mios-a2a-discover` (add `/v1/agent-card`, dedup by card id).
- **New components:** `/v1/cluster/topology`; the refresh loop; configurator card; new `[a2a]` tunables; AgentCard `securitySchemes` + optional ed25519 JWS signature; `test_mios_a2a.py`.
- **Tech choice:** A2A v1.0/0.3 AgentCard at `/.well-known/agent-card.json` (already MiOS's shape); ed25519 JWS (offline, no CA, per-host firstboot key); **LAN/WSL-gateway discovery as primary, tailnet sweep default-OFF** (per the standing rule that Tailscale congests the operator's internet).
- **Effort:** M.
- **Verification:** `mios-sync-env && grep MIOS_A2A_ /etc/mios/install.env` shows populated keys; kill a peer → it flips offline and drops from `/v1/cluster/topology` WITHOUT restarting the node (proves dynamic re-probe).

---

#### G11 — Close the integrity chain (composefs-digest UKI + MOK-sign + fapolicyd observe→enforce) `[L]`
- **Current state (1 line):** WS-7 is scaffolded but DEAD — the build lib `automation/lib/ws7-uki-fapolicyd-build.sh` lives under `lib/` so `build.sh`'s `[0-9][0-9]-*.sh` glob never runs it; the UKI embeds no composefs digest, is unsigned, and verity.require is a deliberate no-op karg.
- **First PRs/files:** `C:\MiOS\automation\48-ws7-integrity.sh` — numbered NON-FATAL step that invokes the dead build lib (the single biggest fix); `ws7-uki-fapolicyd-build.sh` — embed `composefs=<digest>` on the UKI cmdline + sbsign with MOK; `automation/47-mok-enroll.sh` + firstboot oneshot; `mios-fapolicyd-report` (would-deny collector) + `etc/greenboot/check/wanted.d/50-mios-integrity.sh` (auto-rollback a bad enforce flip); commit `etc/pki/mios/mok.der` (public cert only).
- **New components:** the 47/48 steps; the report + greenboot + `mios-integrity-status` tooling; firstboot MOK enrollment; new `[uki]`/`[security]` knobs (`enroll_mok`, `sign_uki`, `fapolicyd_enforce`) + configurator fields; tmpfiles for `/var/lib/mios/ws7`.
- **Tech choice:** bootc composefs backend + `bootc container compute-composefs-digest` + `composefs=<sha512>` UKI cmdline (2026 upstream sealed-bootc); systemd-ukify + sbsign (both already packaged); greenboot (already wired) as the brick safety net.
- **Effort:** L.
- **Verification:** with flags default-off, `just build` runs 48 as a logged no-op + lint passes; with signing on, `sbverify --cert mok.der mios-verity.efi.signed` succeeds; enforce flip is bare-metal-only (WSL2 can build/sign but not validate verity.require boot).

---

## 4. Cross-Cutting Concerns (Architectural Law compliance)

Every plan was authored to satisfy the six laws; the consolidated obligations:

| Law | How all 11 items comply |
|---|---|
| **Law 5 (UNIFIED-AI-REDIRECTS)** | G1 vision endpoints target `mios-llm-light :11450`, not retired ollama `:11434` or vendor URLs; G3/G5 eval runner + grader default to `MIOS_AI_ENDPOINT`; G8 forced-call traffic and probe target configured node endpoints; the enforcer/arbiter (G2) and integrity tooling (G11) make no model calls at all. |
| **Law 6 (UNPRIVILEGED-QUADLETS)** | Most items add **no container** (G3/G5/G8/G9/G10 reuse host-libexec oneshots as `mios-ai`/`mios-codemode`; G6/G7 ride existing unprivileged quadlets). The **one documented exception is G2's `mios-enforcer.container`** (Tetragon needs CAP_BPF/CAP_SYS_ADMIN — added to the `99-postcheck.sh` Law-6 allowlist alongside mios-ceph/k3s/forgejo-runner, with header rationale: the platform plane must be unevadable by the agent user). G4's sandbox quadlets stay under `users/` (validators glob non-recursively) with `User=root + UserNS=keep-id` exactly like the existing coderun-sandbox. |
| **mios.toml SSOT** | Every new constant is a `mios.toml` key → `userenv.sh` slot → `MIOS_*` env → consumer, with a configurator field. No hardcoded literals — G4 reuses the existing high-privilege verb set rather than re-listing; G2/G11 render YAML/kargs FROM TOML; G6/G8 generate verb surfaces from `[verbs.*]`. |
| **Immutability / rollback** | Every brick-capable or behavior-changing flip is default-OFF + reversible by a single TOML key or `bootc rollback`. G5 exploits this as its core safety property (a bad self-applied change rolls back atomically); G11's whole design leans on greenboot auto-rollback; G2/G4 gate on `.ready`/`.enable` sentinels so a bad policy no-ops rather than bricks boot. |
| **BOUND-IMAGES (Law 3)** | G1 bakes GGUFs into the existing bound `mios-llm-light` seed (no new image). G7 **closes an existing Law-3 hole**: the bound-images binder is extended to walk the `users/` quadlet subdir + the coderun-sandbox image is baked at build time. G2 binds the Tetragon image via the auto-symlink. No other new images. |

**New `mios.toml` sections required (consolidated):** `[reliability]` (G3), `[security.enforcer]` + `[security.policy]` (G2), `[isolation]` + `[packages.isolation_tiers]` (G4), `[self_improve]` (G5), `persona_block`-driving `[knowledge]` additions (G6), `[code_mode]` additions (G7), `[dispatch]` additions (G8), `[shell_session]` (G9), `[a2a]` additions (G10), `[uki]`/`[security]` integrity additions (G11). **New configurator cards** mirror each. **New schema tables:** `reliability_case`, `reliability_run` (G3), `improvement_proposal` (G5), `persona_block` (G6).

---

## 5. Explicit Non-Goals (de-scoped kernel-space addendum items)

| De-scoped item | One-line rejection reason |
|---|---|
| **In-kernel LLM token scheduler** | MiOS already has a superior userspace priority scheduler (`mios_sched.py` — priority + anti-starvation + admission + circuit breaker, *ahead of* the AIOS FIFO/RR reference); a kernel rewrite trades a working asset for fragility with no capability gain. |
| **`sys_llm_query` syscall ABI** | Breaks Law 5 — the unified value is the OpenAI-compatible HTTP/`/v1` contract every agent/tool resolves from `MIOS_AI_ENDPOINT`; a syscall ABI would fork the surface and de-portabilize the agent stack. |
| **Kernel-managed KV-cache page tables** | llama.cpp `/slots` KV checkpoint/restore already does per-conversation context paging in userspace; a kernel page-table layer is enormous effort for a problem already solved at the engine boundary. |
| **In-kernel `/dev/llm` inference device** | Inference belongs in the llama.cpp/SGLang/vLLM lanes; putting a model in kernel space is a security and maintainability anti-pattern with zero offline/FOSS precedent. |

**Optional-low:** a `/dev/llm` *ergonomic shim* (a userspace character-device or FIFO that forwards to `MIOS_AI_ENDPOINT`) is acceptable as a thin convenience wrapper IF it stays Law-5-compliant (forwards to the HTTP `/v1` surface, holds no model) — low priority, no capability unlock, build only on explicit operator request.

---

## 6. Quick Wins vs Heavy Lifts — start this week

**Highest capability-unlock-per-effort (do first):**

1. **G2-step1 — flip HITL to `gate` (`S`, config only).** One `mios.toml` edit closes the lethal trifecta and turns policy from observe into enforcement. Highest safety-per-edit in the whole roadmap. `C:\MiOS\usr\share\mios\mios.toml:1350-1353` + line 497.
2. **G1 — bake the Holo1.5 GGUF + fix 3 agent-pipe lines (`L`, but the bake line is `S`).** The single `[llamacpp].bake_models` line at `mios.toml:3656` activates the *entire* dormant perception plane — the biggest single capability gap (computer-use ~zero → live) for the least new code, since `mios-pc-vision`/`mios-computer-use`/the verify daemon all already exist.
3. **G8 — universal `tool_choice` (`M`, in-process, no container).** Fixes the "narrate instead of act" correctness bug across all llama.cpp lanes; the rescue parser already exists, this is unification not greenfield.
4. **G6 — agent-self-edit memory verbs (`M`, no container/image/privilege).** ~7 mechanical SSOT verb blocks + ~120 lines in `mios-remember`; auto-projects to MCP/OpenAI/A2A with zero new dispatch code.

**Build-the-foundation (do next, unblocks Wave 2):**

5. **G3 — reliability gate (`L`).** Build `mios-eval-run` once; it is the shared scorer that gates skill promotion now *and* unblocks G5 self-improvement. The single most important precondition for safe autonomy.

**Heavy lifts (sequence after, design + bare-metal validation):**

- **G2-rest (Tetragon)** and **G4 (gVisor/microVM ladder)** — `L` each; need a privileged-exception review, observe→enforce soak, and bare-metal validation (WSL2 can't exercise eBPF or /dev/kvm).
- **G5 (closed self-improvement)** — `L`; gated on G3, plus reward-hacking + routing-sub-suite hardening.
- **G11 (integrity chain)** — `L`; brick-capable, so promotion stays operator-gated and final enforce proof requires the operator on Secure-Boot bare metal.

The cheapest three edits (G2-step1, G1's bake line, G8) move MiOS from "blind, observe-only, narrating" to "sees the screen, blocks dangerous actions, takes them" — the largest qualitative jump toward a true AIOS available this week.