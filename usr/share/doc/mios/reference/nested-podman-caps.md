<!-- AI-hint: Technical reference on nested podman-in-podman container capabilities and security flags. -->
---
title: Nested Podman Capabilities and Security Flags Reference
description: Technical reference on nested podman-in-podman container capabilities, fuse-overlayfs device mounts, and security options for GitHub Actions and Forgejo CI runners.
type: reference
---

# Nested Podman Capabilities & Security Flags Reference

## Overview

When building MiOS container images inside CI/CD environments (such as GitHub Actions or Forgejo), Podman runs inside a nested container environment (podman-in-podman). Building multi-stage images or compiling nested layers requires specific Linux kernel capabilities, device nodes, and seccomp/AppArmor profile overrides.

## Required Flags

Nested `podman build` invocations in unprivileged environments (e.g. GitHub Actions `ubuntu-latest` runners) MUST include the following parameters:

```bash
podman build \
  --device /dev/fuse \
  --cap-add all \
  --security-opt seccomp=unconfined \
  --security-opt apparmor=unconfined \
  ...
```

## Parameter Rationale

1. **`--device /dev/fuse`**:
   Required for `fuse-overlayfs` rootless/nested storage mounts inside unprivileged container layers when kernel overlayfs mounts are restricted.

2. **`--cap-add all` (or `SYS_ADMIN` + `SYS_RESOURCE`)**:
   - `CAP_SYS_ADMIN`: Required to execute inner filesystem mounts (`mount`, `pivot_root`).
   - `CAP_SYS_RESOURCE`: Required by `crun` / `runc` to execute `setrlimit(RLIMIT_NOFILE)` inside nested container stages.

3. **`--security-opt seccomp=unconfined --security-opt apparmor=unconfined`**:
   Prevents host security profiles from blocking inner system calls (such as `unshare`, `clone`, `mount`, and `pivot_root`) executed by inner build processes.

## CI Environment Parity

- **GitHub Actions (`mios-ci.yml`)**:
  GitHub Actions runners execute unprivileged. Explicit `--device /dev/fuse`, `--cap-add`, and `--security-opt` flags MUST be provided on every `podman build` step.

- **Forgejo Runners (`.forgejo/workflows/`)**:
  Forgejo self-hosted runners operate with `Privileged=true` by default, which masks missing cap flags. The explicit flags guarantee build portability across both platforms.

## Monitored Invocations

The following files are drift-checked by `automation/38-drift-checks.sh` (check 65):
- [.github/workflows/mios-ci.yml](file:///C:/MiOS/.github/workflows/mios-ci.yml)
- [usr/libexec/mios/57-mios-sys-build.sh](file:///C:/MiOS/usr/libexec/mios/57-mios-sys-build.sh)
