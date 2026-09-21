# Separate dotfiles and secrets repositories — upstream pattern research

**Run date:** 2026-09-21
**Scope:** MiOS root dotfolder workflow, operator dotfiles, credentials,
machine bootstrap, and cross-platform projection

## Decision summary

MiOS should use a split repository model:

| Surface | Recommended repository | Contents | Plaintext allowed? |
|---|---|---|---|
| System source | `mios-dev/MiOS` | Immutable FHS overlay, shipped prompts, generators, SSOT defaults | Only non-secret defaults |
| Operator dotfiles | `mios-dev/mios-dotfiles` or a private operator-owned equivalent | User preferences and non-secret projected dotfiles | Yes, if intentionally non-secret |
| Operator secrets | `mios-dev/mios-secrets` | SOPS-encrypted files using age or an approved KMS recipient | No |
| Local checkout boundary | `.secrets/` | Encrypted checkout metadata and ignored local material | Never commit plaintext |
| Runtime secret sink | `/etc/mios/secrets.env` or an OS secret manager | Decrypted, permission-protected runtime values | Only at runtime, mode `0600` |

The requested name `.secrets.git` is not recommended as the repository name.
Use a normal repository name such as `mios-secrets`, with the local root
checkout or mount represented by `.secrets/`. The `.git` suffix describes a
repository implementation detail, not a useful identity for the secret
service.

## Verified upstream patterns

| Pattern | Evidence | MiOS interpretation |
|---|---|---|
| Encrypted files can be versioned in Git while keys remain outside Git | SOPS documents encrypted YAML, JSON, ENV, INI, and binary files with age, PGP, and cloud KMS backends: <https://github.com/getsops/sops#readme> | `mios-secrets` may be Git-backed, but only ciphertext and non-secret policy metadata are committed |
| age uses explicit recipients and supports multiple recipients | age documents `-r/--recipient`, recipient files, multiple recipients, and separate identity files: <https://github.com/FiloSottile/age#readme> | Encrypt for the operator recovery key plus approved machine/deployment recipients; never commit identity files |
| A public dotfiles repository can fetch secrets from a password manager at apply time | chezmoi documents password-manager template functions that insert values during application: <https://www.chezmoi.io/user-guide/password-managers/> | Non-secret dotfiles can remain separate from credentials; MiOS should prefer its existing secret resolver rather than embedding provider-specific functions |
| Encrypted dotfile archives still benefit from a private repository | yadm explicitly recommends a private repository for confidential files even when encrypted: <https://yadm.io/docs/encryption> | Repository access control is defense in depth; encryption is not a reason to make a secret repository public |
| Symlink farms are not the right ownership model for MiOS projections | ADR-0010 rejects GNU Stow and chooses render-and-copy with drift gates | Project decrypted/merged bytes through the existing MiOS dotfile renderer; do not make `.secrets/` a symlink source |

## Repository boundaries

### `mios.git`

Owns the system image and its non-secret contract:

- `usr/share/mios/mios.toml` defaults and `dotfiles.registry`;
- prompt templates and deployed research prompts;
- renderers, validators, drift checks, and secret-reference resolution;
- documentation of the contract.

It must not contain operator tokens, private keys, password hashes, decrypted
secret fixtures, or a live checkout of `mios-secrets`.

### `mios-dotfiles.git`

Should contain operator-owned, non-secret configuration such as:

- shell aliases and prompt/theme preferences;
- editor settings that do not contain credentials;
- non-secret Git preferences;
- host/profile labels and projection metadata;
- encrypted references such as `secret_ref = "mios/ssh/github"` without the
  referenced value.

It may be public or private according to operator privacy needs. Privacy is
not a substitute for encryption when a value is a credential.

### `mios-secrets.git`

Should contain only encrypted payloads and safe metadata:

- SOPS-encrypted TOML, YAML, JSON, ENV, or binary files;
- `.sops.yaml` creation rules without private identities;
- age recipient public keys;
- rotation and recovery documentation containing placeholders;
- checksums or version metadata that do not reveal secret values.

It must not contain age identity files, KMS credentials, plaintext `.env`
files, decrypted archives, shell histories, or runtime logs. Access should be
private, least-privilege, audited, and separately revocable from the system
repository.

## Recommended flow

1. The operator edits non-secret choices through the MiOS configurator or
   `mios-dotfiles` source.
2. A dotfile surface references a secret by stable `secret_ref`, never by
   value.
3. A deployment-specific resolver obtains the encrypted `mios-secrets`
   checkout or archive.
4. SOPS/age decrypts only the required item into a protected temporary or
   runtime sink.
5. MiOS projects the resulting configuration through the existing
   `mios-dotfiles-render`/`mios-theme-render` contract.
6. The secret is removed from temporary material and never written to
   generated research, logs, prompts, shell startup files, or the public
   repository.

For a local interactive command, prefer an OS secret store or a protected
one-shot process environment. For boot services, prefer a native secret
manager or a `0600` `/etc/mios/secrets.env` generated at provisioning time.
The repository should carry the reference and policy, not the decrypted value.

## MiOS-specific constraints

- `mios.toml` remains the singular SSOT for names, references, policy, and
  projection metadata; it does not become a secret database.
- `secret_ref` is an indirection key, not a URL, token, filename containing a
  token, or shell expression.
- The resolver must fail explicitly when a required reference is absent or
  cannot be decrypted; it must not substitute an empty success-shaped value.
- A missing secrets repository should degrade only where the consuming
  feature is optional. Required boot credentials must fail before activation,
  with a redacted diagnostic.
- Rotation is a repository/key-management operation: revoke the old recipient
  or credential, issue the replacement, re-encrypt affected files, verify
  deployment, then remove stale plaintext and old encrypted generations where
  policy requires.
- Loopback endpoints and private Git hosting reduce exposure but do not
  replace encryption or local access control.

## Recommended next implementation boundary

No secret-repository implementation should be added to the image until the
resolver contract is specified and tested. The next narrowly scoped change
would be:

- document `[dotfiles.registry.*].secret_ref` semantics in the SSOT;
- add a validator that rejects inline secret-looking values and unresolved
  references;
- add a deployment adapter that reads from an operator-selected secret
  source, without naming a cloud provider in MiOS artifacts;
- add redacted positive/negative tests for projection and rotation failure.

This research does **not** authorize creating `mios-secrets.git`, generating
keys, cloning a private repository, or decrypting any material.

## Unknowns

- Which Git forge is the operator's authoritative private publisher:
  GitHub, Forgejo, or another local forge?
- Which recipient authority is required for multi-Blade recovery: operator
  age key, TPM-bound identity, hardware token, or an external KMS?
- Which secrets are host-scoped, user-scoped, Blade-scoped, or fleet-scoped?
- Should the first implementation support SOPS/age only, or also a native
  platform secret manager adapter?
