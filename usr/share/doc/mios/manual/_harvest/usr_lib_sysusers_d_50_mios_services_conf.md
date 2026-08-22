<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines pinned UIDs/GIDs for MiOS system and AI service accounts, establishing the 810-829 range for stable filesystem ownership and the 850/860 bucket groups for cross-service state sharing.
AI-related: /usr/lib/mios/crawl4ai/.venv, /etc/mios/adguard, /etc/mios/hermes/api.env, mios-ai, mios-sys, mios-virt, mios-hermes, mios-agent-pipe, mios-daemon, mios-mcp
'MiOS' sidecar service accounts -- pinned IDs in the 810-829 range to keep
/var/lib ownership stable across image rebuilds.
Format: u USER UID:GROUP "GECOS" HOME SHELL

---- USER / SYSTEM / AI separation (operator directive 2026-05-18) ----

MiOS uses a three-tier permission model:

  USER tier   -- the login operator (`mios` 1000) in 10-mios.conf.
                 Member of `wheel` (sudo), `mios-ai` (read AI shared
                 state without sudo), `mios-sys` (read SYSTEM shared
                 state without sudo), and the hardware groups.

  SYSTEM tier -- infra services (Guacamole stack, PXE hub, CrowdSec,
                 Forgejo VCS, libvirt/mios-virt). Per-service UIDs
                 remain for /var/lib ownership stability; all share
                 the `mios-sys` GROUP so files chgrp'd to mios-sys
                 are readable by every infra service without per-
                 service ACL surgery.

  AI tier     -- AI agents (Open WebUI, Hermes,
                 agent-pipe, SearXNG, pgvector, llamacpp). Same shape: per-
                 service UIDs for fs ownership, shared `mios-ai`
                 group for cross-agent reads (skill catalog, passport
                 public keys, shared scratch, kanban shadow, ...).

The two bucket groups (mios-ai, mios-sys) are the ONLY new ACL
surfaces. Existing per-user groups stay -- they own their service's
state dir so a compromised agent can't smash another agent's state.
Cross-agent reads happen through `chgrp mios-ai` + `0640` on the
specific files that need to be shared, not by collapsing user IDs.

Bucket group GIDs are pinned at 850 (mios-ai) + 860 (mios-sys) --
above the per-service 810-829 range so they don't collide on a host
where systemd-sysusers auto-allocates.

<!-- mios-src:26abb11beadc from usr/lib/sysusers.d/50-mios-services.conf:1-37 -->

