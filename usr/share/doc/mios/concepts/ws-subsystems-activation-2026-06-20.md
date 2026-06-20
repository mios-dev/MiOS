<!-- AI-hint: Operator activation playbook for the default-off WS-* subsystems shipped 2026-06-20 (RLS, A2A signed principal, peer reputation, egress firewall, mTLS PKI, GOAP lane, self-improve loop) -- what each does, its mios.toml SSOT flag, how to enable + verify. -->

# Activating the WS-* subsystems (shipped 2026-06-20)

The 2026-06-20 session completed the WS-* architectural backlog. **Everything
shipped DEFAULT-OFF / inert** — the single-node behaviour is unchanged until you
opt in. This is the playbook for turning each on. All flags live in `mios.toml`
(layered: `~/.config/mios` < `/etc/mios` < `/usr/share/mios`); run `mios-sync-env`
after edits where a service reads the derived `install.env`.

Each subsystem has a standalone unit test (`test_mios_*.py`, run by the drift
gate) and is degrade-open (a failure never breaks a turn).

## Data plane

### Owner-scoped memory recall (RLS) — `#59`
- **Does:** tags `knowledge` rows with the requesting principal (`owner_user`);
  under enforce, recall returns only the caller's rows plus shared/legacy (NULL)
  rows. `agent_memory` recall fail-closes under enforce.
- **Enable:** `[pgvector].rls_mode = "enforce"` (default `"off"` = tag-only).
- **Verify:** multi-user chat; a second user must not recall the first's answers.
- **Follow-on:** owner-tagging `agent_memory`/`scratch` writes (mios-remember) so
  they can be owner-scoped instead of fail-closed.

## Federation (zero-trust A2A) — `#54`, `#60`

Inert until peers are registered in `a2a-peers.json`. The four primitives:

### Signed delegation principal (`#60`)
- **Does:** signs the principal on outbound A2A delegations (text-bound Ed25519,
  on `message.metadata.mios_principal`); verifies inbound.
- **Enable:** provision an agent-passport key (`[agent_passport].signing_key_path`).
  To *require* valid inbound principals: `[agent_passport].principal_mode = "require"`
  (default `"off"` = attribution/audit only).

### Peer reputation
- **Does:** ranks ready peers by delegation reliability (auto, no flag). Inspect
  at `GET /v1/a2a/peers` → `reputation`.

### Outbound egress firewall
- **Does:** OS-level nftables, scoped to the agent uid — constrains the agent's
  external egress (other users untouched, so `web_search` still works).
- **Enable:** `[security.egress].mode = "audit"` then `"enforce"`; widen
  `[security.egress].allow` (CIDRs) as needed. Then:
  `tools/generate-egress-firewall.py && sudo nft -f usr/share/mios/security/egress.nft`.
- **Verify:** `journalctl -k | grep mios-egress` in audit before enforcing.

### mTLS transport
- **Does:** mints a self-signed local CA + agent cert (clientAuth+serverAuth).
- **Enable:** `tools/provision-agent-mtls.py` → `/etc/mios/mtls/`; exchange
  `ca.crt` with peers; require client certs at the reverse proxy fronting `/a2a`
  (see `usr/share/mios/security/README.md`). Override `[security.mtls].*_file`
  for an org PKI.

## Orchestration + ops

### Deterministic GOAP planner lane — `#53`
- **Does:** plans known multi-step tasks (e.g. launch→type→verify) by search, not
  LLM — reproducible.
- **Enable:** `[goap].mode = "available"` (default `"off"`); extend
  `[[goap.actions]]` (the action model) per verb. Auto-routing GOAP-vs-LLM-DAG is
  a follow-on; `_goap_plan(goal)` is the entry point.

### Self-improvement loop — `#64`
- **Does:** surfaces failing/slow tools + unreliable peers from local outcome
  data. On demand: `GET /v1/self-improve/report`. Proactively: a periodic task
  logs new findings (the daemon-agent + you see them).
- **Enable proactive surfacing:** `[selfimprove].interval_min = N` (default `0`
  = off). Thresholds: `[selfimprove].{fail_threshold,slow_ms,min_samples}`.
- **Note:** it only SURFACES. Autonomous remediation (self-modification) is a
  deliberate non-goal here — it needs a guardrails design first.

## Build/CI gates (always-on, no flag) — `#63`, `#58`

- **AI-hint coverage** (`mios-ai-hint-coverage`, 38-drift-checks check 5): fails
  the build if untagged taggable files exceed `[ai_tag].max_untagged` (ratchet;
  lower it toward 0 with `mios-ai-tag`).
- **Module boundary** (check 6): the agent-pipe `mios_*.py` siblings must never
  `import server` (the modular-monolith one-way boundary).
- **k3s manifests** (`#61`): regenerate from the live pods with
  `tools/generate-k3s-manifests.sh` → `usr/share/mios/k3s/generated/`. Adapt
  host-net/GPU/bind-mounts before deploying (see that dir's README).

## Still operator-gated (not autonomously completable)

- **`#49`** compound-launch decomposition — logic shipped + regression-tested
  (`test_mios_launch.py`); needs a **live launch-test** in OWUI to confirm
  end-to-end (the agent is barred from launching apps).
- **`#50`** desktop-app reasoning rendering — the agent-pipe emits standard
  `reasoning_content` deltas (verified); the **Hermes desktop app's frontend**
  must render them (its source is outside this repo).
