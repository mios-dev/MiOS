<!-- AI-hint: The Blade-Node topology decision: what a blade is, what a node is, how a MiOS addresses a service that lives on another machine, and why "MiOS-Mini" currently names three different things. Establishes that base LINEAGE (which bootc base) and ROLE (what the machine does) are orthogonal axes, that service offload is a [urls] overlay rather than a code change because every pod is Network=host, and that the blade registry must key on something other than the port -- since port is currently the whole of a service's identity. -->
<!-- AI-related: usr/share/doc/mios/concepts/mios-mini-architecture.md, usr/share/mios/mios.toml [urls], [ports], [blades], [nodes], [profile], usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py, usr/lib/mios/agent-pipe/mios_pipe/scheduler/vram.py -->
---
adr: 0016
title: "Blade-Node topology — orthogonal lineage/role axes, and service offload as a URL overlay"
status: proposed
date: 2026-08-22
deciders: [operator, ai-pair]
tags: [topology, blades, nodes, mini, offload, addressing, image-variants]
laws: [1, 3, 5, 7, 8, 9, 12]
ssot_keys: [urls, ports, blades, nodes, profile, mini, quadlets.enable, greenboot.critical_services]
related_ws: [WS-BLADE, WS-MIOSSYS, WS-GUARD]
supersedes: []
superseded_by: []
---

# ADR-0016: Blade-Node topology — orthogonal lineage/role axes, and service offload as a URL overlay

## Status

**Proposed.** Decisions 1, 2 and 4 below are mechanical consequences of what the tree already
is and are recommended for acceptance as written. **Decision 3 (naming) is deliberately left
open** — it is the operator's call and every other decision here is independent of it.

## Context

Three separate things in this repository currently answer to a variant of the name *mini*:

| Claimant | What it actually is | Evidence |
|---|---|---|
| `[mini]` + `mios-mini-architecture.md` | A **tiny headless hypervisor-router**: binds every dGPU to `vfio-pci`, owns the NICs/radios/TPM, and boots the *full* MiOS as a super-privileged guest VM | `bind_dgpu_vfio = true`, `dgpumode = "vfio-pci"`, `[mini.gpu].assignments`, `[mini.mesh]` headscale; 224-line architecture doc with decisions D1–D5 and risks R1–R10 |
| `Containerfile.minimal` | A **base-lineage variant**: bare `fedora-bootc` instead of `ucore-hci`. Its own header calls it *"MiOS-Lite"* and marks it `STUB / EXPERIMENTAL` | `Containerfile.minimal` header; ~1.2 GB vs ~2.5 GB |
| The operator's stated intent | A **full-featured seat** that runs the whole UX but offloads every service to a hosted MiOS OCI image, local / localhost / remote | stated requirement |

The first two are not variants of each other, and neither is the third. They differ on **two
orthogonal axes** that the naming has collapsed into one:

* **Lineage** — which bootc base the image is built from (`ucore-hci` vs `fedora-bootc`). Affects
  size, inherited kmods, and upstream lag. Decided at bake time.
* **Role** — what the machine *does* (owns metal and hypervises; serves services to others; runs
  the UX and consumes services). Affects which units start and where addresses point.

Conflating them is why "mini" has three meanings. `[profile].role` already exists (`"developer"`,
with `features = ["ai", "virtualization", "k3s"]`), and `Containerfile.minimal` already exists;
they are answers on different axes.

### What the tree can express today

Measured, not assumed:

| Fact | Value |
|---|---|
| Pods | **All three are `Network=host`.** No container publishes a port |
| `[urls]` coverage | **9 of 41** addressable ports have a canonical URL; the other **32 are hand-composed** in 1–18 files each |
| Consumers hand-composing an address | ~125 non-generated, non-doc files |
| `[blades]` | **Zero keys.** An empty section under a 30-line comment about nodes |
| `[admission].multiblade_enable` | `false` |
| `[nodes.*]` | 6 declared; **5 point at the same endpoint and the same model**; 1 ships empty |
| `[nodes.local-cpu]` | `lane = "gpu"`, endpoint = the GPU heavy lane. There is no CPU lane |
| `[greenboot].critical_services` | `agent-pipe`, `llm-light`, `pgvector` |
| `[quadlets.enable]` gated off | exactly **one** container |

`Network=host` is the load-bearing one. It means every service genuinely *is* on the host's
loopback, so a service's identity is **its port number** and nothing more — `_discover_portal_services()`
dedupes the entire service surface by port. It also means the ~600 `localhost` references across
the tree are not sloppiness; they are the architecture stating itself.

The consequence cuts both ways. Because there is no network namespace to re-plumb, **moving a
service to another machine is purely an addressing change** — but because service identity *is*
the port, there is currently nowhere to put the "which machine" half of the answer.

## Decision

### 1. Service addressing becomes total through `[urls]`, and offload is an overlay

Every addressable service gets exactly one canonical address key in `[urls]`. Consumers resolve
`MIOS_URL_*`; no consumer composes `localhost:${MIOS_PORT_*}` itself. A drift gate enforces both
halves, with a shrink-only register draining the existing debt the way `[refactor].oversize` and
`[schema].unconsumed` already do.

Offloading a service is then an `/etc/mios/mios.toml` overlay that rewrites its URL. No quadlet
change, no code change, no rebuild — `Network=host` already put every port on a real address, and
the three-layer resolver (vendor < host < user) already exists to override it.

This is Law 9 (one canonical name) applied to **addresses** rather than to values, and it is
required under *every* answer to the naming question, which is why it is decided first and
separately.

### 2. A blade is a machine; a node is a lane on a blade

* A **blade** is a machine that serves addresses. `[blades.<name>]` becomes the machine registry:
  reachability (host or tailnet name), what it serves, and its capacity envelope.
* A **node** stays what `_load_node_pool()` already makes it — one canonical inference worker on
  one lane — and gains a `blade` field naming its host. `[nodes.*]` keys stop pretending to be
  machines (`local-dgpu` and `local-sglang` are the same box, the same port and the same model).
* A **seat** is a machine that runs the UX and consumes addresses. A seat may also be a blade.

The existing `health_gate = true` semantics — *auto-join when reachable, drop when gone* — become
the blade-level availability primitive rather than a per-node flag.

`[blades]` being empty today is not a gap to fill with the current node list; the current node list
is five aliases for one backend and must collapse before anything is built on it.

### 3. Naming — OPEN, operator's call

Two coherent resolutions exist and the rest of this ADR holds under either:

* **(a) Keep `mini` where it is.** The hypervisor-router stays MiOS-Mini; the seat gets its own
  name. Costs nothing already written; costs the operator the word they wanted.
* **(b) Move `mini` to the seat.** The hypervisor-router is renamed (MiOS-Router / MiOS-Metal),
  and `mios-mini-architecture.md`, `[mini]`, `[mini.gpu]`, `[mini.mesh]`, `mios-mini-vfio-gen`,
  `mios-mini-mesh-gen` and drift-check #68 move with it. Costs a rename across the most finished
  design artifact in the tree; costs nothing architectural.

`Containerfile.minimal` is on the **lineage** axis in both cases and should be named for its base,
not for a role — its own header already calls it *MiOS-Lite*.

### 4. One image, role by flag — on the role axis only

Role is a **runtime** activation, not a bake-time fork: `[profile].role` selects which units start
and which addresses resolve locally. This is the WS-BLADE *"one image, role by flag"* position and
it is what `[quadlets.enable]` and `[profile]` were built for.

Lineage stays a **bake-time** fork, because it is one — a different `FROM`.

The two must not be conflated again: a role must never require its own Containerfile, and a lineage
must never imply a role.

## Consequences

**Enabling**

* Offload becomes a config overlay. A seat pointed at a blade is `[urls]` rewritten, nothing more.
* "local, localhost or remote" collapses into one mechanism: they are three values of the same URL.
* The blade registry gives the VRAM/admission machinery (`_BLADE_POOL`, `_ENDPOINT_BLADE`,
  `MULTIBLADE_ENABLE`) an SSOT to read, which it currently lacks.

**Costs and hazards**

* **`[greenboot].critical_services` will roll a seat back on every boot.** It lists `llm-light` and
  `pgvector`, which a seat does not run. Greenboot must become role-aware, or a seat's "critical"
  must be redefined as *can reach my blade* — which makes boot success depend on the network, and
  that trade must be taken deliberately (Law 12 says degrade open, never block boot).
* **Law 3 BOUND-IMAGES** symlinks every Quadlet image so it ships *with* the host. A seat that runs
  none of them still carries all of them. Either Law 3 gains a role-aware exception, or a seat is
  not actually smaller — only quieter.
* **Service identity is the port.** Two blades serving the same service collide in
  `_discover_portal_services()`, which dedupes by port. Either the portal service list moves to
  `[urls]`, or blades get a port offset — `[ports].stack_id` already computes `stack_id * 10000`
  and is the obvious candidate for a blade ordinal.
* **`Network=host` on a blade exposes every service** to anything that can route to it. A blade is
  only as safe as its mesh plus inbound auth; there is no per-service network boundary to attach a
  policy to.
* **Shared state is not shared identity.** Two seats on one pgvector collide on the `uid_alloc` /
  `gid_alloc` sequences and the RLS owner column. Either the blade is the identity authority, or
  seats keep local identity and rent only the vector store.

**Deliberately not decided here**

* Whether URLs gain a per-service host variable (`${MIOS_HOST_X}`) or are overridden whole. Whole-URL
  override needs no new machinery and is the default until a blade ordinal exists.
* Whether a seat may write to a blade's pgvector, and whose `[security.redact]` policy applies on
  the persist path when it does.
* Blade discovery. Static endpoints work today; `mios_gossip.py` has no transport under it (T-229).

## Rationale

The alternative — building a second image and a service-placement engine — was rejected because the
tree does not need one. `Network=host` already made every service address a real, routable address;
the only thing missing is a canonical name for each address and the discipline to use it. That is a
gate and a register, not an architecture.

Starting from naming would have been the mistake. The naming collision is real but it is
downstream: every mechanism above is identical whichever image ends up called *mini*.
