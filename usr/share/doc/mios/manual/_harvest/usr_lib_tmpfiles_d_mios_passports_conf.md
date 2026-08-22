<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the directory structure and permissions for agent identity keys, ensuring public keys are accessible to the mios-ai group for cross-agent verification while restricting private keys.
AI-related: mios-ai, mios-passports, mios-passport-provision, mios-passport-provision.service
/usr/lib/tmpfiles.d/mios-passports.conf
Phase C.3 of the AgentOS roadmap: persistent state dir for the
agent passport keypairs. Each agent's keypair lives under
/var/lib/mios/agent-passports/<agent>/ -- the parent dir is
world-readable so any agent can resolve another agent's public
key for verification without an ACL flip.

Per-agent subdirs are created at provision time by
mios-passport-provision.service with the correct sysuser
ownership for private.key (0600 sysuser:sysuser) and public.key
(0644 sysuser:sysuser).

<!-- mios-src:b07a063bec75 from usr/lib/tmpfiles.d/mios-passports.conf:1-13 -->

