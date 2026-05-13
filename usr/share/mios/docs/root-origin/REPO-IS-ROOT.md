<!-- FHS: /usr/share/mios/docs/root-origin/REPO-IS-ROOT.md -->

# Root-Origin: The Repo IS the OS Root

## Statement

The MiOS git working tree's top-level directory IS the filesystem
root of the OS being built. There is no intermediate `system_files/`
directory, no `rootfs/` staging, no `overlay/`. What's in the repo
at `etc/foo` is what ends up at `/etc/foo` on the target.

## `.git` as Root-Level Overlay

The `.git` directory sits at `/.git` on the live MiOS-DEV
filesystem. It is treated as a normal directory by ostree/composefs
(included in `/var` for mutability via the standard transient-etc /
persistent-var split). Conceptually: `./[ROOT]/.git`.

`bootc` and ostree do not care about `.git`. composefs's read-only
view of `/usr` does not include `/.git` (which lives at the top
level, NOT under `/usr`). Therefore the repo metadata is mutable and
rebuild-friendly.

## Why

- Eliminates the "build vs. source" cognitive split that plagues
  every other OS builder.
- Every fix is `vim /etc/foo` then `git commit` — no copy step.
- Auditing what's in the OS is `git ls-files`.

## Containerfile Implications

The single-stage `Containerfile` uses
`--mount=type=bind,source=.,target=/ctx,ro` to make the build
context available. Phase scripts copy from `/ctx/<path>` to the
image rootfs using **tar pipelines** (see `DUAL-WHITELIST.md` and the
ucore-hci `/usr/local` symlink rule).

## What NOT to Do

- ❌ Don't create a `system_files/` directory.
- ❌ Don't `cp -a /ctx/usr /usr` — breaks `/usr/local` (symlink to
  `/var/usrlocal` in ucore-hci). Use the two-stage tar pipeline:

  ```sh
  ( cd /ctx && tar --exclude=./.git -cf - . ) \
    | ( cd /  && tar --no-overwrite-dir -xpf - )
  ```

- ❌ Don't relocate `.git`. It MUST live at root for the dual-
  whitelist scheme to work.

## Mental model

```
┌─────────────────────────────────────────────────────────┐
│  Working tree on MiOS-DEV                               │
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
staging area, modulo the `.git` exclusion in the tar pipeline.

## Implications for editors and IDEs

- `git status` works at any directory under `/`.
- An IDE rooted at `/` sees both repos' files (visibility is
  determined by which repo's `.gitignore` is active).
- Backups MUST exclude both `.git` directories' object stores OR
  back them up explicitly — there's no separate "source tarball" to
  capture.
