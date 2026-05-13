<!-- FHS: /usr/share/mios/docs/day-0/BOOTSTRAP.md -->

# Day-0: Bootstrap from `mios-bootstrap`

`mios-bootstrap` is the minimal repository that materializes the
first MiOS-DEV environment from a bare host. It IS NOT a separate
image — it is the same root filesystem as MiOS, viewed through a
different `.gitignore`-as-whitelist.

## Inputs

- A host capable of running rootful Podman (Fedora 44+, Ubuntu LTS,
  Windows with Podman Desktop in rootful mode, macOS with rootful
  podman machine).
- Network access to `ghcr.io/ublue-os/ucore-hci:stable-nvidia`.
- ~30 GB free disk for image cache + first build.

## Steps

1. `git clone https://github.com/mios-dev/mios-bootstrap.git /srv/mios`
2. `cd /srv/mios`
3. `just bootstrap` — pulls ucore-hci, builds a one-shot tooling
   container, materializes MiOS-DEV inside a Podman machine.
4. `just dev-up` — starts MiOS-DEV; SSH listener on 2222.
5. `just build` — first self-replicated MiOS image emitted to
   `out/mios-<gen>.oci-archive`.

## Hand-Off to MiOS Proper

At the end of `just bootstrap`, the bootstrap repo writes a marker
`.mios/bootstrap-handoff` to the shared root. From this point on, all
build invocations come from the **MiOS** repo's Justfile (the same
filesystem, viewed through the MiOS whitelist). The bootstrap repo's
`.gitignore` whitelist excludes everything except the bootstrap
sources, so the bootstrap repo "disappears" from the working set
without any file deletion.

## Why a Separate Repo

- Cleaner first-time UX (no need to clone the full MiOS tree).
- Bootstrap is portable across hosts (mustn't depend on MiOS internals).
- Bootstrap evolves independently — once Day-1 succeeds, it is rarely
  touched.

## Bootstrap repo whitelist (illustrative `.gitignore`)

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

The corresponding MiOS-repo `.gitignore` is the inverse: ignore the
bootstrap sources, include everything else under `etc/`, `usr/`,
`var/lib/mios/templates/`, etc.

## Re-running bootstrap

`just bootstrap` is idempotent. Re-running it:

- Re-pulls ucore-hci only if a newer digest is available (or
  `--force-pull`).
- Re-applies any drift in `bootstrap/templates/`.
- Refreshes `.mios/bootstrap-handoff` with a new timestamp.

No data outside `bootstrap/` is touched.
