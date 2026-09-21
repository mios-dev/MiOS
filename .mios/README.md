# MiOS root control plane

The MiOS repository has two distinct layers:

1. **Root dotfolders** are the source-control workflow and review control
   plane. They organize prompts, research, documentation staging, secrets
   boundaries, and generated work without pretending those paths are runtime
   FHS destinations.
2. **FHS directories** (`etc/`, `usr/`, `var/`, `srv/`) are the deployable
   system overlay. They remain authoritative for image contents and runtime
   paths.

| Root path | Purpose | Commit policy | Deploys to |
|---|---|---|---|
| `.mios/` | workflow contract and metadata | tracked | nowhere |
| `.prompts/` | prompt authoring/indexes | tracked, no secrets | `usr/share/mios/prompts/` after projection |
| `.research/` | working research and evidence staging | tracked when promoted | `docs/research/` |
| `.docs/` | documentation drafts and publication manifests | tracked | `docs/` or `usr/share/doc/mios/` |
| `.secrets/` | local secret boundary and placeholders | README only | secret manager or `/etc/mios/secrets.env` |
| `.artifacts/` | generated outputs and validation results | ignored | nowhere |
| `.work/` | disposable agent/build scratch | ignored | nowhere |

Dotfolders do not replace the existing `mios.toml` SSOT, the FHS overlay, or
the `usr/share/mios/prompts/` shipped surface. They make authoring and
promotion visible at repository root while keeping generated/runtime paths
governed by their existing laws.

## Promotion rules

- Write new prompt sources and indexes in `.prompts/`.
- Promote reviewed prompts to `usr/share/mios/prompts/` as complete files.
- Stage research in `.research/`; publish durable reports under
  `docs/research/`.
- Stage documentation in `.docs/`; publish shipped documentation under
  `usr/share/doc/mios/` only when it belongs in the image.
- Never put credentials in `.secrets/`; use `[REDACTED]` or
  `<REPLACEMENT_CREDENTIAL>` placeholders.
- Never place generated output, logs, caches, or model artifacts in tracked
  dotfolders.
