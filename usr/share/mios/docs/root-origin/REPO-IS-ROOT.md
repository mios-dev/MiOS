<!-- AI-hint: Defines MiOS Architectural Law USR-OVER-ETC's foundation — the git working tree's top-level directory IS the literal OS filesystem root, eliminating staging/overlay directories so any file at repo path X maps directly to /X in the built bootc/OCI image; explains the .git-at-root overlay, the tar-pipeline build copy, and how this rule makes the build pipeline -> image -> bootc lifecycle reproducible and auditable.
     AI-related: /usr/share/mios/docs/root-origin/REPO-IS-ROOT.md, /usr/share/mios/docs/root-origin/DUAL-WHITELIST.md, Containerfile, automation/08-system-files-overlay.sh, automation/build.sh, mios-bootstrap -->
<!-- FHS: /usr/share/mios/docs/root-origin/REPO-IS-ROOT.md -->

# Root-Origin: The Repo IS the OS Root

## Purpose

MiOS is one thing built two ways at once: an immutable, bootc/OCI-shaped
Fedora workstation (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that
is *also* a local, self-replicating, agentic AI operating system. For that
dual nature to hold — for the image to be deterministic, auditable, and
reproducible on every box that pulls the ref — the source of the OS and the OS
itself must be the *same* artifact. This document states the law that makes
that true: **the repo working tree IS the deployed system root.** It is the
ground floor under Architectural Law 1 (USR-OVER-ETC) and the whole
build pipeline → image → bootc lifecycle.

Audience: anyone editing the MiOS repo or extending the build. The takeaway is
simple — when you edit a file in this repo, you are editing the OS.

## Statement

The MiOS git working tree's top-level directory IS the filesystem
root of the OS being built. There is no intermediate `system_files/`
directory, no `rootfs/` staging, no `overlay/`. What's in the repo
at `etc/foo` is what ends up at `/etc/foo` on the target.

This is what lets the rest of the system stay coherent: the agent stack
(agent-pipe, MiOS-Hermes, the inference lanes, the pgvector datastore) ships in
the exact same immutable image as the kernel, GNOME session, and GPU wiring,
version-locked to the OS and reproduced byte-for-byte everywhere the image
deploys. There is no separate "agent install" to drift.

## `.git` as Root-Level Overlay

The `.git` directory sits at `/.git` on the live MiOS working
tree. It is treated as a normal directory by ostree/composefs
(included in `/var` for mutability via the standard transient-etc /
persistent-var split). Conceptually: `./[ROOT]/.git`.

`bootc` and ostree do not care about `.git`. composefs's read-only
view of `/usr` does not include `/.git` (which lives at the top
level, NOT under `/usr`). Therefore the repo metadata is mutable and
rebuild-friendly — you can `git commit` on a running, immutable host.

## Why

- Eliminates the "build vs. source" cognitive split that plagues
  every other OS builder. The image you ship and the tree you edit are
  one and the same.
- Every fix is `vim /etc/foo` then `git commit` — no copy step, no
  re-sync of a staging directory.
- Auditing what's in the OS is `git ls-files` — Law 4
  (BOOTC-CONTAINER-LINT) checks the image; `git` lets you audit the
  source of every byte that went into it.

## Containerfile Implications

The image is produced by a single-stage `Containerfile` that bind-mounts the
build context read-only with
`--mount=type=bind,source=.,target=/ctx,ro`. Phase scripts copy from
`/ctx/<path>` into the image rootfs using **tar pipelines** (see
[`DUAL-WHITELIST.md`](DUAL-WHITELIST.md) and the ucore-hci `/usr/local`
symlink rule). `automation/08-system-files-overlay.sh` applies this
root overlay before the numbered `automation/build.sh` pipeline runs.

This is Phase-2 of the build: the working tree (Phase-1's Total Root
Merge) becomes the image, which the bootc lifecycle then carries forward
(`bootc switch`/`upgrade` to deploy, `bootc rollback` to revert).
Because the copy is a faithful tar of the tree — not a hand-curated
staging area — the image is reproducible from the commit alone.

## What NOT to Do

- ❌ Don't create a `system_files/` directory.
- ❌ Don't `cp -a /ctx/usr /usr` — breaks `/usr/local` (symlink to
  `/var/usrlocal` in ucore-hci). Use the two-stage tar pipeline:

  ```sh
  ( cd /ctx && tar --exclude=./.git -cf - . ) \
    | ( cd /  && tar --no-overwrite-dir -xpf - )
  ```

- ❌ Don't relocate `.git`. It MUST live at root for the dual-
  whitelist scheme (two repos sharing one working tree) to work.

## Mental model

```
┌─────────────────────────────────────────────────────────┐
│  Working tree on the live MiOS host                     │
│                                                         │
│  /                  <─ OS root AND repo root            │
│  ├── .git/          <─ MiOS repo (overlay-at-root)      │
│  ├── .mios-bootstrap.git/   <─ Bootstrap repo           │
│  ├── etc/           <─ becomes /etc on target           │
│  ├── usr/           <─ becomes /usr on target           │
│  │   ├── bin/                                           │
│  │   ├── lib/bootc/kargs.d/                             │
│  │   ├── libexec/mios/phases/                           │
│  │   └── share/mios/                                    │
│  └── var/           <─ becomes /var on target (mutable) │
└─────────────────────────────────────────────────────────┘
```

The build does NOT copy from a staging area; the working tree IS the
staging area, modulo the `.git` exclusion in the tar pipeline. The two
`.git` directories that share this one tree are isolated by the
whitelist-style `.gitignore` topology described in
[`DUAL-WHITELIST.md`](DUAL-WHITELIST.md).

## Implications for editors and IDEs

- `git status` works at any directory under `/`.
- An IDE rooted at `/` sees both repos' files (visibility is
  determined by which repo's `.gitignore` is active).
- Backups MUST exclude both `.git` directories' object stores OR
  back them up explicitly — there's no separate "source tarball" to
  capture.

## How this serves the whole system

Because the repo *is* the root, the entire MiOS stack is one auditable,
version-locked unit: the build pipeline assembles the tree into an OCI image,
bootc deploys and rolls it back atomically, and everything that runs on
top — the GPU wiring (CDI), the KVM/VFIO passthrough path, the k3s+Ceph
cluster option, and the local agentic AI plane behind the single
`MIOS_AI_ENDPOINT` — ships from that same image. No drift between source and
system; `git ls-files` and `bootc` together account for every byte the OS runs.
