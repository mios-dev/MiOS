# MiOS Linux user / group model

Operator directive 2026-05-18: *"consolidate MiOS Linux users/wheel(s)/
groups for USER/SYSTEM/AI Separations -- keeping the entire stack as
minimal as possible"*.

This doc is the SSOT for the three-tier permission model. Every per-
service sysuser stays where it is; the only NEW ACL surfaces are the
two shared bucket groups described below.

## Three tiers

| Tier   | Who                                     | Purpose                                  |
|--------|-----------------------------------------|------------------------------------------|
| USER   | `mios` 1000 (operator login)            | Hands-on operator session                |
| SYSTEM | infra services (Guacamole, PXE, Forgejo, CrowdSec, libvirt) | Non-AI service plane    |
| AI     | AI agents (Ollama, Hermes, OWUI, SurrealDB, agent-pipe, ...) | AI service plane        |

## Two bucket groups

| Group     | GID | Members                                                   | What it gates                             |
|-----------|-----|-----------------------------------------------------------|-------------------------------------------|
| `mios-ai` | 850 | mios-ollama, mios-open-webui, mios-hermes, mios-surrealdb, mios-agent-pipe, mios-ollama-cpu, mios-searxng | Cross-agent reads: skill catalog, passport public keys, scratch, kanban shadow |
| `mios-sys`| 860 | mios-guacamole, mios-guacd, mios-postgres, mios-pxe-hub, mios-crowdsec, mios-forge | Cross-infra reads: shared configs, common state |

The login user `mios` is a member of BOTH groups so the operator
reads every shared surface without sudo. Writes still require the
per-service UID or `sudo -u <service> …`.

## How shared files end up readable

Standard pattern for sharing a file across the AI bucket:

```
chown mios-agent-pipe:mios-ai /var/lib/mios/skills/catalog.json
chmod 0640 /var/lib/mios/skills/catalog.json
```

For directories that house multiple shared files:

```
d /var/lib/mios/<dir> 0750 <owner-sysuser> mios-ai -
```

The `0750` keeps "others" (non-AI processes) out. The setgid bit
isn't used by default -- newly-created files inherit the writer's
primary group unless the writer sets sgid on the dir explicitly.

## Per-service UIDs stay

Every agent / infra service keeps its own UID/GID for `/var/lib`
ownership stability. Collapsing UIDs would mean a compromised
agent could write to another agent's state dir; the per-uid
ownership is the actual security boundary. The bucket groups
add an OR clause (READ on group=mios-ai) on top, not a
replacement.

## Live verification

```
getent group mios-ai mios-sys
id mios            # should list both bucket groups in supplementary
id mios-agent-pipe # should list mios-ai
id mios-forge      # should list mios-sys
```

## Pinned IDs (for /var/lib chown stability across rebuilds)

| Range     | Allocation                |
|-----------|---------------------------|
| 36/39/105 | Hardware groups (kvm, video, render) -- inherited from base image |
| 800       | mios-virt                 |
| 810-823   | Per-service sysusers      |
| 850       | mios-ai (AI bucket group) |
| 860       | mios-sys (SYSTEM bucket)  |
| 1000      | mios (operator login)     |
| 1001      | core (CoreOS legacy)      |
