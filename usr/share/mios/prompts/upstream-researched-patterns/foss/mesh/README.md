# Upstream researched patterns -- FOSS/mesh

This prompt family is for primary-source research of the free and
open-source mesh-VPN client, coordinator and identity provider that MiOS
Blades and hosted nodes use for the HCI mesh (TASKS.md T-986).

## Prompts

- `userspace-mesh-node-capabilities.xml.md` -- which client features work in
  userspace-networking mode: inbound, serve, public ingress, relay through an
  egress proxy, several instances per host, and role claims.
- `self-hosted-mesh-coordinator.xml.md` -- the self-hosted coordinator's
  features, client compatibility, packaging, and behaviour while it is down.

Every prompt requires primary sources, exact versions, a badge and a
confidence per claim, and replies with one JSON object that validates against
the strict OpenAI-format `response_format` schema embedded in the prompt.
These are research prompts, not commands: they must not mutate the
repository, authenticate to a service, or handle real secrets.
