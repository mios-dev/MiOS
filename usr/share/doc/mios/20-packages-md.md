# PACKAGES.md — Single Source of Truth

> Source: `ENGINEERING.md` §Package-management,
> `automation/lib/packages.sh:get_packages`.

`usr/share/mios/PACKAGES.md` (NOT repo root) is the SSOT for every RPM
installed into the MiOS image. The format is **fenced markdown blocks**,
not a table. Each category lives in a fenced ` ```packages-<category>`
block:

````markdown
```packages-base
podman
buildah
skopeo
bootc
bootc-image-builder
syft
cosign
just
# ... one package per line, comments with #
```

```packages-critical
systemd
selinux-policy-targeted
firewalld
fapolicyd
```

```packages-self-build
podman
buildah
bootc
bootc-image-builder
just
git
```
````

## Parser

`automation/lib/packages.sh:get_packages` extracts a category with regex:

```bash
get_packages() {
  local category="$1"
  awk "/^\`\`\`packages-${category}\$/,/^\`\`\`\$/" "${PACKAGES_MD}" \
    | grep -vE '^(\`\`\`|#|$)' | grep -v '^[[:space:]]*$'
}
```

## Helpers

| Helper | Behavior |
| --- | --- |
| `install_packages "<category>"` | Best-effort: `dnf5 install --skip-unavailable`. Logs misses but continues. |
| `install_packages_strict "<category>"` | Fails the script on any miss. Used for `base`. |
| `install_packages_optional "<category>"` | Pure best-effort, never fails. |

## Where each category is consumed

| Category | Consumer | Notes |
| --- | --- | --- |
| `base` | `Containerfile` pre-pipeline RUN, before `automation/build.sh` | The only category installed strictly. |
| `critical` | Post-build validation in `automation/build.sh:285-300` via `rpm -q`. | If any package in `critical` is missing from the final image, the build fails. |
| `self-build` | Ensures the deployed image contains every tool needed to build the next image (Mode-4 self-build). | `podman`, `buildah`, `bootc`, `bootc-image-builder`, `just`, `git`. |
| `desktop` | GNOME 50 + xdg-desktop-portal + supporting packages. | |
| `nvidia` | NVIDIA-specific user-space (drivers come from the base image). | `nvidia-container-toolkit`, `nvtop`, etc. |
| `k3s` | k3s and supporting tools. | |
| `ceph` | Ceph client + cephadm. | |
| `ai` | LocalAI runtime deps. | |
| `gpu` | CDI tooling for AMD/Intel/NVIDIA. | |
| `virt` | libvirt/QEMU/virtiofs/Looking-Glass build deps. | |

## Rules

- Adding a package → add it to the appropriate fenced block. **Do not
  install packages from inside phase scripts that are not declared in
  PACKAGES.md.** CI cross-references the two.
- Removing a package → delete from the block. Pure build-up only — `dnf
  remove` is forbidden in the build pipeline (use `NoDisplay=true` or
  `install_weak_deps=False` to suppress unwanted noise instead).
- The build pipeline is **strictly additive** on the base image. Anything
  the base ships that you don't want must be hidden, masked, or filtered —
  not removed.

## Querying

The `packages_md_query` function tool (defined in
`/usr/lib/mios/tools/responses-api/packages_md_query.json`) exposes this
SSOT to LLMs: given a `package_name` and optional `stage`, it returns
whether the package is included, in which fenced block, and the build
script that installs it.
