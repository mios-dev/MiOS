<!-- AI-hint: The three MiOS engineering repositories (MiOS, mios-bootstrap, mios-dev-loop), what each owns, and how they merge or stay separate. -->
# MiOS three-repository topology

MiOS has three overall engineering repositories:

| Repository | Role | Merge relationship |
|---|---|---|
| `mios-dev/MiOS` (`mios.git`) | System image, FHS overlay, build pipeline, runtime AI plane | Product system source |
| `mios-dev/mios-bootstrap` (`mios-bootstrap.git`) | Installer, user profile layer, operator dotfiles, configuration capture | Merges/overlays with `mios.git` |
| `mios-dev/mios-dev-loop` (`-dev-loop`) | Parallel agent orchestration, worktrees, concurrency, verification | Developed alongside both; never folded into product image repos |

## Ownership

`mios.git` owns what the image is. `mios-bootstrap.git` owns how an operator
gets onto the image and which non-secret user/host choices are captured.
`mios-dev-loop` owns how parallel engineering work is scheduled and verified.

The bootstrap repository is the canonical home for operator dotfiles and
profile templates. There is no separate `mios-dotfiles` repository in the
MiOS topology.

Encrypted secrets are deployment data, not a fourth MiOS engineering
repository. They may be stored in an operator-controlled encrypted Git
repository, archive, or platform secret manager and consumed by bootstrap.
Private identities and decrypted values never enter either product repository
or the dev-loop repository.

## Boundary rules

- Never double-track system-owned files in bootstrap.
- Never put installer/user-overlay files into the immutable system layer.
- Never merge dev-loop orchestration code into the product repositories merely
  to make the workflows appear unified.
- Keep `secret_ref` names and policy in bootstrap; keep secret values outside
  source repositories.
- Keep runtime secret sinks protected and ephemeral where possible.
