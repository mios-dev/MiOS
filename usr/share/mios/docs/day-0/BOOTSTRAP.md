<!-- AI-hint: Documentation for the Day-0 bootstrap process — how the minimal `mios-bootstrap` repo materializes the first MiOS-DEV build environment from a bare host, where it sits in the build pipeline (Phase-0/1, the Total Root Merge, hand-off to the MiOS repo's Justfile + mios-build-driver), and why it is a separate repo. Use this to understand the entry point of the build pipeline → OCI image → bootc lifecycle.
     AI-related: /usr/share/mios/docs/day-0/BOOTSTRAP.md, /usr/share/mios/docs/day-0/FIRST-BOOT.md, mios-bootstrap, mios-dev, mios-build-driver, ghcr.io/ublue-os/ucore-hci -->
<!-- FHS: /usr/share/mios/docs/day-0/BOOTSTRAP.md -->

# Day-0: Bootstrap from `mios-bootstrap`

## Purpose

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is
*also* a **local, self-replicating, agentic AI operating system**. The same image
ships GNOME/Wayland, GPU wiring via CDI, KVM/libvirt passthrough, and a k3s+Ceph
cluster path *and* a full local agent stack behind one OpenAI-compatible endpoint.

That self-replicating property has to start somewhere. **Day-0 is where a bare
host becomes a machine that can build MiOS.** `mios-bootstrap` is the minimal
repository that materializes the first **MiOS-DEV** environment — the seed build
environment from which every subsequent "next MiOS" OCI image is produced.

This document covers the bootstrap repo's role and mechanics. Its sibling,
[`FIRST-BOOT.md`](FIRST-BOOT.md), covers what happens the first time MiOS-DEV
boots; together they are Day-0 of the lifecycle whose later stages
(**build pipeline → OCI image → `bootc` lifecycle on the host**) are described in
[`../../doc/mios/guides/self-build.md`](../../doc/mios/guides/self-build.md) and
[`../../doc/mios/guides/deploy.md`](../../doc/mios/guides/deploy.md).

`mios-bootstrap` IS NOT a separate image — it is the same root filesystem as
MiOS (the repo root IS the deployed system root), viewed through a different
`.gitignore`-as-whitelist. It owns **Phase-0** (preflight, profile load, identity
capture) and **Phase-1** (the Total Root Merge) of the build pipeline; once those
complete, every later build invocation comes from the **MiOS** repo's Justfile
and `mios-build-driver` over the same filesystem.

## Where bootstrap sits in the pipeline

| Phase | Owner | Description |
|---|---|---|
| Phase-0 | `mios-bootstrap` | Preflight, profile load, identity capture |
| Phase-1 | `mios-bootstrap` | Total Root Merge — clone `mios.git` into `/`, overlay the bootstrap sources |
| Phase-2 | `Containerfile` / `automation/build.sh` | Build the OCI image (numbered `automation/NN-*.sh` sub-phases) |
| Phase-3 | both | sysusers/tmpfiles/services + user create + per-user config staging |
| Phase-4 | `mios-bootstrap` | Reboot |

Day-0 (this doc + `FIRST-BOOT.md`) is Phase-0/1 plus the first boot of the
resulting MiOS-DEV. Phase-2 onward is the MiOS repo's territory.

## Inputs

- A host capable of running rootful Podman (Fedora 44+, Ubuntu LTS,
  Windows with Podman Desktop in rootful mode, macOS with rootful
  `podman machine`).
- Network access to the OCI base image
  `ghcr.io/ublue-os/ucore-hci:stable-nvidia` (the `MIOS_BASE_IMAGE` default;
  `:stable` for the no-NVIDIA variant). MiOS layers its workstation + agent
  stack on top of this Universal Blue `ucore-hci` base.
- ~30 GB free disk for the image cache + first build.

## Steps

### From scratch, on Linux

1. `git clone https://github.com/mios-dev/mios-bootstrap.git /srv/mios`
2. `cd /srv/mios`
3. `just bootstrap` — runs Phase-0/1: pulls the `ucore-hci` base, builds a
   one-shot tooling container, performs the **Total Root Merge** (clones
   `mios.git` into the shared root and overlays the bootstrap sources), and
   materializes MiOS-DEV inside a Podman machine.
4. `just dev-up` — starts MiOS-DEV; SSH listener on `2222`.
5. `just build` — the first self-replicated MiOS image is emitted to
   `out/mios-<gen>.oci-archive`. (Inside MiOS-DEV this drives the MiOS repo's
   pipeline via `/usr/libexec/mios/mios-build-driver`.)

### From scratch, on Windows

The canonical Windows entry is the `irm | iex` one-liner shipped by
`mios-bootstrap` (runnable from the Run dialog, cmd.exe, or any PowerShell
session — no pre-existing pwsh or manual elevation needed):

```text
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex"
```

`Get-MiOS.ps1` self-elevates, provisions the `MiOS-DEV` Podman machine, clones
`mios.git` + `mios-bootstrap`, and then auto-chains into
`/usr/libexec/mios/mios-build-driver` inside MiOS-DEV for the OCI build — the
Windows equivalent of `just bootstrap` → `just dev-up` → `just build`. It drops
the result as a WSL2 distro, a Hyper-V VHDX, an Anaconda ISO, and a qcow2.

## Hand-Off to MiOS Proper

At the end of `just bootstrap` (Phase-1), the bootstrap repo writes a marker
`.mios/bootstrap-handoff` to the shared root. From this point on, all build
invocations come from the **MiOS** repo's Justfile and `mios-build-driver` (the
same filesystem, viewed through the MiOS whitelist). The bootstrap repo's
`.gitignore` whitelist excludes everything except the bootstrap sources, so the
bootstrap repo "disappears" from the working set without any file deletion — the
Total Root Merge has already laid down the full MiOS tree underneath it.

This is the seam where Day-0 becomes the rest of the lifecycle: the merged root
is exactly the layout the `Containerfile` bakes (`usr/`, `etc/`, `srv/`, `var/`
land where they sit in the repo), so Phase-2's numbered automation scripts —
including the ones that stand up the **AI plane** (the inference lanes, the agent
units, the pgvector schema) — operate on a root the bootstrap merge produced.

## Why a Separate Repo

- **Cleaner first-time UX** — no need to clone the full MiOS tree to get started;
  the bootstrap repo is small and self-describing.
- **Portable across hosts** — bootstrap mustn't depend on MiOS internals, so it
  can run identically on Fedora, Ubuntu, Windows (Podman Desktop), or macOS.
- **Evolves independently** — once Day-1 succeeds, bootstrap is rarely touched;
  decoupling it keeps churn in the MiOS tree from rippling into the entry path.

## Bootstrap repo whitelist (illustrative `.gitignore`)

The bootstrap repo and the MiOS repo are the *same filesystem* differentiated by
inverse whitelists. The bootstrap whitelist re-includes only the bootstrap
sources:

```gitignore
# /.mios-bootstrap.gitignore (whitelist style)
# Ignore everything by default…
*
# …then re-include only what bootstrap needs.
!/.gitignore
!/.mios-bootstrap.gitignore
!/bootstrap/
!/bootstrap/**
!/README-BOOTSTRAP.md
!/Justfile.bootstrap
!/.mios/
!/.mios/bootstrap-handoff
```

The corresponding MiOS-repo `.gitignore` is the inverse: ignore the bootstrap
sources, include everything else under `etc/`, `usr/`, `var/lib/mios/templates/`,
etc. — the deployed system root.

## Re-running bootstrap

`just bootstrap` is idempotent. Re-running it:

- Re-pulls `ucore-hci` only if a newer digest is available (or `--force-pull`).
- Re-applies any drift in `bootstrap/templates/`.
- Refreshes `.mios/bootstrap-handoff` with a new timestamp.

No data outside `bootstrap/` is touched.

## Next

Once bootstrap hands off and MiOS-DEV is up, see [`FIRST-BOOT.md`](FIRST-BOOT.md)
for the Day-0 first-boot sequence (systemd-firstboot, repo clone, invariant
checks, and bring-up of the agent plane), then the build/deploy guides for
Phase-2 onward.
