# dnf5 — The Package Manager Used at Build Time

> MiOS's `Containerfile` mounts `/var/cache/libdnf5` and `/var/cache/dnf`
> as buildkit cache mounts and calls `${DNF_BIN:-dnf5} clean metadata`
> before `install_packages_strict base`.
> Source: `Containerfile`, `ENGINEERING.md` §Containerfile-conventions.

## Project

- Repo: <https://github.com/rpm-software-management/dnf5>
- Docs: <https://dnf5.readthedocs.io/>
- Status: dnf5 is the C++ rewrite of dnf with a libdnf5 daemon and a
  faster resolver; dnf4 is legacy.

## Critical knobs for image builds

| Setting | Value | Why |
| --- | --- | --- |
| `install_weak_deps` | `False` | dnf5 spelling (underscore). `install_weakdeps` (no underscore) is the dnf4 form and is **silently ignored** by dnf5 — this caused real bugs in the v1 KB. |
| `keepcache` | `0` (with cache mount) | Avoid baking the package cache into the image |
| `repo_gpgcheck` | `True` (set in `automation/01-repos.sh`) | bootc-image-builder ISO depsolve fails with `repo_gpgcheck=1` AND `gpgcheck=1` not both set; configure carefully |
| `tsflags` | `nodocs` (selective) | Only where 'MiOS' doesn't ship man pages for that package |

## Cache mount idiom (buildkit)

```dockerfile
RUN --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf,sharing=locked \
    set -ex; \
    dnf5 clean metadata; \
    install_packages_strict base
```

Cache mounts are **not** baked into the image (BuildKit mounts them
only for the duration of the RUN), so 'MiOS' gets 5–10× faster rebuilds
without bloating the OCI layers.

## Kernel rule (re-stated)

Only `kernel-modules-extra`, `kernel-devel`, `kernel-headers`,
`kernel-tools` may be installed. Never `kernel` or `kernel-core` —
`automation/01-repos.sh:65,68` excludes them. The base image
(`ucore-hci:stable-nvidia`) owns the kernel; upgrading it desyncs the
running ABI from akmod-built NVIDIA modules.

## How 'MiOS' calls dnf5 (helpers)

`automation/lib/packages.sh` exposes:

```bash
install_packages "<category>"           # best-effort, --skip-unavailable
install_packages_strict "<category>"    # fails the script on any miss
install_packages_optional "<category>"  # never fails
```

Each helper parses `usr/share/mios/PACKAGES.md` for a fenced
` ```packages-<category>` block and feeds the names to dnf5.

## Cross-refs

- `usr/share/doc/mios/20-packages-md.md`
- `usr/share/doc/mios/10-build-pipeline.md`
- `ENGINEERING.md` §Package-management
