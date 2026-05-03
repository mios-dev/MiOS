# Build Pipeline -- Containerfile + automation/

> Source: `Containerfile`, `automation/build.sh`, `ENGINEERING.md` §Phase-2,
> `ENGINEERING.md` §Containerfile-conventions.

## Containerfile shape (single-stage + ctx scratch)

The `Containerfile` is **single-stage** with a `ctx` scratch context
stage. The v1 KB's "multi-stage base→overlay→packages→finalize" was a
fabrication.

```dockerfile
# syntax=docker/dockerfile:1.9
ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia

FROM scratch AS ctx
COPY automation/ /ctx/automation/
COPY usr/        /ctx/usr/
COPY etc/        /ctx/etc/
COPY usr/share/mios/PACKAGES.md /ctx/PACKAGES.md
COPY VERSION                    /ctx/VERSION
COPY config/artifacts/          /ctx/bib-configs/
COPY tools/                     /ctx/tools/

FROM ${BASE_IMAGE}
LABEL org.opencontainers.image.title="'MiOS'" \
      org.opencontainers.image.source="https://github.com/mios-dev/'MiOS'" \
      org.opencontainers.image.version="v0.2.2" \
      containers.bootc="1" \
      ostree.bootable="1"
CMD ["/sbin/init"]

ARG MIOS_USER=mios
ARG MIOS_HOSTNAME=mios
ARG MIOS_FLATPAKS=

RUN --mount=type=bind,from=ctx,source=/ctx,target=/ctx,ro \
    --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf,sharing=locked \
    set -ex; \
    install -d -m 0755 /tmp/build; \
    cp -a /ctx/automation /ctx/usr /ctx/etc /ctx/PACKAGES.md /ctx/VERSION \
          /ctx/bib-configs /ctx/tools /tmp/build/; \
    export PACKAGES_MD=/tmp/build/PACKAGES.md; \
    source /tmp/build/automation/lib/packages.sh; \
    ${DNF_BIN:-dnf5} clean metadata 2>/dev/null || true; \
    install_packages_strict base; \
    if [[ -n "${MIOS_FLATPAKS}" ]]; then \
      echo "${MIOS_FLATPAKS}" | tr "," "\n" > /tmp/build/usr/share/mios/flatpak-list; \
    fi; \
    bash /tmp/build/automation/08-system-files-overlay.sh; \
    CTX=/tmp/build /tmp/build/automation/build.sh; \
    dnf clean all; \
    rm -rf /tmp/build; \
    find /var -mindepth 1 -maxdepth 1 ! -name tmp ! -name cache -exec rm -rf {} +; \
    find /run -mindepth 1 -maxdepth 1 ! -name secrets -exec rm -rf {} + 2>/dev/null || true

RUN bootc completion bash > /etc/bash_completion.d/bootc

RUN --mount=type=bind,from=ctx,source=/ctx/tools,target=/ctx/tools,ro \
    install -d -m 0755 /usr/lib/extensions/source && \
    bash /ctx/tools/mios-sysext-pack.sh /usr/lib/extensions/source || true

RUN ostree container commit
RUN bootc container lint   # ARCHITECTURAL LAW 4 -- must be the final RUN
```

## Pipeline phases (sub-phases of Phase-2)

The `Containerfile` triggers `automation/build.sh`, which iterates every
`automation/[0-9][0-9]-*.sh` script in numeric order. **~48 phase scripts**
exist (not 01-39 as v1 claimed). Notable ones:

| Phase | Purpose |
| --- | --- |
| `01-repos.sh` | Configure dnf repos. **Excludes `kernel`/`kernel-core` from upgrades** (lines 65, 68). |
| `08-system-files-overlay.sh` | Apply the FHS overlay onto `/`. **Runs pre-pipeline from `Containerfile`**, so `build.sh` skips it. Includes the BOUND-IMAGES binder loop at lines 74-86 (LAW 3). Writes home dotfiles to `/etc/skel/`. |
| `12-virt.sh` | Configure virtualization. Disables CrowdSec `online_client` at lines 42-50 -- `/etc/crowdsec/config.yaml` is an upstream-contract `/etc/` location with no `/usr/lib` drop-in. |
| `19-k3s-selinux.sh` | Ship custom SELinux modules to `usr/share/selinux/packages/mios/`. Compiled but not auto-loaded. |
| `33-firewall.sh` | firewalld default-deny zone=drop; allow cockpit/9090, ssh/22, libvirt bridge, CrowdSec nftables bouncer. |
| `34-gpu-detect.sh` | Detect GPUs at runtime; write `/run/mios/gpu-passthrough.status`. |
| `37-ollama-prep.sh` | **CI-skipped** (large-model warmup not viable in CI runner). |
| `37-selinux.sh` | Declare `semanage` booleans (`container_use_cephfs`, `virt_use_samba`) and fcontexts. |
| `52-bake-kvmfr.sh` | Build KVMFR shared-memory module. |
| `53-bake-lookingglass-client.sh` | Build Looking Glass B7 client. |
| `90-generate-sbom.sh` | Run syft to emit a CycloneDX SBOM. |

`automation/build.sh` wraps each script in `set +e` (lines 234-237) so
individual failures are captured in `FAIL_LOG`/`WARN_LOG` rather than
aborting the orchestrator. Critical packages from the
` ```packages-critical` block in `usr/share/mios/PACKAGES.md` are
post-validated via `rpm -q` (lines 285-300).

## Build invariants enforced in CI

- `set -euo pipefail` at the top of every phase script.
- `VAR=$((VAR + 1))` only -- `((VAR++))` is forbidden because under
  `set -e` it exits 1 when the result is 0, silently killing the script.
- shellcheck-clean; **SC2038 fatal**.
- File names: `NN-name.sh` where `NN` encodes execution order.
- `Containerfile` final RUN is `bootc container lint` (LAW 4).
- No `--squash-all` on `podman build` -- strips OCI metadata bootc needs
  for client-side delta updates.
- Kernel rule: only `kernel-modules-extra`, `kernel-devel`,
  `kernel-headers`, `kernel-tools`. Never `kernel`/`kernel-core`.
- `dnf install_weak_deps=False` (underscore -- dnf5 spelling).
  `install_weakdeps` (no underscore, dnf4) is silently ignored by dnf5.

## What `bootc container lint` enforces (final RUN)

- Kernel present at `/usr/lib/modules/<kver>/vmlinuz`
- No files written under `/var` or `/run` in image layers
- `/usr` structurally valid (no dangling symlinks, no unexpected setuid)
- OCI config has `architecture` and `os` set
- `/sbin/init` is systemd PID 1
- `kargs.d` files use the flat `kargs = [...]` format only
