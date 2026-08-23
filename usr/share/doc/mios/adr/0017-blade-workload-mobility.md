<!-- AI-hint: Workload mobility across the blade mesh: scheduling, fallbacks, failover, and divergence. -->

<!-- AI-related: usr/share/doc/mios/adr/0016-blade-node-topology.md, usr/share/mios/mios.toml [blade], [blade.archetypes], [blade.requires], [blades], [nodes], usr/libexec/mios/role-apply, tools/generate-blade-dropins.py -->
---
adr: 0017
title: "Blade workload mobility — placement ownership, degrade-not-refuse, local-first failover, and blade-only divergence"
status: accepted
date: 2026-08-22
deciders: [operator, ai-pair]
tags: [topology, blades, nodes, failover, placement, scheduling, ha, data]
laws: [3, 5, 7, 8, 12]
ssot_keys: [blade, blade.archetypes, blade.requires, blade.discovery, blade.collapse, blade.placement, blade.reconcile, blades, nodes]
related_ws: [WS-BLADE, WS-MIOSSYS, WS-GUARD]
supersedes: []
superseded_by: []
---

# ADR-0017: Blade workload mobility

## Status

**Accepted.** ADR-0016 settled what a blade, a node and a seat *are*, and that
`MiOS-Metal` is the seat archetype of one image. It did not settle what happens
when a blade dies, who places a workload, or what a GPU service does on a
machine with no GPU. Those are decided here.

This ADR **extends** ADR-0016; it does not supersede it. Every definition there
stands, including the two that constrain this one: a seat has no local inference
floor (§6) and a seat is stateless (§8).

## Context

The tree ships two schedulers with no stated boundary. `k3s` places containers;
`Pacemaker`+`Corosync` live-migrates VMs. Nothing said which owns what, so both
could claim a workload and neither could be held responsible for it.

`[blade.requires]` already maps a service to the capabilities it needs, and
`[blade.archetypes]` maps an archetype to the capabilities it grants. That is a
working placement-constraint system. What it does not express is what happens
when the constraint cannot be met anywhere reachable — the service simply does
not start, which reads as a hang rather than a decision.

The operator's requirement is that workloads move freely: *"everything can
migrate anywhere and is always load-balancing services, containers and VMs among
blades across the entire cluster/mesh."* Free movement raises three questions the
tree cannot currently answer, plus one it must be prevented from answering
badly.

## Decision

### 1. Two schedulers, one boundary, by workload kind

| Kind | Owner | Mechanism |
|---|---|---|
| Containers, pods, Quadlet workloads | **k3s** | scheduler + nodeSelector |
| Virtual machines | **Pacemaker + Corosync** | `VirtualDomain allow-migrate` |

Neither ever schedules the other's kind. If it is an image, k3s owns it; if it
is a libvirt domain, Pacemaker owns it.

The alternative — KubeVirt, making VMs into CRDs so one scheduler owns both —
was rejected for the same reason ADR-0016 D5 rejected it: it pulls a full
KubeVirt control plane onto every machine, and the tree already runs Pacemaker
for `MiOS-Teleport`. Building a third arbiter over the two was rejected as
inventing a scheduler to referee two mature ones.

### 2. A GPU service on a GPU-less blade degrades; it does not refuse

`mios-llm-heavy` requires `gpu-serving`. Today that means it cannot land on a
blade without a GPU. It will instead start its **CPU fallback lane** — the same
`/v1` contract, the same SSOT-allocated port, lower throughput.

This is what makes "migrate anywhere" literally true rather than aspirational:
there is no blade a service cannot land on, only blades where it runs slower. A
caller never has to know which kind of blade answered.

The fallback is declared alongside the requirement, so one declaration still
drives both schedulers and no constraint is hand-maintained in two dialects.

### 3. Failover tries local first, then the cluster allocates

A failed workload is retried **local/localhost first**, and only then handed to
the cluster for allocation elsewhere.

The reason is that a large share of failures are a crashed process on a healthy
machine, where a restart in place is the whole fix. Migrating first turns a
two-second restart into a scheduling event, a cold start, and possibly a volume
move. Trying local first costs one restart interval and avoids all of that; when
local recovery does not take, allocation proceeds normally.

This does **not** amend ADR-0016 §6. A seat still grants no service capability
and runs no service in steady state. Local-first is a *recovery ordering* for a
workload already assigned to a machine, not a licence for a seat to acquire one.

### 4. Anti-flap is asymmetric by construction

Absorbing work is quick; releasing it is slow. Symmetric thresholds oscillate: a
blade on a flaky link would absorb and release repeatedly, migrating workloads on
every flap and spending all its time moving rather than serving. The dwell before
failing back is therefore several times the dwell before taking over, and both
values live in SSOT rather than in code.

### 5. Only blades may diverge; seats keep nothing

During a partition, blades **accept writes independently and reconcile on
rejoin**. Availability is chosen over consistency deliberately.

Seats are excluded, which follows from ADR-0016 §8 rather than being a new rule:
a seat keeps nothing, so a seat has nothing to diverge. Divergence is strictly
blade-to-blade.

Availability at that price is affordable only because of what MiOS stores, and
only if the merge rule is fixed per data class in advance. A vague rule here is
how this decision fails:

| Data | Merge rule | Why it is safe |
|---|---|---|
| `knowledge`, embeddings | union by content hash | Immutable and derived; the same input yields the same vector, so a duplicate is a no-op. |
| `agent_memory`, `event` | append-only, ordered by (timestamp, origin) | Nothing updates in place, so a merge is a sort. |
| `session`, `scratch` | last-writer-wins per key | Ephemeral by definition; the older value costs nothing. |
| `config_kv` | **conflict is an error, operator resolves** | Config is intent. Auto-picking a winner would let a partition silently change policy. |

Every row therefore carries an origin node id and a logical timestamp. Without
those the merge is not implementable, so this is a schema prerequisite and not an
optimisation: divergence must not be enabled before it lands.

## Rationale

Workloads must move across the blade mesh deterministically while maintaining system stability and data safety. Schedulers are explicitly bounded by workload type to avoid placement conflicts.

## Consequences

- `[blade.requires]` gains a fallback lane per GPU-gated service; the capability
  model of ADR-0016 is extended, not replaced.
- New SSOT surfaces: `[blade.placement]`, `[blade.collapse]`, `[blade.discovery]`,
  `[blade.reconcile]`.
- The pgvector schema needs origin-node and logical-timestamp columns before
  divergence is permitted. Until then, partitioned writes are not enabled.
- `config_kv` conflicts surface to the operator rather than resolving silently,
  which is a deliberate availability cost on exactly one table.
- Endpoint resolution walks a declared order and takes the first healthy tier
  (`localhost` → LAN mDNS → tailnet → declared remote), so the same chain that
  answers "where is this service" also answers "am I isolated".
