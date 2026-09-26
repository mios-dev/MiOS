<!-- AI-hint: The only tracked file in .secrets/: documents the local encrypted-secret boundary consumed by mios-bootstrap; everything else here is ignored. -->
# Local secret boundary

This directory is intentionally tracked only through this README. Its
contents are ignored and must remain local.

It represents the local boundary for encrypted operator input consumed by
`mios-bootstrap.git`; it is not a fourth MiOS repository and must not become a
nested Git checkout committed into `mios.git`.

## Expected encrypted repository shape

```text
operator-secret-input/
├── README.md
├── .sops.yaml
├── recipients/
│   └── operators.txt
├── encrypted/
│   ├── common.env.sops
│   ├── linux.env.sops
│   ├── windows.env.sops
│   └── hosts/
└── rotation/
    └── README.md
```

Only encrypted payloads, public recipient identifiers, and non-sensitive
rotation metadata belong in that repository. Age identity files, KMS
credentials, plaintext `.env` files, decrypted archives, and logs remain
outside Git.

Do not commit credentials, tokens, private keys, password hashes, or exported
environment files here. Use `[REDACTED]` or
`<REPLACEMENT_CREDENTIAL>` in research and examples. Runtime secrets belong
in the repository-approved secret manager or protected
`/etc/mios/secrets.env` with the required permissions.

An empty `.secrets/` directory is not an authentication mechanism. Local
loopback is not a sufficient multi-user security boundary.

## Mobile-shell transport for `mios-dev/.secrets.git`

`github.com/mios-dev/.secrets.git` is an operator-controlled private
repository for encrypted secret payloads. It is a transport source, not a
runtime secret store and not a fourth MiOS code repository.

Use separate trust paths for transport, decryption, and application use:

- A mobile shell such as Blink may authenticate SSH with an iOS
  Keychain/Secure Enclave-backed key. Prefer a dedicated, least-privilege
  key and the integrated SSH agent; never export the private key to a
  Codespace or remote host.
- GitHub access should use a dedicated read-only deploy key, a narrowly scoped
  short-lived credential, or SSH-agent forwarding. Agent forwarding provides
  signing capability, not a copy of the private key, but remote processes can
  still request signatures.
- `.secrets.git` should contain only SOPS/age ciphertext, public recipient
  identifiers, non-secret manifests, and rotation metadata. It must not
  contain plaintext `.env` files, age identities, private keys, OAuth caches,
  shell history, decrypted archives, or runtime logs.
- Decrypt only the required entry, as late as possible, into a protected
  pipe, tmpfs, or `0600` runtime sink. Pass values only to the child process
  that needs them, then remove temporary material and unset shell variables.
- Never place decrypted values in `/workspaces`, a Git worktree, an image
  layer, `devcontainer.json`, Dockerfile `ENV`, command arguments, shell
  startup files, logs, generated manifests, or world-readable
  `/etc/mios/install.env`.

The transport flow is:

```text
Blink Shell
  -> SSH to the Codespace or MiOS remote shell
  -> read-only access to mios-dev/.secrets.git
  -> decrypt one encrypted entry with an external age/SOPS identity
  -> protected one-shot runtime handoff
  -> target process
```

Codespaces secrets can provide the GitHub transport credential, but they remain
readable by trusted processes in the Codespace. Treat the repository,
devcontainer lifecycle scripts, extensions, and dependencies as trusted before
granting access. Rotate or revoke GitHub credentials and encryption identities
independently, and diagnose all stages by checking names, permissions, and
metadata only—never by printing secret values.

The MiOS contract is therefore: source code carries policy and stable
`secret_ref` names; `.secrets.git` carries encrypted operator data; the
runtime source supplies decryption capability; and the target process receives
only the required plaintext for the shortest possible lifetime.
