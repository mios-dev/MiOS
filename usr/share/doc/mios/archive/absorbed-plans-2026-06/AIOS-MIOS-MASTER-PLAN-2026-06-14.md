<!-- Master plan: full AIOS+MiOS capabilities + fix-all-outages. Consolidates this session's install/outage work, the AIOS-kernel-features research (K1-K6), and the AIOS-GAP plan (G1-G11, see AIOS-GAP-IMPLEMENTATION-PLAN-2026-06-14.md). 2026-06-14. -->

# MiOS → Full AIOS: Master Plan (2026-06-14)

Goal: achieve full AIOS + MiOS capabilities and fix all outages. This unifies three workstreams: **(A) outages/fresh-install bring-up** (operational, mostly done this session), **(B) AIOS-kernel features K1–K6** (new research), and **(C) the AIOS-GAP roadmap G1–G11** (companion doc). Sequenced so dependencies build in order; cross-references avoid duplication.

---

## Part A — Fix all outages (operational)

### A.1 — Fixed this session (verified)
- **Install** via canonical `irm|iex` → DEV-ready (worked around the `Get-MiOS.ps1` BOM parse bug).
- **Inference**: `mios-llm-light` `:11450` serving granite-4.1-8b / lfm2-700m / embeddinggemma (baked 5.8 GB) + embeddings.
- **Hermes** `:8642`: was hitting the openrouter cloud default → fixed (installed local-provider config into `$HERMES_HOME/config.yaml`). `@`/`mios` chat works + grounded.
- **agent-pipe** `:8640` + **delegation-prefilter** up (DAG path).
- **RAG**: backfilled embeddings for all 64 knowledge rows (`mios-ingest` never embedded) + lowered recall thresholds → agent grounds in MiOS docs.
- **SGLang heavy lane** `:11441` (`mios-heavy`, Qwen3-8B-AWQ on the 4090): provisioned + 2 Quadlet bugs fixed (tool-parser placeholder, context 131072→40960); auto-starts when GPU frees.
- **Launcher broker** `mios-launcher.service` started → `/run/mios-launcher/launcher.sock` present + interop env (so `launch_*` dispatches; visible-launch still gated by WSLg Session-0).
- **MCP / A2A / Passport / pgvector / OWUI / SearXNG / Forge** up.

### A.2 — Remaining outages (triage)
- **Real, fix next:** `code-server` (`:8800` shows down — verify port/bind), `ttyd-bash`/`ttyd-ps` (`:7681/7682`, disabled), `mios-daemon` (down), `Dash-AI` (`:9119`), `webtools` crawl4ai/firecrawl (stuck activating — unbuilt images).
- **Launch visibility** — Windows-app launch lands in WSLg Session-0 (no window); robust fix = broker uses operator's live interactive-session interop, or KasmVNC desktop.
- **SGLang VRAM volatility** — shared 4090; health_gate fallback to CPU when contended (working as designed).
- **By-design down (not outages):** Ceph, K3s, ha-node (bare-metal/cluster), Guacamole/Skills-Miner/CrowdSec (opt-in), the legacy datastore (retired→pgvector), wsl-init/wslg-permissions (masked).

### A.3 — SOURCE fixes so a clean install self-assembles (operator push)
Root cause of nearly every gap above: the dev-VM overlay skipped `automation/36-tools.sh` (mios-tools) → `userenv.sh` resolver missing → `/etc/mios/install.env` never rendered → services on bare defaults. Fixes:
1. Run `36-tools.sh` in the overlay (or `mios build` runs full automation).
2. Complete `generate_env` to emit the agentic/auth/RAG vars + fix its `set -e` early-abort.
3. Make `mios-ingest` embed-on-write; bridge `MIOS_LLAMACPP_BAKE_MODELS`.
4. Fix firstboot↔hermes-agent ordering deadlock; enable `mios-launcher.service` in firstboot.
5. Fix the Quadlet renderer for `${VAR:-default}`; set SGLang context=40960; pin Hermes to a served model.
6. Push the `Get-MiOS.ps1` BOM fix; teach the AI-tagging generator to not strand BOMs / trip `<!-- -->` injection guards (also breaks Hermes `SOUL.md`).

---

## Part B — AIOS-kernel features (K1–K6, this research)

| K | Feature | Current MiOS state | Effort |
|---|---|---|---|
| **K1** | LLMAdapter chokepoint — format-instruction prompt for **non-native-tool** models + primary-path rescue + UUID call-ids + `{type:any}` grammar | ~80% built (encode/decode/rescue exist; proactive format-prompt + primary rescue absent) | **M** |
| **K2** | Domain agent profiles (Math/Rec/Travel/Academic/Creation) via `[agents.*]` SSOT + per-domain workflow prompts + 2 verbs (academic source-flag, offline image-gen params) | role-based not domain-based; absent | **L** |
| **K3** | 3-phase router (@-direct + **Agent Recommender** + autonomous swarm) + formal **Planner/Coder/Reviewer/Test** SE loop + **Claw Bridge** (NemoClaw/DeerFlow/GitAgent importers) | refine/council/swarm + opencode exist; explicit recommender/SE-loop/bridge absent | **L** |
| **K4** | Weighted **Consensus-Judge** pipeline (4 profiles) + BFT/Raft + **JSD drift** (Θ=0.877) + Goodhart | DCI yes/no exists; scored weighted consensus + drift absent — **builds on G3** | **XL** |
| **K5** | Execution safety: **Verify/Monitor** modes + **Analyst(read-only)→Action(write)** phase escalation | HITL gate + permission SSOT + tool-scope exist — **builds on G2** | **M** |
| **K6** | Directory-prompt-state (`tasks/backlog|in-progress|done.md`) + **LSFS** semantic-FS verbs (mount/create/write/search/rollback/share) | docs-index + pgvector + scratch exist; tasks-protocol + LSFS verbs absent | **M–L** |

Full per-area file-level steps: workflow output `tasks/wr4p5w2ty.output` (K1–K5). K6 + cross-synthesis were cut by the session limit — folded into the sequencing below.

**Key merges (don't double-build):** K1 ≡ G8 (tool-call shaping — one `_llm_adapter_shape()` implementation). K4 requires G3 (reliability gate is the Goodhart ground-truth). K5 extends G2 (HITL/firewall). K3's coder/reviewer/test reuse opencode + critic + coderun.

---

## Part C — AIOS-GAP roadmap (G1–G11)
Detailed in `AIOS-GAP-IMPLEMENTATION-PLAN-2026-06-14.md`. Summary: G1 grounding VLM, G2 out-of-process policy + eBPF/Tetragon + HITL-gate, G3 replay reliability gate, G4 per-action isolation ladder, G5 closed self-improvement, G6 agent-self-edit memory, G7 Code Mode, G8 universal tool_choice (≡K1), G9 persistent PTY, G10 A2A topology/discovery, G11 integrity chain.

---

## Sequenced build plan (waves)

**Wave 0 — finish outages + source fixes (A.2 + A.3).** Bring up code-server/ttyd/daemon; rebuild webtools images; then push the A.3 source fixes so the next clean install needs zero manual recovery.

**Wave 1 — quick wins, plumbing exists:**
1. **G8≡K1** unify tool-call shaping (`mios_llmadapter.py` chokepoint: format-instruction prompt + primary rescue + UUID ids + `{type:any}`). Fixes "narrate instead of act" + weak-lane tool use.
2. **G2-step1** flip HITL `log`→`gate` for dangerous verbs (config).
3. **K5** Verify/Monitor + Analyst→Action scope gate (`mios_execmode.py`, on the HITL/permission SSOT).
4. **G6** agent-self-edit memory verbs (pgvector tiers).
5. **G3** replay reliability gate (`mios_reliability.py`) — the foundation for K4 + G5.

**Wave 2 — feature depth:**
6. **K2** domain agent profiles + the 2 capability verbs.
7. **K3** 3-phase router + Agent Recommender + Planner/Coder/Reviewer/Test loop.
8. **G1** grounding VLM (bake Holo1.5, wire perception→act→verify).
9. **K6** `tasks/*.md` execution-state protocol + LSFS verbs (over FS + pgvector).

**Wave 3 — heavy / dependent:**
10. **K4** weighted consensus judges + BFT/Raft + JSD drift + Goodhart (on G3).
11. **G5** closed self-improvement (on G3, immutable substrate).
12. **G4** isolation tier ladder; **G2-rest** eBPF/Tetragon enforcement; **G11** integrity chain; **K3 Claw Bridge** external-format importers.

---

## Cross-cutting (every item)
- **Architectural Laws:** Law5 (everything → `MIOS_AI_ENDPOINT`, no vendor URLs — esp. K1/K2/K3 model calls); unprivileged Quadlets (K4 judge panel, G2 Tetragon = documented exception); **mios.toml SSOT** (new sections: `[llmadapter]`, `[agents.*]` domain fields, `[router]`, `[judge]`/`[reliability]`, `[execmode]`, `[lsfs]`); immutability/rollback; BOUND-IMAGES.
- **New pgvector tables:** `reliability_case`/`reliability_run` (G3), `judge_verdict`/`drift_baseline` (K4), `improvement_proposal` (G5), `persona_block` (G6), `tasks` (K6).
- **Configurator:** mirror every new `mios.toml` section in `mios.html`.

## Quick wins to start (highest unlock/effort)
G8≡K1 (act-not-narrate), G2-step1 (one config flip), K5 (safety on existing HITL), G6 (mechanical verbs) — then G3 as the foundation that unblocks K4 + G5.
