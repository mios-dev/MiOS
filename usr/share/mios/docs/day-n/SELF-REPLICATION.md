<!-- AI-hint: Documents the recursive self-build-and-upgrade lifecycle of MiOS — how a running MiOS host rebuilds itself into the next bootc/OCI image generation and upgrades onto it, and how Justfile phases, pinned dependencies, signing, and bootc make that loop reproducible. Frames self-replication as the property that makes MiOS (an immutable Fedora workstation that is also a local agentic AI OS) able to re-create itself with no terminus.
     AI-related: /usr/share/mios/docs/day-n/SELF-REPLICATION.md, /usr/share/mios/src/, /usr/share/mios/mios.toml, Justfile, automation/build.sh, mios-build-driver, mios-doctor, mios-dev -->
<!-- FHS: /usr/share/mios/docs/day-n/SELF-REPLICATION.md -->

# Day-1 → Day-N: The Self-Replication Loop

## Purpose & place in the whole system

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is
*also* a **local, self-hosted, agentic AI operating system** (local inference
lanes behind one OpenAI-compatible endpoint, a multi-agent orchestration
pipeline, and a PostgreSQL+pgvector memory, all on your own hardware).

Self-replication is what binds those two halves into a single living lifecycle.
Because the *entire* system — GNOME/Wayland desktop, GPU wiring, KVM/libvirt
passthrough, the k3s+Ceph cluster path, **and** the full AI stack — is baked into
one rebuildable OCI image, a running MiOS host can rebuild itself into the *next*
image and then upgrade onto its own output. The build pipeline produces the
image; the bootc lifecycle deploys it and can revert it; this document describes
the loop that connects the two and makes it reproducible generation after
generation.

This doc is for operators and contributors who run or reason about that loop.

## Day-1: First Self-Built MiOS

MiOS-DEV's running state IS the build input. The Justfile target `build` drives
the `Containerfile`, which runs every `automation/[NN]-*.sh` phase script in
numeric order (the prefix encodes dependency order). Those phases install
packages, configure SELinux, wire CDI for the GPUs, stand up the inference lanes
and agent units, and seed the pgvector schema — the *same* mechanism that
installs a package also stands up the brain. The output is a bootc OCI image
that, when booted, is functionally identical to the MiOS-DEV that produced it
(modulo machine-local state in `/etc` and `/var`).

This is the system's first half of lifecycle made recursive: **build pipeline →
OCI image → bootc lifecycle → (the new host can run the build pipeline again).**

## Day-N: Continuous Loop

Each generation builds the next. The build is reproducible to the extent that:

- The base `ucore-hci` tag (`ghcr.io/ublue-os/ucore-hci:stable-nvidia`, the
  vendor default in `mios.toml` `[image].base`) is pinned by digest in the
  `Containerfile`.
- Package versions resolve from `usr/share/mios/mios.toml` under
  `[packages.<section>].pkgs` (the single source of truth, parsed by
  `automation/lib/packages.sh`), recorded as pinned NVRs in the per-generation
  packages lock.
- The Justfile and `automation/` scripts are committed; phase script SHAs are
  recorded in the manifest.

The image that comes out is whole — the AI plane (inference lanes,
`agent-pipe`/Hermes orchestration, pgvector memory, MCP/A2A surfaces) ships
*inside* it by Architectural Law 3 (BOUND-IMAGES), so a freshly-built generation
boots with its brain already attached and reproduced bit-for-bit on any host that
pulls the ref.

## Generation Tagging

```
ghcr.io/mios-dev/mios:gen-<N>
ghcr.io/mios-dev/mios:latest    # = gen-<N> for the latest signed gen
```

`bootc upgrade` always points at `:latest` (the canonical ref is
`ghcr.io/mios-dev/mios:latest`, set in `mios.toml` `[image].ref`). Specific
generations are referenced by digest for rollback — the same digest-pinning that
lets `bootc rollback` be a deterministic Ctrl-Z.

## What "Self-Replicating" Excludes

- Machine-local state (`/etc`, `/var`, `/var/home/*`) does not carry over — by
  design (bootc semantics). `/usr` is the read-only composefs that replicates;
  `/etc` gets a 3-way merge across upgrades; `/var` survives but is host-local.
  This is also why the runtime AI state that lives under `/var` (pgvector data,
  KV-cache slot files, agent memory) is *host-local* and does **not** propagate
  through the image — only the agent stack's code and configuration replicate.
- The `Containerfile` must be cleanly buildable from a stock `ucore-hci` base;
  MiOS doesn't "embed" itself in the new image except as source files in
  `/usr/share/mios/src/` (a committed snapshot). Self-replication is *rebuild
  from source*, not *copy the running root*.

## The Day-N loop in five steps

```sh
# 1. Pull or refresh the canonical mios source view (repo root IS system root).
git fetch --all && git rebase origin/main

# 2. Run all invariants. Refuses to continue on any failure.
mios-doctor

# 3. Build the next image. The Justfile drives the Containerfile, which runs
#    every automation/[NN]-*.sh phase in numeric order; the final RUN is
#    `bootc container lint` (Architectural Law 4 — fail = fail the build).
just build

# 4. Sign and publish to GHCR (cosign keyless via OIDC).
just publish

# 5. Upgrade the running MiOS-DEV to its own output.
sudo bootc upgrade
sudo systemctl reboot
```

After reboot, the now-newer MiOS-DEV is ready to build the *next* next gen. The
loop has no terminus: a complete OS — desktop, GPU stack, VMs, cluster path, and
local AI brain — re-creating itself on each turn.

## Reproducibility ledger

Each generation publishes alongside its image a ledger that makes the build
auditable and the loop verifiable:

- `mios-<gen>.containerfile-digest`  — sha256 of the `Containerfile`.
- `mios-<gen>.packages-lock`         — pinned NVRs resolved from `mios.toml`.
- `mios-<gen>.kargs-effective`       — merged `kargs.d` output.
- `mios-<gen>.invariants-passed`     — `mios-doctor` JSON report.
- `mios-<gen>.cosign.sig` + `.cert`  — cosign keyless artifacts.

A second host, given identical inputs, MUST produce a bit-identical ostree commit
(modulo timestamps in metadata). Drift is treated as a build bug — because the
whole-system promise (Law 3 bakes the containers in, Law 5 unifies the AI
endpoint, Law 6 keeps the agent plane unprivileged) only holds if every
generation reproduces the last one faithfully.
