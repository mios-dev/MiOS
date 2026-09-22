# MiOS devcontainer harness — portability contract

The committed `devcontainer.json` is the full MiOS artifact-builder baseline.
It provisions the MiOS, mios-bootstrap, and -dev-loop workspace layout and
uses privileged nested Podman with persistent container storage. It is intended
to run the same upstream `just` workflow that produces MiOS OCI/bootc images,
OCI archives, RAW disks, ISOs, QCOW2, VHDX, WSL exports, and USB installer
images.

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

## Privileged artifact-builder boundary

MiOS disk artifact targets invoke `bootc-image-builder` through nested,
privileged Podman and mount the container image store. The canonical profile
therefore sets `privileged: true` and persists
`/var/lib/containers/storage`; use it only on a trusted builder host. It does
not hardcode GPU, KVM, or host-specific device mappings. Hardware-dependent
checks remain conditional, and artifact builds that need a particular device
must request it explicitly.

## Adding local hardware passthrough (not committed)

If you are running this devcontainer on a MiOS-Metal Blade or another host
with KVM/NVIDIA passthrough available, add the extra `runArgs` in your local,
uncommitted Dev Containers configuration (for example your editor's
per-user `devcontainer.json` override, or a Podman CLI wrapper you keep outside
the repository). Do not add unconditional hardware-specific device mappings to
the committed configuration.
