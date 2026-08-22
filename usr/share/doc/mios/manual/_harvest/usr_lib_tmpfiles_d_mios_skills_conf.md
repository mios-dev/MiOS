<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the persistent storage directory for the MiOS skill catalog at /var/lib/mios/skills, ensuring the miner (uid 822) can write and all AI agents (gid 850) can read the shared catalog.json file.
AI-related: /usr/share/mios/skills, mios-skills, mios-ai
/usr/lib/tmpfiles.d/mios-skills.conf
Phase C.2 of the AgentOS roadmap: persistent state dirs for the
MiOS skill catalog. The seed catalog lives under
/usr/share/mios/skills (read-only, bootc-immutable); operator-
authored or mined skills land under /var/lib/mios/skills
(writable, persistent across upgrades).

The catalog.json file emitted by `mios-skills export-catalog` is
the cross-agent static surface every external agent (MiOS-Hermes,
MiOS-OpenCode, future MCP clients) reads when agent-pipe HTTP is
not reachable in their deployment context. World-readable so a
user-namespace OpenCode rootless container can read it without
extra ACLs.

<!-- mios-src:6862c60c96ef from usr/lib/tmpfiles.d/mios-skills.conf:1-15 -->

