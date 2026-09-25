# MiOS devcontainer harness — portability contract

The committed `devcontainer.json` is the portable MiOS development baseline.
It provisions the MiOS, mios-bootstrap, and -dev-loop workspace layout and
automatically initializes the development core on every supported Dev
Container connection, including GitHub Codespaces.

## One image, every environment

`Containerfile` is the only MiOS development image definition. The
mios-bootstrap and -dev-loop devcontainers point `build.dockerfile` at
`../../MiOS/.devcontainer/Containerfile` (their `initializeCommand` clones this
repo as a sibling first) and run this directory's lifecycle from
`/workspaces/MiOS`. Codespaces and Cloud Shell (`cloud-shell/bootstrap.sh`) use
the same `devcontainer.json`, and the hosted cloud-session projection
(`-dev-loop` `cloud-fedora-setup.sh`) builds this file unedited and commits its
lifecycle into the image. No other repository keeps a copy. The dnf package set
is `[packages.devcontainer]` in `usr/share/mios/mios.toml`, resolved at build
time by `automation/lib/packages.sh`; change it there, not here. The Antigravity
CLI is baked in, and a build that cannot install it fails instead of shipping
without it.

## Development-safe MiOS core

The image includes rootless Podman/Quadlet networking dependencies and the
agent-pipe runtime at `/usr/lib/mios/agents/.venv`, matching the MiOS service
contract. Post-create applies the complete MiOS root overlay, initializes the
developer's MiOS state directories, and builds both upstream native Rust
workspaces. Their release binaries are available from `/opt/mios/bin`, while
the in-tree release targets remain available to the normal `just` preflight
checks.

Every Dev Container start runs `boot-mios-systems.sh`, which reapplies the
root overlay, incrementally rebuilds the source-matched native components, and
records the active platform contract before the verification gate runs. This
keeps resumed workspaces aligned with the checked-out MiOS system source rather
than relying on one-time creation state. The same boot step re-projects the
`.dotfiles` SSOT into the live editor `Machine/settings.json` so theme and
layout settings never drift, but the edge-to-edge terminal CSS itself
(`vscode_custom_css.imports`) is applied by the `be5invis.vscode-custom-css`
extension, which can only patch a real local workbench install. It is pinned
to run on the connecting client via `remote.extensionKind: {"be5invis.vscode-custom-css": ["ui"]}`;
after every client-side VS Code update, its own upstream docs require
re-running "Enable Custom CSS and JS" once and reloading the window — see
`docs/research/spike-vscode-edge-to-edge-terminal.md` for the full root-cause
trace. This is not automatable from inside the container.

Run `miosd --help` to inspect the native control-plane interface. Run
`mios-agent-pipe-dev` explicitly when developing the API gateway; it uses the
service-compatible runtime and checked-out source. Podman
sidecars, pgvector, inference lanes, systemd units, hardware services, and
host-security services are deliberately not started automatically. They need
host-specific privileges, devices, credentials, or persistent state and remain
explicit developer actions.

## Mobile portrait workbench

The Dev Container and its two workspace files default to Dark Modern with a
top Activity Bar, one primary side bar, a full-width bottom panel, horizontal
editor splits, word wrap, and larger editor and terminal text. This preserves
usable vertical space and touch targets in portrait remote sessions. VS Code
does not detect or rotate its layout for device orientation; users can still
override these defaults from the layout controls or their user settings.

## Platform-aware connection bootstrap

`.devcontainer/platform-bootstrap.sh` records the detected platform and
portable profile in `~/.config/mios/devcontainer.env` during post-create.
GitHub Codespaces runs the Dev Container lifecycle automatically. Google Cloud
Shell can run a persistent `$HOME/.customize_environment` bootstrap at VM
start, while Oracle Cloud Shell retains standard shell initialization in its
persistent home; neither cloud shell automatically applies a repository's
Dev Container configuration by itself.

`.devcontainer/cloud-shell/bootstrap.sh install` installs the portable
Dev Containers launcher once under persistent `$HOME/.local`; use
`mios-cloud-shell up` from a later shell connection to create or update the
portable development environment. See
[Cloud Shell bootstrap](cloud-shell/README.md) for the provider-specific
details.

## Privileged artifact-builder profile

Use `.devcontainer/artifact-builder/devcontainer.json` on a trusted,
self-managed Podman/Docker host to run `just raw`, `just iso`, `just qcow2`,
or `just vhdx`. The profile enables privileged nested Podman and persistent
container storage for `bootc-image-builder`. The portable default supports
development, validation, and OCI workflows but does not claim that restricted
cloud platforms can locally produce privileged disk artifacts.

The privileged profile does not hardcode GPU, KVM, or host-specific device
mappings. Hardware-dependent checks remain conditional, and artifact builds
that need a particular device must request it explicitly.

## Adding local hardware passthrough (not committed)

If you are running this devcontainer on a MiOS-Metal Blade or another host
with KVM/NVIDIA passthrough available, add the extra `runArgs` in your local,
uncommitted Dev Containers configuration (for example your editor's
per-user `devcontainer.json` override, or a Podman CLI wrapper you keep outside
the repository). Do not add unconditional hardware-specific device mappings to
the committed configuration.
