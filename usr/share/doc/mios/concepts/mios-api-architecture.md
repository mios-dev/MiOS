# MiOS-API architecture

## Decision

MiOS-API is one API plane with two bounded concerns:

1. **AI API:** the existing OpenAI-compatible `/v1` contract served by
   `mios-agent-pipe.service`.
2. **System API:** a capability-scoped management surface, also under `/v1`,
   brokered by agent-pipe and executed only through a local `miosd` executor.

MiOS-API does not introduce a second HTTP gateway, a second authentication
store, or a generic remote-shell endpoint. `MIOS_AI_ENDPOINT` remains the
single public AI endpoint. System operations are additive resources on the same
gateway and never bypass its authentication, policy, approval, audit, or trace
path.

## Current assets

| Concern | Existing owner | Reuse in MiOS-API |
|---|---|---|
| OpenAI `/v1` ingress, streaming, models, embeddings, agent discovery | `usr/lib/mios/agent-pipe/server.py` | Public HTTP ingress and response envelopes |
| Bearer-to-principal resolution | `mios_pipe/access/authn.py` | Caller identity and scoped principal metadata |
| Capability and policy decision point | `mios_pdp`, `mios_capreg` imports in `server.py` | Authorize every system operation before dispatch |
| Human approval gate | `mios_pipe/access/hitl.py`, `mios_hitlflow` | Block destructive operations until an approval is recorded |
| Agent audit, trace, and pgvector state | `mios_audit`, `mios_trace`, pgvector integration | Correlate caller, policy decision, approval, job, and result |
| Native system supervisor | `src/mios-rs/miosd`, `miosd.service` | Local privileged executor and durable job state |
| Declarative configuration | `usr/share/mios/mios.toml` | Capability registry, policy, ports, and defaults |

The current code already exposes several non-generation resources through
agent-pipe, including `/v1/storage/cephfs/*`, `/v1/inference/lora/*`,
`/v1/drift`, and `/v1/agents`. MiOS-API consolidates this pattern instead of
creating unrelated management listeners.

## Target topology

```text
OpenAI-compatible clients, Portal, CLI, MCP/A2A peers
                         |
                         | HTTPS or loopback HTTP /v1
                         v
                 mios-agent-pipe
        authentication -> PDP -> HITL -> audit/trace
                         |
                         | versioned local executor request
                         v
             miosd Unix-domain executor socket
          fixed capability handlers; no shell passthrough
                         |
               systemd, bootc, Podman, storage, network
```

Agent-pipe stays unprivileged (`mios-ai`). `miosd` is the only component allowed
to cross into privileged system operations. It accepts requests exclusively on
a local Unix socket, validates the peer and the signed delegated principal, and
dispatches only registered handlers. It must never accept arbitrary commands,
shell fragments, unit names, file paths, or environment assignments from an API
request.

`miosd` writes minimal durable job state below its existing
`/var/lib/mios/daemon` state directory. Agent-pipe projects sanitized job state,
audit events, and user-visible progress to the API. Secrets and command
arguments classified as sensitive are excluded from API responses, traces, and
pgvector events.

## Completed first slice: capability inventory

The read-only capability inventory is already shipped at
`GET /v1/capabilities`. It uses `mios_capreg.build_capability_manifest()` to
project the `[verbs.*]` and `[recipes.*]` SSOT entries, plus structured skills,
through the caller's permission ceiling. The result contains deterministic
`verb`, `recipe`, and `skill` records with a tier, description, and applicable
platforms; `GET /v1/capabilities/dag` exposes skill dependency edges and flags
cycles or dangling references.

The committed `usr/share/mios/ai/v1/capabilities.generated.json` is the
interactive-ceiling artifact. `tools/drift-checks.py capability-manifest`
regenerates it and fails on drift, while
`test_mios_capreg.py` and `test_mios_http_caps.py` cover the projection and
HTTP response contract. The system-specific capability registry in the next
slice extends this existing inventory; it does not replace it or create a
second catalog.

## API contract

The established OpenAI-compatible surfaces remain unchanged:

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/responses`
- `POST /v1/embeddings`
- tool calling, structured outputs, MCP, and A2A discovery

The additive management resources use predictable JSON objects and the standard
MiOS error envelope:

| Endpoint | Purpose | Mutability |
|---|---|---|
| `GET /v1/system/capabilities` | Caller-filtered capability catalog, schemas, risk class, and approval requirement | Read |
| `GET /v1/system/status` | Sanitized health, deployment, and job-summary projection | Read |
| `GET /v1/system/jobs/{job_id}` | Durable job state, progress, trace ID, and redacted result | Read |
| `POST /v1/system/jobs` | Submit one typed operation from the capability catalog | Write |
| `POST /v1/system/jobs/{job_id}/cancel` | Request cancellation of a cancellable job | Write |
| `POST /v1/hitl/approve` | Existing approval path; binds approval to one action hash | Approval |

`POST /v1/system/jobs` accepts a closed job envelope:

```json
{
  "capability": "system.unit.restart",
  "input": {
    "unit": "mios-agent-pipe.service"
  },
  "idempotency_key": "client-generated-opaque-key",
  "dry_run": false
}
```

The `capability` selects a schema from the catalog. The executor rejects unknown
fields and values outside that schema. `dry_run` returns the planned effect and
the approval posture without changing the host. Successful mutable requests
return `202 Accepted` with a job resource; they do not hold an HTTP request open
while a build, image deployment, or service transition runs.

The only supported initial capability families are:

| Family | Examples | Default posture |
|---|---|---|
| `system.status.*` | health, versions, units, storage | Read-only |
| `system.unit.*` | restart an allowlisted MiOS unit | Approval required |
| `system.image.*` | inspect, stage, or roll back a bootc deployment | Approval required |
| `system.container.*` | inspect or reconcile allowlisted Podman units | Approval required |
| `system.config.*` | validate or render a declarative MiOS configuration | Validate/read-only first |
| `system.build.*` | create or inspect a self-build job | Approval required |

There is no `system.exec`, `system.shell`, unrestricted `systemd`, unrestricted
Podman, or arbitrary-file API capability.

## Identity, authorization, and approval

1. Agent-pipe resolves `Authorization: Bearer` through the existing shared key
   or caller-key store into a principal and scope.
2. The PDP intersects the caller scope with the requested capability and the
   capability's resource allowlist.
3. The request is normalized, schema-validated, assigned a trace ID, and hashed.
4. Mutating or high-risk capabilities enter the existing HITL flow. An approval
   is valid only for the normalized action hash, principal, and bounded expiry.
5. Agent-pipe sends the executor a signed delegation containing principal,
   capability, normalized input hash, trace ID, approval reference, and expiry.
6. `miosd` independently rechecks the capability, signature, expiry, and
   resource allowlist before starting work.
7. Every transition is appended to the audit chain; API projections redact
   secret-bearing fields.

Network exposure follows the existing auth posture: default bind is loopback.
An externally reachable listener is permitted only when authentication is
required, the gateway is explicitly configured through `mios.toml`, and the
host firewall admits the named port. The executor socket is never exposed over
TCP.

## Configuration and source of truth

`mios.toml` gains a single declarative capability registry rather than per-route
constants. Each capability declares:

- canonical name and schema reference;
- read/write risk class and whether it is cancellable;
- required principal scope and HITL policy;
- bounded target resources;
- executor handler identifier; and
- audit redaction fields.

The registry projects to the API capability response, the agent tool catalog,
MCP tool definitions, and `miosd`'s accepted-handler table. This preserves
Law 7 (no operator-tunable hardcodes) and Law 8 (SSOT projection). The HTTP
route code is intentionally generic; it dispatches registered capabilities and
does not grow one imperative route per system command.

## Delivery sequence

1. **Inventory and normalize:** project existing `/v1/storage`,
   `/v1/inference`, drift, and agent resources into a generated capability
   manifest; add contract tests without changing their behavior.
2. **Read-only system slice:** implement `/v1/system/capabilities`,
   `/v1/system/status`, and a local `miosd` socket protocol for status handlers.
   Verify that unprivileged callers cannot reach the socket.
3. **Durable jobs:** add typed submit, status, idempotency, cancellation, and
   audit correlation using one harmless reconciliation capability.
4. **Approval-controlled mutations:** add allowlisted MiOS unit restarts, then
   image and build operations. Each capability must have negative authorization,
   missing-approval, expired-approval, and forbidden-resource tests.
5. **Tool projection:** expose the same generated registry through OpenAI tool
   definitions and MCP. The agent may propose an action, but only the job API
   plus HITL can execute it.
6. **Federation:** permit signed remote delegation only after local socket,
   audit, revocation, and policy tests pass. Remote peers never receive a wider
   capability set than local caller keys.

## Acceptance criteria

- One public HTTP gateway and one public `/v1` namespace; no duplicate
  management listener.
- No privileged system call is reachable from agent-pipe without a typed,
  policy-authorized, auditable capability invocation.
- Every mutable operation is asynchronous, idempotent, cancellable where
  feasible, approval-bound, and rollback-aware.
- The executor has no generic command execution path and no TCP listener.
- OpenAI-compatible generation behavior remains unchanged and contract-tested.
- Every exposed capability is generated from `mios.toml` and has schema,
  authorization, approval, redaction, and negative-path tests.

## Open questions

- Whether completed job records should be retained only in
  `/var/lib/mios/daemon` or additionally projected into PostgreSQL for
  cross-node history; the initial design keeps executor recovery local and
  projects sanitized audit events to PostgreSQL.
- Whether external management clients require a separate operator-issued
  caller-key scope or are limited to local Portal/CLI access in the first
  release.
- Which bootc image transitions can be cancelled safely after staging begins;
  those capabilities remain non-cancellable until their rollback semantics are
  measured and documented.
