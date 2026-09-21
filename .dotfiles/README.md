# MiOS operator dotfiles boundary

`.dotfiles/` is the root-level control-plane boundary for the
`mios-bootstrap.git` operator/user overlay. It is not a fourth repository, not
the runtime home directory, and not a replacement for `mios.toml`.

## Three-repository model

| Repository | Owns | Secret policy |
|---|---|---|
| `mios-dev/MiOS` (`mios.git`) | immutable system overlay, generators, validators, shipped defaults | no operator secrets |
| `mios-dev/mios-bootstrap` (`mios-bootstrap.git`) | installer, user-editable overlay, profiles, dotfiles, `secret_ref` references | no plaintext runtime secrets |
| `mios-dev/mios-dev-loop` (`-dev-loop`) | parallel orchestration, worktrees, agent lanes, verification | no system/runtime secrets |

These are the three MiOS engineering repositories. The dev-loop repository is
developed in parallel and is not merged into either product repository.
Encrypted secret material is an operator-controlled data source associated
with bootstrap, not a fourth MiOS source repository.

## Bootstrap-owned dotfiles shape

```text
mios-bootstrap/
├── mios.toml
├── profile/
├── etc/skel/.config/mios/
├── etc/
├── usr/
└── .dotfiles/
```

The bootstrap repository owns the operator-facing dotfile/profile layer and
may carry stable `secret_ref` names and policy metadata. It must not contain
credential values, private keys, tokens, or provider access details that
disclose a secret.

The layer is projected through the MiOS dotfile renderer and layered
`mios.toml` resolver during the bootstrap merge. Render-and-copy with drift
checks is the contract; symlink farms are not.
