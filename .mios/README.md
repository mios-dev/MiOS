<!-- AI-hint: Explains the two layers of the MiOS repository: root dotfolders as the review and workflow control plane, and the FHS directories as the deployable system overlay. -->
# MiOS root control plane

The MiOS repository has two distinct layers:

1. **Root dotfolders** are the source-control workflow and review control
   plane. They organize prompts, research, documentation, secrets
   boundaries, and generated work without pretending those paths are runtime
   FHS destinations.
2. **FHS directories** (`etc/`, `usr/`, `var/`, `srv/`) are the deployable
   system overlay. They remain authoritative for image contents and runtime
   paths.

| Root path | Purpose | Commit policy | Deploys to |
|---|---|---|---|
| `.mios/` | workflow contract and metadata | tracked | nowhere |
| `.dotfiles/` | bootstrap-owned operator-dotfiles boundary and layout | tracked, no secrets | projected user/host dotfiles |
| `.prompts/` | prompt catalog and contract index | tracked, no secrets | nowhere |
| `.research/` | research evidence and reports | tracked, no secrets | nowhere |
| `.docs/` | documentation and publication manifests | tracked | nowhere |
| `.secrets/` | local secret boundary and placeholders | README only | secret manager or `/etc/mios/secrets.env` |
| `.artifacts/` | generated outputs and validation results | ignored | nowhere |
| `.work/` | disposable agent/build scratch | ignored | nowhere |

Dotfolders do not replace the existing `mios.toml` SSOT, the FHS overlay, or
the `usr/share/mios/prompts/` shipped surface. They provide a visible
repository control plane while generated/runtime paths remain governed by
their existing laws.

## Control-plane rules

- Use `.mios/system-prompt.md` as the formal report system prompt for external
  research and engineering applications.
- Use `.prompts/README.md` as the prompt catalog; shipped prompt contracts
  remain under `usr/share/mios/prompts/`.
- Keep non-secret operator dotfile structure and `secret_ref` references in
  the separate repository described by `.dotfiles/README.md`.
- Keep research evidence in `.research/` and durable documentation in their
  owning documented paths.
- Never put credentials in `.secrets/`; use `[REDACTED]` or
  `<REPLACEMENT_CREDENTIAL>` placeholders.
- Never place generated output, logs, caches, or model artifacts in tracked
  dotfolders.

## Three repositories and secret data

The corrected three-repository model and secret-data pattern are documented in
`.research/separate-dotfiles-secrets-repository-pattern-2026-09.md`:

- `mios.git` owns the immutable system layer.
- `mios-bootstrap.git` owns installation, profiles, and operator dotfiles.
- `mios-dev-loop` is the parallel orchestration repository and is excluded from
  the product merge boundary.
- `.secrets/` is a README-only local boundary in this repository; encrypted
  secret data is operator-controlled bootstrap input, not a fourth MiOS source
  repository.
- Decrypted values exist only at deployment/runtime in the approved protected
  sink, such as `/etc/mios/secrets.env` with mode `0600`, or an OS secret
  manager.

Do not create a fourth MiOS code repository, plaintext `.secrets.git`
repository, or put private identities, tokens, password hashes, or decrypted
archives into this repository.
