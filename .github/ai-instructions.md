# MiOS AI Integration — GitHub Instructions

MiOS is a bootc-based, AI-native immutable workstation. AI agents
contributing to this repo must follow the rules in `INDEX.md` and the
canonical agent prompt at `usr/share/mios/ai/system.md`.

## Contribution rules for AI agents

1. **Architectural laws:** changes must comply with the six laws listed
   in `INDEX.md` §3.
2. **OpenAI v1 compatibility:** preserve the local OpenAI-compatible
   surface at `http://localhost:8080/v1`.
3. **FHS 3.0:** filesystem overlays follow the Filesystem Hierarchy
   Standard 3.0 (<https://refspecs.linuxfoundation.org/FHS_3.0/>).
4. **Sanitization:** persisted artifacts comply with
   `usr/share/mios/ai/system.md` §6 — no vendor brand prose, no chat
   metadata, no foreign sandbox path traces.

## Integration points

- **Canonical system prompt:** `usr/share/mios/ai/system.md`
  (host override: `/etc/mios/ai/system-prompt.md`,
  per-user: `~/.config/mios/system-prompt.md`).
- **Architectural index:** `INDEX.md`.
- **AI ingestion index:** `llms.txt`, `llms-full.txt`.

## Quick actions

- Validate image: `just build` (Containerfile final RUN is `bootc container lint`).
- Refresh AI manifests: `./automation/ai-bootstrap.sh`.
- Re-run lint on built image: `just lint`.
