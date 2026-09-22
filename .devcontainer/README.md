# MiOS devcontainer harness — portability contract

The committed `devcontainer.json` is the portable baseline. It must build and
pass `postStartCommand` on any standard Dev Containers host, including GitHub
Codespaces and a bare Linux/macOS/Windows Docker or Podman install, with no
GPU, no KVM, and no elevated container privileges.

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
per-user `devcontainer.json` override, or a `docker`/`podman` CLI wrapper you
keep outside the repository). Do not reintroduce hardware-specific `runArgs`
into the committed `devcontainer.json`; that regresses portability for every
Codespace and CI runner that builds this harness.
