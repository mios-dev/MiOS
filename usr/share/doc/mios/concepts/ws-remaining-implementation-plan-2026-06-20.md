<!-- AI-hint: Decision-ready implementation plan for the 6 remaining MiOS WS-* architectural subsystems (GOAP planner, zero-trust federation, server.py strangler-fig, RLS, pods→k3s, self-improve loop) — for each: the design decision needed, the recommended safe default, prerequisites, blast-radius, the safe first increment, and the verification plan.
     AI-related: usr/lib/mios/agent-pipe/server.py, usr/share/mios/mios.toml, usr/share/doc/mios/concepts/ -->

# Remaining WS-* architectural subsystems — implementation plan (2026-06-20)

The bounded/live work is done (#36–#52, #55–#57, #65, #66, the "MiOS AI" rename, the
OWUI location chain, identity-leak grounding, code_interpreter, #49 type-chain, #50
CLI reasoning-stream, #51 plan, **#62 HITL gate-mode**, **#60 per-user authz**). These
6 remain — each is multi-session and its first move is a design decision or a
prerequisite. For each: **Decision** (what's yours to choose), **Default** (the safe
choice I'd take), **Prereq**, **Risk**, **First increment** (safe, default-inert),
**Verify**. Approve any and I implement it the way I did #62/#60.

## #59 — WS-5: owner_user + RLS + durability  ← HIGHEST LEVERAGE (unblocks #60-signing, #62-arbiter)
- **Decision:** add an `owner_user` column to the pgvector memory/scratch tables (+ backfill to the single operator user)? RLS enforce-by-owner now, or tag-only first?
- **Default:** tag-only first — add `owner_user`, write it on every row, do NOT filter yet (zero behaviour change); enable Postgres RLS in a second, reviewed step.
- **Prereq:** a pgvector schema migration (ALTER TABLE) via an idempotent ExecStartPost (the pattern already used for the scratch/mios_rag columns).
- **Risk:** data-plane — a bad migration breaks memory writes. Mitigate: additive nullable column, `IF NOT EXISTS`, degrade-open writes.
- **First increment:** migration + write-side tagging, behind `[ai].rls_mode=off|tag|enforce` (default tag).
- **Verify:** write a memory row, confirm `owner_user` populated; recall still works; RLS off → no filtering.

## #60 (remaining half) — signed principal
- **Decision:** how is a user/agent principal AUTHENTICATED? OWUI's JWT, a MiOS ed25519 principal token (reusing the agent-passport key), or trust-the-surface?
- **Default:** sign MiOS AI's OWN outputs with the agent-passport ed25519 key (verifiable provenance) + accept the OWUI-forwarded identity as trusted-surface for authz (already shipped in #60's per-user layer). Full cross-trust principal verification waits on the auth choice.
- **Prereq:** the agent-passport signing key provisioned (`[agent_passport].signing_key_path`).
- **Risk:** low (additive signing); verification-enforcement is the risky part (gated).
- **Verify:** response carries a verifiable signature; tampering fails verification.

## #62 (remaining half) — out-of-process policy arbiter
- **Decision:** in-process gate (shipped) enough, or a separate arbiter process the pipe consults per action?
- **Default:** keep the in-process gate as the enforcement point; add an OPTIONAL arbiter HTTP hook (`[ai].hitl_arbiter_url`) the gate POSTs to for an allow/deny verdict, default unset → use the in-process decision.
- **Risk:** low (default-unset → no external dependency); a down arbiter must degrade-open or fail-closed per `[ai].hitl_arbiter_fail` (default open).
- **Verify:** with a stub arbiter returning deny, a high-risk verb is blocked; arbiter down + fail=open → proceeds.

## #54 — Zero-trust agent federation (mTLS + ed25519 + reputation + egress firewall)
- **Decision:** the cert/PKI model (self-signed per-node CA? Tailscale identity? operator CA?) and whether outbound egress is allowlisted.
- **Default:** reuse the agent-passport ed25519 keys for peer identity (no new PKI); peer-reputation as a passive counter; egress allowlist = the configured A2A peers + local SearXNG, default permissive.
- **Prereq:** real A2A peers configured (`a2a-peers.json` is vendor-empty → most of this is dead weight on a single node).
- **Risk:** egress allowlist can block legitimate traffic if wrong → default permissive + log-only first.
- **Verify:** a non-allowlisted egress is logged (audit) then (later) blocked; passport-verified peer accepted.

## #53 — Optional deterministic GOAP planner lane
- **Decision:** declare per-verb preconditions/effects in the SSOT (`[verbs.*]`) to plan over? Which goals route to GOAP vs the LLM DAG?
- **Default:** a NEW optional lane, default-off (`[ai].planner=llm|goap`, default llm); GOAP used only when explicitly selected.
- **Prereq:** preconditions/effects on the ~71 verbs (a large SSOT pass) — without them the planner is a toy.
- **Risk:** low if default-off + additive; high effort on the SSOT annotations.
- **Verify:** a goal with declared pre/effects yields a correct deterministic plan; default llm path unchanged.

## #58 — WS-3: server.py strangler-fig (modularize the monolith)
- **Decision:** which concern carves out FIRST (candidates: grounding helpers, the A2A surface, the OS-control path, the RBAC/HITL gates)? Import-constraint lint rules?
- **Default:** start with the LEAF, low-coupling, already-cohesive blocks I've been adding (grounding `_identity/_arch/_client_*`, the RBAC/HITL gates) → extract to `mios_policy.py` / `mios_grounding.py` with an import-constraint lint; delete any remaining `patch*.py` (already done).
- **Risk:** HIGH blast radius — it's the live 26k-line orchestrator. Must be done attended, one module at a time, each behind a green smoke + the drift gate.
- **Verify:** after each extraction, `py_compile` + full smoke (chat/web/os-control/memory) + `just drift-gate` green; byte-identical behaviour.

## #61 — WS-7: pods → generated-k3s (pods-as-SSOT)
- **Decision:** k3s as the runtime, or keep podman-quadlets + GENERATE k3s manifests from the pod SSOT for portability?
- **Default:** pods-as-SSOT → generate k3s manifests as an artifact (no runtime switch); keep quadlets as the live runtime until a deliberate cutover.
- **Risk:** runtime migration is high-risk; manifest-generation is safe (an artifact).
- **Verify:** generated manifests validate (`kubectl --dry-run`); quadlet runtime unchanged.

## #64 — WS-11: federation + self-improve loop (closure)
- **Decision:** what is the self-improve signal (eval scores? operator feedback? satisfaction events?) and the gated action (fine-tune? prompt-tune? config-tune?)?
- **Default:** closure task — depends on #54 (federation) + the eval/feedback substrate; sequence LAST.
- **Risk:** a self-modifying loop is the highest-risk; must be HITL-gated (uses #62) + reversible.
- **Verify:** N/A until the dependencies land.

---
**Recommended order:** #59 (unblocks the multi-user chain) → #60-signing → #62-arbiter → #54 → #53 → #58 (attended) → #61 → #64. Each ships default-inert + verified, the #62/#60 way.
