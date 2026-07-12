<!-- AI-hint: Defines the MiOS three-tier permission model (USER/SYSTEM/AI) and the GID-based bucket groups (mios-ai 850, mios-sys 860) that gate cross-service reads of shared agent/infra state on the immutable bootc workstation; also documents the consolidated core AI-agent user (mios-ai, uid 850) the agent/code plane runs as. Use this to understand ACL requirements for sharing files between MiOS services and to ground UID/GID allocations.
     AI-related: mios-ai, mios-sys, mios-virt, mios-llm-light, mios-llamacpp, mios-pgvector, mios-open-webui, mios-hermes, mios-agent-pipe, mios-searxng, mios-crawl4ai, mios-codemode, mios-guacamole, mios-forge, mios-crowdsec, usr/lib/sysusers.d/50-mios-services.conf, usr/lib/sysusers.d/10-mios.conf -->
# MiOS Linux user / group model

> **Where this fits.** MiOS is one image built two ways at once: an immutable
> bootc/OCI Fedora workstation *and* a local, self-replicating agentic AI OS. The
> same image ships GNOME/Wayland, GPU-via-CDI, KVM/libvirt, and a k3s+Ceph
> cluster path **and** a full local agent stack behind one OpenAI-compatible
> endpoint. Two service planes therefore share one host: an **infra (SYSTEM)**
> plane and an **AI** plane. This document is the SSOT for how those planes are
> kept least-privileged yet able to share state — the permission model that lets
> the agent stack read its own shared surfaces without collapsing the security
> boundaries that keep a compromised agent contained. It serves the Architectural
> Laws' intent (Law 6, UNPRIVILEGED-QUADLETS) at the user/group layer.

Operator directive 2026-05-18: *"consolidate MiOS Linux users/wheel(s)/
groups for USER/SYSTEM/AI Separations -- keeping the entire stack as
minimal as possible"*.

This doc is the SSOT for the three-tier permission model. The authoritative
declaration lives in `usr/lib/sysusers.d/10-mios.conf` (the login user) and
`usr/lib/sysusers.d/50-mios-services.conf` (the service accounts + bucket
groups); this document is the human-readable rationale for what those files
declare. Per-service sysusers stay where they are; the only NEW ACL surfaces
are the two shared bucket groups described below.

## Three tiers

| Tier   | Who                                     | Purpose                                  |
|--------|-----------------------------------------|------------------------------------------|
| USER   | `mios` 1000 (operator login)            | Hands-on operator session                |
| SYSTEM | infra services (Guacamole, PXE hub, Forgejo, CrowdSec, AdGuard, libvirt/`mios-virt`) | Non-AI service plane    |
| AI     | AI agents (the inference lanes, Open WebUI, Hermes, agent-pipe, pgvector, SearXNG, web-tools, code-mode sandbox) | AI service plane        |

These two service planes are not bolted-together products — they coexist on one
immutable host. The tiering is what lets each plane share its *own* state freely
while staying walled off from the other and from the operator's writable home.

## Two bucket groups

| Group     | GID | Members                                                                                                                  | What it gates                                                                  |
|-----------|-----|------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| `mios-ai` | 850 | `mios-open-webui`, `mios-hermes`, `mios-agent-pipe`, `mios-searxng`, `mios-crawl4ai`, `mios-pgvector`, `mios-llamacpp`, `mios-codemode` | Cross-agent reads: skill catalog, passport public keys, shared scratch, kanban shadow |
| `mios-sys`| 860 | `mios-guacamole`, `mios-guacd`, `mios-postgres`, `mios-pxe-hub`, `mios-crowdsec`, `mios-forge`, `mios-adguard`          | Cross-infra reads: shared configs, common state                               |

The login user `mios` is a member of BOTH groups (declared in `10-mios.conf`) so
the operator reads every shared surface without sudo. Writes still require the
per-service UID or `sudo -u <service> …`.

> **Migration note (Ollama/the legacy datastore removal).** Earlier revisions listed
> `mios-ollama`, `mios-ollama-cpu`, and `mios-legacydb` in the `mios-ai` bucket.
> Those backends are **removed**: local inference + embeddings now run on the
> `mios-llm-light` lane (`mios-llamacpp` uid 827) and the unified agent datastore
> is **PostgreSQL + pgvector** (`mios-pgvector` uid 826). The bucket membership
> above reflects the current AI plane; the legacy accounts are gone from the
> group.

## The consolidated core AI-agent user

Operator directive 2026-05-23 (*"consolidate MiOS system users to fewer
combined/core users"*) collapsed the agent/code **process** plane onto a single
runtime identity, while keeping every isolated DATA-plane container on its own
UID.

- **`mios-ai` (uid 850, gid 850)** is both the AI bucket group GID *and* the user
  the agent/code plane now runs as: `agent-pipe`, `hermes-agent`,
  `delegation-prefilter`, `hermes-browser`, `mios-daemon`, `mios-mcp`, and the
  skills-miner. One owner for `/var/lib/mios` agent state means no cross-user
  permission walls (the class of bug behind the earlier container/snapshot
  visibility failures). `HOME=/var/lib/mios/hermes` keeps opencode's `~/.local`
  and `$HERMES_HOME` working; the user also carries `systemd-journal` + `adm`
  for read-only log/journal access.
- **Per-container DATA-plane users stay isolated.** The inference lanes
  (`mios-llamacpp`), the datastore (`mios-pgvector`), Open WebUI
  (`mios-open-webui`), search (`mios-searxng`), web-tools (`mios-crawl4ai`), and
  the code-mode sandbox (`mios-codemode`) each keep their own UID for
  `/var/lib` ownership stability, and join `mios-ai` only for cross-agent reads.
- **Legacy `mios-hermes` (820) + `mios-agent-pipe` (822) are retained inert** for
  `sudo -u` / `chown` reference-compat. Nothing runs as them now, but their
  GIDs survive so existing on-disk ownership and tooling keep resolving.

This is the user-layer expression of the AI stack the rest of the system
describes: the agent-pipe orchestrator, the MiOS-Hermes gateway, the MCP/A2A
tool/agent surfaces, and the pgvector memory all run as one least-privileged
identity that can read the shared AI surfaces but cannot write another plane's
state.

## How shared files end up readable

Standard pattern for sharing a file across the AI bucket — set the group to
`mios-ai` and grant group-read:

```
chown mios-agent-pipe:mios-ai /var/lib/mios/skills/catalog.json
chmod 0640 /var/lib/mios/skills/catalog.json
```

For directories that house multiple shared files, declare them via tmpfiles
(Architectural Law 2 — NO-MKDIR-IN-VAR; every `/var/` path is declared in
`usr/lib/tmpfiles.d/*.conf`, never written at build time):

```
d /var/lib/mios/<dir> 0750 <owner-sysuser> mios-ai -
```

The `0750` keeps "others" (non-AI processes, including the SYSTEM plane) out.
The setgid bit isn't used by default — newly-created files inherit the writer's
primary group unless the writer sets sgid on the dir explicitly.

## Per-service UIDs stay

Every agent / infra service keeps its own UID/GID for `/var/lib`
ownership stability across image rebuilds. Collapsing UIDs would mean a
compromised service could write to another's state dir; the per-UID
ownership is the actual security boundary. The bucket groups
add an OR clause (READ on group=`mios-ai` or `mios-sys`) on top, not a
replacement. This is the user-level half of Law 6 (UNPRIVILEGED-QUADLETS):
the Quadlets declare `User=`/`Group=`, and these pinned identities are what
those declarations resolve to.

## Live verification

```
getent group mios-ai mios-sys
id mios            # should list both bucket groups in supplementary
id mios-agent-pipe # should list mios-ai
id mios-pgvector   # should list mios-ai (the unified agent datastore)
id mios-forge      # should list mios-sys
```

## Pinned IDs (for /var/lib chown stability across rebuilds)

UID/GID allocations are pinned in `usr/lib/sysusers.d/*.conf` and mirrored in
`usr/share/mios/mios.toml` under `[services.<svc>]`. Pinning keeps `/var/lib`
ownership stable so that an immutable rebuild (Law 3, BOUND-IMAGES) and a
`bootc upgrade` never reshuffle who owns agent state on disk.

| Range     | Allocation                                                          |
|-----------|--------------------------------------------------------------------|
| 36/39/105 | Hardware groups (`kvm`, `video`, `render`) — inherited from base image |
| 800       | `mios-virt` (virtualization service)                               |
| 810-829   | Per-service sysusers (Guacamole stack, PXE hub, CrowdSec, Forge, Open WebUI, SearXNG, Hermes, agent-pipe, web-tools, AdGuard, `mios-pgvector` 826, `mios-llamacpp` 827, `mios-codemode` 828) |
| 850       | `mios-ai` — AI bucket group **and** the consolidated core AI-agent user |
| 860       | `mios-sys` — SYSTEM bucket group                                   |
| 1000      | `mios` (operator login)                                            |
| 1001      | `core` (CoreOS legacy)                                             |

Bucket GIDs are pinned above the 810-829 sidecar range so they never collide on
a host where `systemd-sysusers` auto-allocates.
