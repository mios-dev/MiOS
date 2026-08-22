<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the persistent state directory and permissions for the mios-agent-pipe service, ensuring the mios-ai user (UID 850) has exclusive access to the agent pipe's data.
AI-related: mios-agent-pipe, mios-ai, mios-services
/usr/lib/tmpfiles.d/mios-agent-pipe.conf
Persistent data + state dir for the standalone Agent Pipe service,
owned by the consolidated agent user mios-ai (uid/gid 850, declared in
/usr/lib/sysusers.d/50-mios-services.conf). The legacy mios-agent-pipe
(822) account is retained INERT -- the agent plane runs as mios-ai.
bootc-immutable code path; mutable state stays under /var.

<!-- mios-src:6df58b34ed9d from usr/lib/tmpfiles.d/mios-agent-pipe.conf:1-8 -->

