<!-- AI-hint: The authoritative VM-completion checklist for the remaining MIOS-MASTER-PLAN WS tasks after the 2026-06-21 offline build-out. Each remaining task is reduced to ONE operator action in the `just build`->boot loop, with its verified code state (built/wired/tested) and the HARD external constraint (GPU model / live k3s pods / inference-engine preemption support / systemd Environment limit / boot-verification of a flag flip) that prevents verifiable offline completion. Companion to aios-engineering-blueprint.md + ws-a3-central-path-cutover-worklist.md.
     AI-related: ../doc/mios/concepts/aios-engineering-blueprint.md, ../doc/mios/concepts/ws-a3-central-path-cutover-worklist.md, ../mios.toml -->
# Remaining WS tasks — VM completion checklist (post 2026-06-21 offline build-out)

Every task below has its pure core **built + unit-tested** and (where safe) wired
into `server.py` **flag-gated, default-off, degrade-open** — so the live path is
byte-identical until you enable it. What remains is one operator action in the
`just build` → boot loop: either a **flag flip + boot-verify**, or work gated on
**hardware/engine/platform** the build host doesn't have. None can be
*verifiably* completed offline without fabricating verification or risking the
live chat path; this is the honest hand-off.

## Flip-a-flag + boot-verify (code built, wired, tested — inert until enabled)
| Task | Action | Wired in |
|---|---|---|
| #26 WS-6 quota | `[users.<name>].rpm_limit` / `daily_budget` → boot → expect `429 quota_block` | `_dispatch_quota_reason` (mios_quota) |
| #27 WS-5 RLS | `[pgvector].rls_mode="enforce"` → boot → recall owner-scoped | `_rls_owner`+`recall(owner=)` |
| #25 WS-A10 | `[agent_passport].principal_mode="enforce"` (+ optional `MIOS_CRL_PATH` file) → boot | `_a2a_verify_principal`+`mios_crl` |
| #20 WS-A16 | `[ai].remote_escalation="on"` + a remote `[nodes.*]` → boot → local-first failover | `_lane_resolver` |
| #30 WS-A18 | `[gossip].interval_min>0` on ≥2 nodes → confirm peer discovery via `/v1/peers` | `_gossip_loop` (mios_gossip) |
| #15 WS-A11 | Stage-2: route `chat_completions`→`KERNEL.handle()` per `ws-decompose-stage2-plan` → boot-verify each mode | mios_kernel/router/dispatcher (Stage 1 done) |

## Hardware / engine / platform-gated (hard constraints, not choices)
| Task | Constraint | Already in place |
|---|---|---|
| #16 WS-A12 | **mid-generation** snapshot/restore needs inference-engine support llama.cpp lacks (`/slots` is request-boundary only) | `_PREEMPT` bookkeeping + request-boundary RR + `RR_ENABLE` |
| #12 WS-8 | a **GPU vision model** must be loaded (absent on the build host) | `mios-computer-use*` verbs exist |
| #28 WS-7 | k3s manifests adapt to **live pods** (hostNet/GPU/PV) | `mios-webtools.pod` + `generate-k3s-manifests.sh` |
| #31 WS-10 (tail) | k3s regen reads **live running pods** (`podman kube generate`) | build-time regen-diff gates done: drift-checks 8 (verbs) / 9 (packages) / 12 (capabilities) |
| #5 WS-0B (tail) | systemd **cannot `${}`-expand `Environment=`** in `.service` units | lane-drift collapsed (WS-1); SSOT comments de-rotted; option: move ports to `EnvironmentFile=install.env` refs |

## Already substantially done (verified this pass; deliberately-deferred halves noted)
- #11 WS-2 — unified RBAC capability manifest: projection (`mios_capreg`) + committed `ai/v1/capabilities.generated.json` + drift-check 12 + live `GET /v1/capabilities`. The "refusal detection" is sub-agent **punt-detection in synthesis** (already present), not a user-facing safety refusal (which would violate MiOS's never-refuse ethos).
- #22 WS-A13 — `mios-sandbox-exec` (bwrap) confines code-exec via `mios-coderun`; `mios_sandbox.resolve_profile`/`build_bwrap_argv` provide the tier decision/argv. GUI/launch verbs are intentionally NOT sandboxed (bwrap would break `/mnt/c` + display).
- #32 WS-11 — `mios_interop` 3-projection + passport-gated A2A + the self-improve **observe/surface** loop (`_selfimprove_loop`, spawned, `interval_min=0` off) are wired; the self-modifying **act** half is guardrail-gated by design.

> Built/wired this build-out (~25 commits, 2026-06-21): the AIOS engineering
> blueprint; `mios_bench`/`mios_gossip`/`mios_capreg` cores + the `mios-bench` /
> `mios-ai-capabilities-gen` CLIs + the committed capability manifest; quota /
> CRL / RLS / remote-escalation / gossip / capreg wirings; drift-checks 11 + 12;
> the SurrealQL→pg CLI cutover + de-rot. Full agent-pipe suite 50/50; drift 1–12
> green (offline). Verify the above in the VM, then these tasks close.
