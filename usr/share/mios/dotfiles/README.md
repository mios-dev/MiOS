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

## VS Code settings: two kinds of surface (ADR-0024)

`vscode/settings.json` is the full desktop profile. `tools/sync-dotfiles.py`
projects it two ways, and `mios.toml [dotfiles.vscode]` is the partition:

| Surface | How the client applies it | Gets |
|---|---|---|
| a settings **file** (`etc/skel/.config/Code/User/settings.json`, the code-server seed, `~/.vscode-server/data/*/settings.json`) | read from disk; an unknown key only warns | the whole profile, byte for byte |
| an **API-applied** block (`devcontainer.json` `customizations.vscode.settings`, the `settings` of a `*.code-workspace`) | written through the configuration API of whichever client connects; an unknown key throws (`... is not a registered configuration`) | only the client-portable subset |

The keys the Electron workbench alone registers (`window.titleBarStyle`,
`window.customTitleBarVisibility`, `window.dialogStyle`, `window.zoomLevel`,
`vscode_custom_css.imports`), the APPLICATION-scoped ones a Workspace target
refuses everywhere, and the ones no client registers any more are listed in
`[dotfiles.vscode]`; the merge prunes them from every API-applied surface and
`--check` (and `check_dotfiles_projection`) goes red, naming file and key, if
one comes back.
