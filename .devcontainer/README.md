# MiOS devcontainer harness — portability contract

The committed `devcontainer.json` is the portable, full-builder baseline. It
installs the MiOS build, test, and container toolchain and provisions the MiOS,
mios-bootstrap, and -dev-loop workspace layout. It must build and pass
`postStartCommand` on any standard Dev Containers host, including GitHub
Codespaces and a bare Linux/macOS/Windows Podman install, with no GPU, no KVM,
and no elevated container privileges.

## Mobile portrait workbench

The Dev Container and its two workspace files default to Dark Modern with a
top Activity Bar, one primary side bar, a full-width bottom panel, horizontal
editor splits, word wrap, and larger editor and terminal text. This preserves
usable vertical space and touch targets in portrait remote sessions. VS Code
does not detect or rotate its layout for device orientation; users can still
override these defaults from the layout controls or their user settings.

## Why there are no `--device` or `--security-opt` entries

An earlier revision hardcoded `--device /dev/kvmfr0:/dev/kvmfr0:rw`,
`--device nvidia.com/gpu=all`, and `--security-opt label=disable` in
`runArgs`. That fails container creation outright on any host without those
exact devices, and disabling SELinux labeling is a privileged default that
should never be silently baked into the FOSS-compatible harness contract.
Those entries were removed. `harness/verification_gates.py` treats hardware
invariants that depend on such devices as `SKIP` (not applicable), never as a
false `PASS`.

## Adding local hardware passthrough (not committed)

If you are running this devcontainer on a MiOS-Metal Blade or another host
with KVM/NVIDIA passthrough available, add the extra `runArgs` in your local,
uncommitted Dev Containers configuration (for example your editor's
per-user `devcontainer.json` override, or a Podman CLI wrapper you keep outside
the repository). Do not reintroduce hardware-specific `runArgs`
into the committed `devcontainer.json`; that regresses portability for every
Codespace and CI runner that builds this harness.
