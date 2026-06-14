<!-- AI-hint: Documentation for the dnf5 package manager as used at MiOS BUILD time, detailing critical build flags (`install_weak_deps`), BuildKit cache-mount patterns, kernel-package install restrictions, and how the automation/lib/packages.sh helpers feed names from mios.toml to dnf5 during the Containerfile pipeline that produces the immutable OCI image. -->
# dnf5 — The Package Manager Used at MiOS Build Time

## Why this matters to MiOS

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image you `bootc
upgrade` like a `git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a
**local, self-replicating agentic AI OS**. Both halves are baked at build time
by a single `Containerfile` that runs every `automation/[0-9][0-9]-*.sh` script
in numeric order — and the very first thing that pipeline does, before it can
stand up GPUs, VMs, clusters, or the local AI stack, is **lay down packages**.

dnf5 is the package manager that does that laying-down. It runs **only at build
time**, inside the Containerfile's main `RUN`, against the
`ghcr.io/ublue-os/ucore-hci:stable-nvidia` base. A booted MiOS host never runs
`dnf install` to mutate `/usr` (Law 1 / Law 2 — `/usr` is a read-only composefs
mount; changes arrive as a new image, not an in-place transaction). So this doc
is for **image builders and pipeline authors**, not day-2 operators: it records
the dnf5-specific knobs, idioms, and footguns that keep the build deterministic
and the resulting image lint-clean.

> MiOS's `Containerfile` mounts `/var/cache/libdnf5` and `/var/cache/dnf`
> as BuildKit cache mounts and calls
> `${DNF_BIN:-dnf5} clean metadata` (falling back to `dnf`) before
> `install_packages_strict base`.
> Source: `Containerfile` (main `RUN`, ~L53–83);
> `usr/share/doc/mios/guides/engineering.md` §Containerfile conventions.

## Project

- Repo: <https://github.com/rpm-software-management/dnf5>
- Docs: <https://dnf5.readthedocs.io/>
- Status: dnf5 is the C++ rewrite of dnf with a libdnf5 daemon and a
  faster resolver; dnf4 is legacy. MiOS targets dnf5 (`DNF_BIN` defaults to
  `dnf5`) and keeps a `dnf` fallback for early build phases.

## Critical knobs for image builds

| Setting | Value | Why |
| --- | --- | --- |
| `install_weak_deps` | `False` | dnf5 spelling (underscore, capital F). Set **globally** by `automation/01-repos.sh` (sed'd into `dnf.conf`) and re-asserted as `--setopt=install_weak_deps=False` in `automation/lib/common.sh`. `install_weakdeps` (no underscore) is the dnf4 form and is **silently ignored** by dnf5 — this caused real bugs in an earlier KB. Without it, recommends/supplements bloat the image and bypass the curated package set. |
| `keepcache` | `0` (with cache mount) | Avoid baking the package cache into the image layers; the BuildKit cache mount holds it instead (see below). |
| `repo_gpgcheck` / `gpgcheck` | repo-specific | The Fedora 44 repos in `01-repos.sh` ship `repo_gpgcheck=0` with `gpgcheck=1` (per-package signature check on, repo-metadata signature check off). bootc-image-builder ISO depsolve is sensitive to having both `repo_gpgcheck=1` AND `gpgcheck=1` set together — configure carefully. |
| `--skip-unavailable` / `--allowerasing` | per helper | The package helpers pass `--skip-unavailable` (external repos like crowdsec/tailscale aren't configured at every phase) and, for the strict foundation set, `--allowerasing` without `--best` (lets conflict resolution proceed by erasure on the F44↔ucore boundary). |
| `tsflags` | `nodocs` (selective) | Only where MiOS doesn't ship man pages for that package. |

## Cache mount idiom (BuildKit)

The Containerfile's main `RUN` bind-mounts the read-only build context and
mounts both dnf caches, then cleans stale metadata before the strict base
install:

```dockerfile
RUN --mount=type=bind,from=ctx,source=/ctx,target=/ctx,ro \
    --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf,sharing=locked \
    set -ex; \
    # ... set MIOS_TOML, source automation/lib/packages.sh ... \
    ${DNF_BIN:-dnf5} clean metadata 2>/dev/null || ${DNF_BIN:-dnf} clean metadata 2>/dev/null || true; \
    install_packages_strict base
```

Cache mounts are **not** baked into the image (BuildKit mounts them only for the
duration of the `RUN`), so MiOS gets much faster rebuilds without bloating the
OCI layers. The `clean metadata` step purges any stale or corrupt repo metadata
left in the cache mount by a previous failed build (zchunk checksum errors,
partial syncs), which otherwise surfaces as opaque depsolve failures.

This is the build-side counterpart to the bootc lifecycle: the cache makes
**build → image** cheap to iterate, while the image's read-only `/usr` makes
**image → host** atomic and rollback-safe. dnf5 only ever touches the former.

## Kernel rule (re-stated)

Only `kernel-modules-extra`, `kernel-devel`, `kernel-headers`, and
`kernel-tools` may be installed (via the `kernel` package section, applied in
`automation/02-kernel.sh`). **Never** install or upgrade `kernel`,
`kernel-core`, `kernel-modules`, or `kernel-modules-core` — `02-kernel.sh`
explicitly excluded them (CHANGELOG v0.2.0). The base image
(`ucore-hci:stable-nvidia`) owns the kernel and ships a working initramfs;
upgrading it inside the container triggers dracut under the tmpfs mount
(`Invalid cross-device link (os error 18)` → broken initramfs) and desyncs the
running ABI from the akmod-built NVIDIA modules. This is what keeps the GPU
wiring (and therefore both the passthrough VMs and the local inference lanes)
intact across an image build.

## How MiOS calls dnf5 (helpers)

`automation/lib/packages.sh` exposes three wrappers around dnf5 so no pipeline
script ever hard-codes package names or raw `dnf install` flags:

```bash
install_packages "<category>"           # best-effort, --skip-unavailable
install_packages_strict "<category>"    # fails the build on any miss (foundation set)
install_packages_optional "<category>"  # never fails (silent skip)
```

Each helper resolves the package list from the **single source of truth**,
`usr/share/mios/mios.toml`, reading the `pkgs` array of the
`[packages.<category>]` table (e.g. `[packages.base].pkgs`). The layered
override chain applies (highest precedence first): `~/.config/mios/mios.toml`
→ `/etc/mios/mios.toml` → `/ctx/mios-bootstrap/mios.toml` →
`/usr/share/mios/mios.toml` → `/ctx/usr/share/mios/mios.toml` (the build sets
`MIOS_TOML` to the build-context copy). Each section can be toggled off with
`[packages.<category>].enable = false`, which the configurator UI writes and the
helpers honor.

> **Note (drift fixed):** As of 2026-05-05 the legacy `PACKAGES.md`
> fenced-block fallback is **removed** — `mios.toml [packages.*]` is the only
> runtime source the helpers parse. `usr/share/doc/mios/reference/PACKAGES.md`
> is retained as **human-readable rationale documentation**, not machine input.

## Cross-refs

- `usr/share/doc/mios/reference/PACKAGES.md` — human-readable package rationale.
- `usr/share/doc/mios/guides/engineering.md` — §Package management, §Containerfile conventions, §Upstream base image constraints (bootc) (the build-pipeline rules this doc supports).
- `usr/share/mios/mios.toml` — `[packages.<section>].pkgs` (the package SSOT dnf5 is fed from).
- `automation/01-repos.sh`, `automation/02-kernel.sh`, `automation/lib/{packages,common}.sh` — where these knobs are actually set.
