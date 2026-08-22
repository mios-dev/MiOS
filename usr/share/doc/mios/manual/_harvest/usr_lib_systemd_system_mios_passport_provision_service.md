<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes the mios-passport provision tool to generate Ed25519 keypairs for all agents in [passport.agents] and sets strict 0600 permissions on private keys before agent services start.
AI-related: /usr/libexec/mios/mios-passport, /etc/mios/userenv.sh, mios-passport, mios-passport-provision, mios-daemon, mios-agent-pipe, mios-ai, mios-hermes, mios-pgvector.service
/usr/lib/systemd/system/mios-passport-provision.service
Phase C.3 of the AgentOS roadmap: keypair generator. Runs at
firstboot (and on every subsequent boot, idempotent) so every
agent in [passport].agents has an Ed25519 private key on disk
before agent-pipe / hermes-agent / mios-daemon / opencode start.

Each agent gets its own keypair at
  /var/lib/mios/agent-passports/<agent>/{private.key,public.key}
Private key 0600 owned by root (sysuser-owned permission flip
happens in the ExecStartPost so the agent's own service can
read its private key without an extra ACL).

<!-- mios-src:e4dff074d1b4 from usr/lib/systemd/system/mios-passport-provision.service:1-13 -->

