# MiOS devcontainer harness — portability contract

The committed `devcontainer.json` is the portable MiOS development baseline.
It provisions the MiOS, mios-bootstrap, and -dev-loop workspace layout and
automatically initializes the development core on every supported Dev
Container connection, including GitHub Codespaces.

## Development-safe MiOS core

The image includes rootless Podman/Quadlet networking dependencies and the
agent-pipe runtime at `/usr/lib/mios/agents/.venv`, matching the MiOS service
contract. Post-create applies the complete MiOS root overlay, initializes the
developer's MiOS state directories, and builds both upstream native Rust
workspaces. Their release binaries are available from `/opt/mios/bin`, while
the in-tree release targets remain available to the normal `just` preflight
checks.

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
