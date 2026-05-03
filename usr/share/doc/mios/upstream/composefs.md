# composefs — Verifiable Read-Only Root

> Enabled in 'MiOS' via `usr/lib/ostree/prepare-root.conf`:
> `[composefs] enabled=true`, `[etc] transient=true`, `[root] transient-ro=true`.
> Source: `SECURITY.md` §composefs.

## What it is

composefs combines **overlayfs + EROFS + fs-verity** to produce a
read-only mount whose every file is independently verified by the
kernel. Backing files live in a content-addressed object store
(deduplicated, sharable across deployments).

- Project: <https://github.com/containers/composefs> (alt mirror: <https://github.com/composefs/composefs>)
- v1.0.0 release (stable on-disk format): <https://github.com/composefs/composefs/releases/tag/v1.0.0>

## How the layers fit

```
┌────────────────────────────────────┐
│ overlayfs (/usr writable for tools │   ← ephemeral, top
│   that must — never persists)      │
├────────────────────────────────────┤
│ EROFS image (synthesized by         │   ← read-only middle layer
│   mkcomposefs from manifest +       │
│   metacopy xattrs → backing files)  │
├────────────────────────────────────┤
│ fs-verity-protected backing files   │   ← content-addressed leaves
│   in ostree object store            │
└────────────────────────────────────┘
```

`mount.composefs` validates each backing file's fs-verity digest before
exposing it. Tampering on disk produces an `EIO`, not silent corruption.

## 'MiOS' enable shape

`usr/lib/ostree/prepare-root.conf`:

```ini
[composefs]
enabled = true

[etc]
transient = true     # /etc is a fresh tmpfs each boot, populated from image + 3-way merge

[root]
transient-ro = true  # / is read-only with a tmpfs upper for ephemeral writes
```

Effects:

- `/usr` — content-addressed, deduplicated, verified
- `/etc` — written each boot from the image's `/etc` + persisted admin
  overrides (3-way merge); LAW 1 USR-OVER-ETC discourages writing here
- `/` — root mount is read-only; runtime writes go to `/var` (governed
  by LAW 2 NO-MKDIR-IN-VAR via `usr/lib/tmpfiles.d/`)

## Why 'MiOS' uses it

- **Trusted boot**: any tampering at the disk level is detected by
  fs-verity before the file is exposed to user space
- **Day-2 deltas**: identical files across image versions are stored
  once; `bootc upgrade` only fetches the deltas (further optimized by
  rechunk's 67-layer split)
- **No write amplification**: applying an upgrade hardlinks unchanged
  files; only changed files consume new blocks

## Cross-refs

- `usr/share/doc/mios/upstream/ostree.md`
- `usr/share/doc/mios/upstream/rechunk.md`
- `SECURITY.md` §composefs
- `ARCHITECTURE.md` §Filesystem-layout (FHS 3.0 + bootc)
