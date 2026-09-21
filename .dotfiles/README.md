# MiOS operator dotfiles boundary

`.dotfiles/` is the root-level control-plane boundary for the separate
operator dotfiles repository. It is not the runtime home directory and is not
a replacement for `mios.toml`.

## Repository model

| Repository | Owns | Secret policy |
|---|---|---|
| `mios-dev/MiOS` | immutable system overlay, generators, validators, shipped defaults | no operator secrets |
| `mios-dev/mios-dotfiles` | non-secret operator preferences and `secret_ref` references | plaintext only when intentionally non-secret |
| `mios-dev/mios-secrets` | encrypted secret payloads and public recipient metadata | ciphertext only |

The external repositories are separate from this checkout. A deployment may
materialize them under a protected workspace, but this repository must not
vendor either checkout or record a machine-specific absolute path.

## Expected non-secret dotfiles repository shape

```text
mios-dotfiles/
├── README.md
├── manifest.toml
├── profiles/
│   ├── common.toml
│   ├── linux.toml
│   ├── macos.toml
│   └── windows.toml
├── surfaces/
│   ├── shell/
│   ├── editor/
│   ├── git/
│   └── ssh/
└── references/
    └── secrets.toml
```

`references/secrets.toml` may contain stable `secret_ref` names and policy
metadata only. It must not contain credential values, private keys, tokens,
or provider access details that disclose a secret.

The repository is projected through the MiOS dotfile renderer and the layered
`mios.toml` resolver. Render-and-copy with drift checks is the contract;
symlink farms are not.
