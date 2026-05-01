# MiOS Engineering Standards

## Global pipeline phases

The end-to-end pipeline (bootstrap → install) is partitioned into five
phases. The numbered `automation/[0-9][0-9]-*.sh` scripts are *sub-phases*
of Phase-2 (build).

| Phase | Owner | Description |
|---|---|---|
| Phase-0 | `mios-bootstrap.git/install.sh` | Preflight + profile load + identity capture |
| Phase-1 | `mios-bootstrap.git/install.sh` | Total Root Merge of `mios.git` and `mios-bootstrap.git` to `/` |
| Phase-2 | `Containerfile`/`automation/build.sh` | Build the running system (this section's subject) |
| Phase-3 | `mios.git/install.sh` + bootstrap profile staging | systemd-sysusers/tmpfiles/daemon-reload + user create + per-user `~/.config/mios/{profile.toml,system-prompt.md}` |
| Phase-4 | `mios-bootstrap.git/install.sh` | Reboot prompt |

## Phase-2: build pipeline (sub-phases)

`Containerfile` triggers `automation/build.sh`, which iterates every
`automation/[0-9][0-9]-*.sh` in numeric order. Skipped under build:
`08-system-files-overlay.sh` (runs pre-pipeline from `Containerfile`),
`37-ollama-prep.sh` (CI-skipped). Sub-phase numbering encodes dependency
order and must be preserved when adding new scripts. See `CLAUDE.md` for
the sub-phase ranges.

Per-phase error handling: `automation/build.sh:234-237` toggles `set +e`
around each script invocation so individual failures are captured in
`FAIL_LOG`/`WARN_LOG` instead of aborting the orchestrator. Critical
packages declared in `usr/share/mios/PACKAGES.md` `packages-critical` are
post-validated via `rpm -q` (`automation/build.sh:285-300`).

## Package management

Single source of truth: `usr/share/mios/PACKAGES.md`. Every RPM installed
into the image must live in a fenced `packages-<category>` block, parsed
by `automation/lib/packages.sh:get_packages` (regex
`/^\`\`\`packages-${category}$/,/^\`\`\`$/`). Helpers:

- `install_packages "<category>"` — best-effort, `--skip-unavailable`.
- `install_packages_strict "<category>"` — fails the script on any miss.
- `install_packages_optional "<category>"` — pure best-effort, never fails.

The `Containerfile` pre-pipeline `RUN` installs `packages-base`
(security stack) before `automation/build.sh` runs.

## Shell conventions

- `set -euo pipefail` at the top of every phase script.
- `VAR=$((VAR + 1))` for arithmetic. `((VAR++))` is forbidden — under
  `set -e` it exits 1 when the result is 0.
- shellcheck-clean. SC2038 is fatal in CI (`.github/workflows/mios-ci.yml`).
- File names: `NN-name.sh` where NN encodes execution order.

## Containerfile conventions

- `ctx` stage holds the build context; the main stage bind-mounts `/ctx`
  read-only and writes mutable copies to `/tmp/build` (`Containerfile`).
- Final `RUN bootc container lint` (LAW 4).
- No `--squash-all` — strips OCI metadata bootc needs.
- Kernel rule: only add `kernel-modules-extra`, `kernel-devel`,
  `kernel-headers`, `kernel-tools`. Never upgrade `kernel`/`kernel-core`
  in-container — `automation/01-repos.sh:65,68` excludes them explicitly.
- dnf option: `install_weak_deps=False` (underscore). `install_weakdeps`
  is silently ignored by dnf5.

## Kargs format

`usr/lib/bootc/kargs.d/*.toml` uses a flat top-level array:

```toml
kargs = ["init_on_alloc=1", "lockdown=integrity"]
```

No `[kargs]` section header. No `delete` sub-key. bootc rejects anything
else (<https://bootc-dev.github.io/bootc/man/bootc-edit.html>).

## SELinux

Custom policies are split into per-rule `.te` modules in
`usr/share/selinux/packages/mios/` (compiled and shipped, not loaded at
build time — see `automation/19-k3s-selinux.sh:46-51`). New booleans and
fcontexts are declared via `semanage` calls in `automation/37-selinux.sh`.

## Service gating

- Bare-metal-only services: `ConditionVirtualization=no` drop-in.
- WSL2-incompatible services: `ConditionVirtualization=!wsl`.
- Optional services: `systemctl enable ... || true`.

## AI integration patterns

- All system agents target the OpenAI v1 protocol at
  `http://localhost:8080/v1` (LAW 5). Vendor-hardcoded URLs are forbidden.
- Episodic journal: `/usr/share/mios/memory/v1.jsonl` seeded into
  `/var/lib/mios/memory/journal/` via `usr/lib/tmpfiles.d/mios.conf`.
- Declarative state: `tmpfiles.d` and `sysusers.d` only.

## Toolchain

| Tool | Use |
|---|---|
| `bootc` | Transactional system upgrade/rollback |
| `podman` | Quadlet sidecar orchestration |
| `bootc-image-builder` (BIB) | RAW/ISO/QCOW2/VHD/WSL2 disk images |
| `syft` | CycloneDX/SPDX SBOM (`automation/90-generate-sbom.sh`) |
| `cosign` | Keyless image signing in CI |
| `just` | Linux build orchestrator (`Justfile`) |
